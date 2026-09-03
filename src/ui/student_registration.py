"""Database-backed public StudentRegistrationView.

The original capture/UI behavior remains in ``legacy_student_registration``;
student persistence is SQLite-first and camera capture uses the resilient
OpenCV wrapper so disconnects can recover without restarting the application.
"""
from __future__ import annotations

import logging
import threading
from typing import Any

import cv2

from src.core.camera import ResilientCamera
from src.core.database.compat_exports import export_legacy_student_csvs
from src.core.database.service import DatabaseService
from src.ui.legacy_student_registration import (
    StudentRegistrationView as _LegacyStudentRegistrationView,
)

logger = logging.getLogger(__name__)


class StudentRegistrationView(_LegacyStudentRegistrationView):
    """Legacy registration UI with canonical student persistence."""

    def __init__(self, master, **kwargs: Any) -> None:
        self.database = DatabaseService()
        super().__init__(master, **kwargs)

    def start_camera(self) -> None:
        """Start a reconnecting camera while preserving the retained UI loop."""
        if self.is_capturing:
            self.stop_camera()
            return

        try:
            camera = ResilientCamera(self.camera_id)
            if not camera.open():
                self.show_status("Failed to open camera. Please check your camera connection.", "red")
                logger.error("Failed to open camera with ID: %s", self.camera_id)
                return
            self.camera_feed = camera

            self.camera_feed.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera_feed.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            ok, frame = self.camera_feed.read()
            if not ok or frame is None:
                self.show_status("Failed to read from camera", "red")
                self.camera_feed.release()
                self.camera_feed = None
                return

            self.is_capturing = True
            self.start_button.configure(
                text="Stop Camera",
                fg_color=("#e74c3c", "#c0392b"),
            )
            self.capture_button.configure(state="normal")
            self.show_status("Camera started successfully", "green")

            self.camera_thread = threading.Thread(target=self._camera_loop, daemon=True)
            self.camera_thread.start()
            logger.info("Resilient camera started for student registration")
        except (cv2.error, OSError, RuntimeError) as exc:
            self.show_status(f"Failed to start camera: {exc}", "red")
            logger.error("Error starting camera: %s", exc)

    def save_student_details(self, student_id: str, name: str, course: str, year: str) -> bool:
        """Upsert the student in SQLite, then refresh read-only compatibility CSVs."""
        student_id = str(student_id).strip()
        name = str(name).strip()
        if not student_id or not name:
            self.logger.error("Student ID and name are required") if hasattr(self, "logger") else None
            return False

        success = self.database.add_student(
            enrollment=student_id,
            name=name,
            department=str(course).strip() or None,
            year=str(year).strip() or None,
        )
        if not success:
            return False

        export_legacy_student_csvs(self.database)
        return True

    def destroy(self) -> None:
        """Close the database when the registration view is destroyed."""
        try:
            self.database.close()
        finally:
            super().destroy()


__all__ = ["StudentRegistrationView"]
