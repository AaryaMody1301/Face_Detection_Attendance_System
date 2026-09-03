"""Database-backed YuNet + SFace training view."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2

from src.core.database.compat_exports import export_legacy_student_csvs
from src.core.database.service import DatabaseService
from src.core.face_engine import DEFAULT_GALLERY_PATH, FaceEngine
from src.core.face_models import ModelUnavailableError
from src.ui import legacy_training_view

legacy_training_view.FaceDetector = FaceEngine


class TrainingView(legacy_training_view.TrainingView):
    """Legacy visual surface with canonical SFace enrollment."""

    def __init__(self, master, controller=None, **kwargs: Any) -> None:
        self.database = DatabaseService()
        self.face_engine = FaceEngine()
        export_legacy_student_csvs(self.database)
        super().__init__(master, controller=controller, **kwargs)

    def _process_camera_frame(self, frame):
        """Preview YuNet detections instead of the retained Haar preview."""
        if frame is None:
            return frame
        mirrored = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(mirrored, cv2.COLOR_BGR2RGB)
        try:
            for top, right, bottom, left in self.face_engine.detect_faces(mirrored):
                cv2.rectangle(rgb_frame, (left, top), (right, bottom), (0, 255, 0), 2)
                cv2.putText(
                    rgb_frame,
                    "YuNet face",
                    (left, max(20, top - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (0, 255, 0),
                    2,
                )
        except (ModelUnavailableError, cv2.error) as exc:
            self.log(f"Face detector unavailable: {exc}", level="error")
        return rgb_frame

    def capture_image(self) -> None:
        """Capture one training frame after a single-face YuNet check."""
        if not self.camera_running or not hasattr(self, "current_frame") or self.current_frame is None:
            self.show_status("Camera not running", "red")
            return

        student_id = self.student_id_var.get().strip()
        student_name = self.student_name_var.get().strip()
        if not student_id:
            self.show_status("Please enter student ID", "red")
            return
        if not student_name:
            self.show_status("Please enter student name", "red")
            return

        try:
            self.target_images = max(1, int(self.image_count_var.get()))
        except ValueError:
            self.target_images = 20

        try:
            locations = self.face_engine.detect_faces(self.current_frame)
            if len(locations) == 0:
                self.show_status("No face detected by YuNet", "red")
                return
            if len(locations) > 1:
                self.show_status("Multiple faces detected", "red")
                return

            image_dir = Path(self.images_dir) / student_id
            image_dir.mkdir(parents=True, exist_ok=True)
            image_path = image_dir / f"{student_id}_{self.images_captured}.jpg"
            if not cv2.imwrite(str(image_path), self.current_frame):
                raise OSError(f"Could not save training image: {image_path}")

            self.images_captured += 1
            self.capture_counter.configure(
                text=f"Images: {self.images_captured}/{self.target_images}"
            )
            self.progress_bar.set(self.images_captured / self.target_images)
            self.show_status(f"Image {self.images_captured} captured", "green")
            self.log(
                f"Captured image {self.images_captured}/{self.target_images} for student {student_id}",
                level="info",
            )
            if self.images_captured >= self.target_images:
                self.show_status("All images captured", "green")
                self.after(1000, self.start_training)
        except (ModelUnavailableError, cv2.error, OSError) as exc:
            self.log(f"Capture failed: {exc}", level="error")
            self.show_status("Face capture failed", "red")

    def _training_process(self) -> None:
        """Enroll the selected student into the canonical SFace gallery."""
        success = False
        try:
            student_id = self.student_id_var.get().strip()
            student_name = self.student_name_var.get().strip()
            if not student_id or not student_name:
                self.log("Student ID and name are required", level="error")
                return

            image_dir = Path(self.images_dir) / student_id
            image_paths = sorted(image_dir.glob(f"{student_id}_*.jpg"))
            if not image_paths:
                self.log(f"No training images found for student {student_id}", level="error")
                return

            self.after(0, lambda: self._update_progress_ui(0.15, "Loading SFace gallery"))
            self.log("Loading existing SFace gallery", level="info")
            if DEFAULT_GALLERY_PATH.exists() and not self.face_engine.load_model(DEFAULT_GALLERY_PATH):
                self.log("Existing face gallery is incompatible and will be rebuilt", level="warning")

            if not self.training_running:
                self.log("Training cancelled", level="warning")
                return

            self.after(0, lambda: self._update_progress_ui(0.35, "Extracting SFace features"))
            self.log(
                f"Extracting aligned SFace features from {len(image_paths)} YuNet detections",
                level="info",
            )
            success = self.face_engine.enroll_student(
                student_id,
                student_name,
                image_paths,
                model_path=DEFAULT_GALLERY_PATH,
            )
            if not success:
                self.log("No usable YuNet/SFace faces were found in the captured images", level="error")
                return

            self.after(0, lambda: self._update_progress_ui(0.8, "Saving gallery"))
            self._update_student_info(student_id, student_name)
            self.log(f"Updated SFace template for {student_name} ({student_id})", level="info")
            self.log(f"Saved canonical gallery to {DEFAULT_GALLERY_PATH}", level="info")
            self.after(0, lambda: self._update_progress_ui(1.0, "Training complete"))
        except (ModelUnavailableError, cv2.error, OSError, RuntimeError, ValueError) as exc:
            self.log(f"SFace training failed: {exc}", level="error")
        finally:
            self.after(0, lambda ok=success: self._update_training_progress_ui(ok))

    def _update_student_info(self, student_id: str, student_name: str) -> None:
        """Upsert training identity metadata in SQLite and refresh CSV exports."""
        student_id = str(student_id).strip()
        student_name = str(student_name).strip()
        if not student_id or not student_name:
            self.log("Student ID and name are required", level="error")
            return

        if not self.database.add_student(student_id, student_name):
            self.log(f"Failed to update student information for ID: {student_id}", level="error")
            return

        export_legacy_student_csvs(self.database)
        self.log(f"Updated student information for ID: {student_id}", level="info")

    def destroy(self) -> None:
        try:
            self.face_engine.cleanup()
            self.database.close()
        finally:
            super().destroy()


__all__ = ["TrainingView"]
