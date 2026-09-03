"""Database-backed public TrainingView.

The existing training UI remains in ``legacy_training_view``. This adapter makes
student updates DB-first and routes detector construction through ``FaceEngine``
without changing the underlying recognition algorithm during Phase 2.
"""
from __future__ import annotations

from typing import Any

from src.core.database.compat_exports import export_legacy_student_csvs
from src.core.database.service import DatabaseService
from src.core.face_engine import FaceEngine
from src.ui import legacy_training_view

# The retained UI resolves FaceDetector from its module globals when it starts
# training. Point that name at the canonical facade before any instance is built.
legacy_training_view.FaceDetector = FaceEngine


class TrainingView(legacy_training_view.TrainingView):
    """Legacy training surface with canonical face/database dependencies."""

    def __init__(self, master, controller=None, **kwargs: Any) -> None:
        self.database = DatabaseService()
        export_legacy_student_csvs(self.database)
        super().__init__(master, controller=controller, **kwargs)

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
        """Close the database when the training view is destroyed."""
        try:
            self.database.close()
        finally:
            super().destroy()


__all__ = ["TrainingView"]
