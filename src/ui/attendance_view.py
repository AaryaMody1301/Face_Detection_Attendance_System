"""Database-backed attendance UI with YuNet, SFace, and anti-spoofing."""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from tkinter import messagebox
from typing import Any

import cv2

from src.core.database.compat_exports import export_legacy_student_csvs
from src.core.database.service import DatabaseService
from src.core.face_engine import DEFAULT_GALLERY_PATH, FaceEngine
from src.core.face_models import ModelUnavailableError
from src.core.liveness import MiniFASLiveness, TemporalLivenessGate, recognize_faces_guarded
from src.ui.legacy_face_compat import LegacyAttendanceView as _LegacyAttendanceView


def _local_now() -> datetime:
    """Return current local time as a timezone-aware datetime."""
    return datetime.now(UTC).astimezone()


class AttendanceView(_LegacyAttendanceView):
    """Legacy visual surface with canonical persistence and guarded recognition."""

    def __init__(self, master=None, config=None, **kwargs: Any) -> None:
        self.database = DatabaseService()
        self.face_engine = FaceEngine()
        self.liveness_engine = MiniFASLiveness()
        self.liveness_gate = TemporalLivenessGate()
        export_legacy_student_csvs(self.database)
        super().__init__(master=master, config=config, **kwargs)
        self.has_recognition_model = self.face_engine.load_model(DEFAULT_GALLERY_PATH)

    def load_students(self) -> None:
        """Populate the recognition lookup from SQLite instead of students.csv."""
        self.students = {}
        try:
            students = self.database.get_student_details()
            for _, row in students.iterrows():
                enrollment = str(row["Enrollment"])
                self.students[enrollment] = (enrollment, str(row["Name"]))
            self.logger.info("Loaded %s student records from SQLite", len(self.students))
        except Exception as exc:  # noqa: BLE001 - UI boundary must not kill the event loop
            self.logger.error("Error loading students from SQLite: %s", exc)

    def _get_subjects(self) -> list[str]:
        """Use database subjects while preserving configured course choices."""
        subjects = set(self.database.get_subjects())
        try:
            configured = self.config.get("courses", []) if self.config is not None else []
            if isinstance(configured, (list, tuple, set)):
                subjects.update(str(item).strip() for item in configured if str(item).strip())
        except (AttributeError, TypeError):
            pass
        subjects.discard("")
        return sorted(subjects) or ["General"]

    def _process_frame(self, frame):
        """Gate automatic SFace recognition behind MiniFAS liveness checks."""
        if frame is None:
            return None
        processed = frame.copy()
        recognition_message = "No face detected"
        try:
            if self.attendance_mode == "auto" and self.has_recognition_model:
                results = recognize_faces_guarded(
                    self.face_engine,
                    processed,
                    self.liveness_engine,
                    self.liveness_gate,
                )
                if results:
                    recognition_message = "Checking liveness"

                for result in results:
                    top, right, bottom, left = result.location
                    decision = result.liveness
                    prediction = decision.prediction
                    recognized = result.name != "Unknown" and bool(result.student_id)

                    if not prediction.is_live:
                        box_color = (0, 0, 255)
                        label = f"Spoof blocked: {prediction.label}"
                        recognition_message = (
                            f"Spoof blocked ({prediction.label}, live={prediction.live_score:.2f})"
                        )
                    elif not decision.passed:
                        box_color = (0, 215, 255)
                        label = (
                            f"Liveness {decision.live_frames}/"
                            f"{self.liveness_gate.required_live_frames}"
                        )
                        recognition_message = "Hold still while liveness is confirmed"
                    elif not recognized:
                        box_color = (0, 165, 255)
                        label = f"Live - Unknown ({prediction.live_score:.2f})"
                        recognition_message = "Live face not enrolled"
                    else:
                        box_color = (0, 255, 0)
                        label = (
                            f"{result.name} {result.recognition_score * 100:.1f}% "
                            f"Live {prediction.live_score:.2f}"
                        )
                        recognition_message = (
                            f"Live + recognized: {result.name} ({result.student_id})"
                        )
                        if result.student_id not in self.marked_students:
                            self.mark_attendance(result.student_id, result.name)
                            self.marked_students.add(result.student_id)
                            self.after(0, self._flash_attendance_marked)

                    cv2.rectangle(processed, (left, top), (right, bottom), box_color, 2)
                    cv2.putText(
                        processed,
                        label,
                        (left, max(20, top - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.62,
                        box_color,
                        2,
                    )
            else:
                locations = self.face_engine.detect_faces(processed)
                if locations:
                    recognition_message = (
                        "Face detected (Manual mode)"
                        if self.attendance_mode == "manual"
                        else "Face detected - train the SFace gallery"
                    )
                for top, right, bottom, left in locations:
                    cv2.rectangle(processed, (left, top), (right, bottom), (255, 0, 0), 2)
                    cv2.putText(
                        processed,
                        "Face",
                        (left, max(20, top - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.65,
                        (255, 0, 0),
                        2,
                    )
        except ModelUnavailableError as exc:
            recognition_message = "Liveness unavailable - auto attendance blocked"
            self.logger.error("Required face/liveness model unavailable: %s", exc)
        except (cv2.error, ValueError) as exc:
            recognition_message = "Recognition/liveness error"
            self.logger.error("Guarded frame processing failed: %s", exc)

        self.after(0, lambda msg=recognition_message: self._update_status(msg))
        return cv2.cvtColor(processed, cv2.COLOR_BGR2RGB)

    def mark_attendance(self, student_id: str, student_name: str) -> None:
        """Persist attendance to SQLite and update the existing UI state."""
        now = _local_now()
        subject = self.subject_var.get().strip() if hasattr(self, "subject_var") else "General"
        subject = subject or "General"
        method = (
            "manual"
            if getattr(self, "attendance_mode", "auto") == "manual"
            else "sface+liveness"
        )

        try:
            success = self.database.mark_attendance(
                enrollment=str(student_id),
                name=str(student_name),
                subject=subject,
                date=now.strftime("%Y-%m-%d"),
                time=now.strftime("%H:%M:%S"),
                method=method,
            )
            if not success:
                raise RuntimeError("database rejected the attendance record")

            record = {
                "id": str(student_id),
                "name": str(student_name),
                "time": now.strftime("%H:%M:%S"),
                "confidence": "Manual" if method == "manual" else "SFace + Liveness",
            }
            existing_ids = {str(item.get("id")) for item in self.attendance_list}
            if str(student_id) not in existing_ids:
                self.attendance_list.append(record)
                if hasattr(self, "tree") and self.tree is not None:
                    self.tree.insert(
                        "",
                        "end",
                        values=(
                            record["id"],
                            record["name"],
                            record["time"],
                            record["confidence"],
                        ),
                    )

            if hasattr(self, "save_button"):
                self.save_button.configure(state="normal")

            message = f"Attendance marked for {student_name} ({student_id})"
            self.logger.info(message)
            if hasattr(self, "_update_log"):
                self._update_log(message)
            if hasattr(self, "_show_attendance_confirmation"):
                self.after(0, lambda: self._show_attendance_confirmation(student_name))
        except Exception as exc:  # noqa: BLE001 - UI boundary must not kill the event loop
            self.logger.error("Error marking attendance through SQLite: %s", exc)
            if hasattr(self, "_update_log"):
                self._update_log(f"Error marking attendance: {exc}", level="error")
            self.show_status(f"Failed to mark attendance: {exc}", "red")

    def _mark_attendance(self, student_id: str, student_name: str) -> None:
        self.mark_attendance(student_id, student_name)

    def _save_attendance(self) -> None:
        """Regenerate a compatibility CSV export from SQLite."""
        try:
            subject = self.subject_var.get().strip() if hasattr(self, "subject_var") else "General"
            subject = subject or "General"
            current_date = _local_now().strftime("%Y-%m-%d")
            records = self.database.get_attendance_records(subject=subject, date=current_date)
            if not records:
                messagebox.showinfo("No Records", "There are no attendance records to export.")
                return

            export_dir = Path(getattr(self, "attendance_dir", "Attendance"))
            export_dir.mkdir(parents=True, exist_ok=True)
            filename = f"Attendance_{subject}_{current_date}.csv"
            export_path = export_dir / filename
            self.database.export_attendance_csv(export_path, subject=subject, date=current_date)
            self.show_status(f"Attendance exported to {filename}", "green")
            messagebox.showinfo("Success", f"Attendance records exported to {filename}")
        except Exception as exc:  # noqa: BLE001 - UI boundary must not kill the event loop
            self.logger.error("Error exporting attendance: %s", exc)
            messagebox.showerror("Error", f"Failed to export attendance: {exc}")

    def cleanup(self) -> bool:
        result = True
        try:
            result = bool(super().cleanup())
        finally:
            self.liveness_gate.reset()
            self.liveness_engine.cleanup()
            self.face_engine.cleanup()
            self.database.close()
        return result


__all__ = ["AttendanceView"]