"""Database-backed public StudentRegistrationView.

The original capture/UI behavior remains in ``legacy_student_registration``;
only student persistence is replaced so registration writes to SQLite first and
legacy CSVs are regenerated from database state.
"""
from __future__ import annotations

from typing import Any

from src.core.database.compat_exports import export_legacy_student_csvs
from src.core.database.service import DatabaseService
from src.ui.legacy_student_registration import StudentRegistrationView as _LegacyStudentRegistrationView


class StudentRegistrationView(_LegacyStudentRegistrationView):
    """Legacy registration UI with canonical student persistence."""

    def __init__(self, master, **kwargs: Any) -> None:
        self.database = DatabaseService()
        super().__init__(master, **kwargs)

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
