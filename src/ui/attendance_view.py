"""Database-backed public AttendanceView.

The original UI/camera implementation is preserved in ``legacy_attendance_view``.
This subclass routes all student reads and attendance persistence through the
canonical SQLite service so CSV files are exports only.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from tkinter import messagebox
from typing import Any

from src.core.database.service import DatabaseService
from src.ui.legacy_attendance_view import AttendanceView as _LegacyAttendanceView


class AttendanceView(_LegacyAttendanceView):
    """Legacy visual surface with canonical database persistence."""

    def __init__(self, master=None, config=None, **kwargs: Any) -> None:
        self.database = DatabaseService()
        super().__init__(master=master, config=config, **kwargs)

    def load_students(self) -> None:
        """Populate the recognition lookup from SQLite instead of students.csv."""
        self.students = {}
        try:
            students = self.database.get_student_details()
            for _, row in students.iterrows():
                enrollment = str(row["Enrollment"])
                self.students[enrollment] = (enrollment, str(row["Name"]))
            self.logger.info("Loaded %s student records from SQLite", len(self.students))
        except Exception as exc:
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

    def mark_attendance(self, student_id: str, student_name: str) -> None:
        """Persist attendance to SQLite and update the existing UI state."""
        now = datetime.now()
        subject = self.subject_var.get().strip() if hasattr(self, "subject_var") else "General"
        subject = subject or "General"
        method = "manual" if getattr(self, "attendance_mode", "auto") == "manual" else "face"

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
                "confidence": "Manual" if method == "manual" else "Recognized",
            }
            existing_ids = {str(item.get("id")) for item in self.attendance_list}
            if str(student_id) not in existing_ids:
                self.attendance_list.append(record)
                if hasattr(self, "tree") and self.tree is not None:
                    self.tree.insert(
                        "",
                        "end",
                        values=(record["id"], record["name"], record["time"], record["confidence"]),
                    )

            if hasattr(self, "save_button"):
                self.save_button.configure(state="normal")

            message = f"Attendance marked for {student_name} ({student_id})"
            self.logger.info(message)
            if hasattr(self, "_update_log"):
                self._update_log(message)
            if hasattr(self, "_show_attendance_confirmation"):
                self.after(0, lambda: self._show_attendance_confirmation(student_name))
        except Exception as exc:
            self.logger.error("Error marking attendance through SQLite: %s", exc)
            if hasattr(self, "_update_log"):
                self._update_log(f"Error marking attendance: {exc}", level="error")
            self.show_status(f"Failed to mark attendance: {exc}", "red")

    def _mark_attendance(self, student_id: str, student_name: str) -> None:
        """Compatibility path used by older camera callbacks."""
        self.mark_attendance(student_id, student_name)

    def _save_attendance(self) -> None:
        """Regenerate a compatibility CSV export from SQLite."""
        try:
            subject = self.subject_var.get().strip() if hasattr(self, "subject_var") else "General"
            subject = subject or "General"
            current_date = datetime.now().strftime("%Y-%m-%d")
            records = self.database.get_attendance_records(subject=subject, date=current_date)
            if not records:
                messagebox.showinfo("No Records", "There are no attendance records to export.")
                return

            export_dir = Path(getattr(self, "attendance_dir", "Attendance"))
            export_dir.mkdir(parents=True, exist_ok=True)
            filename = f"Attendance_{subject}_{current_date}.csv"
            export_path = export_dir / filename
            self.database.export_attendance_csv(
                export_path,
                subject=subject,
                date=current_date,
            )
            self.show_status(f"Attendance exported to {filename}", "green")
            messagebox.showinfo("Success", f"Attendance records exported to {filename}")
        except Exception as exc:
            self.logger.error("Error exporting attendance: %s", exc)
            messagebox.showerror("Error", f"Failed to export attendance: {exc}")

    def cleanup(self) -> bool:
        """Release UI/camera resources and close the database connection."""
        result = True
        try:
            result = bool(super().cleanup())
        finally:
            self.database.close()
        return result


__all__ = ["AttendanceView"]
