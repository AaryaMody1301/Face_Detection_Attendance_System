"""Regression tests for the Phase 2 public UI compatibility adapters."""
from __future__ import annotations

import pandas as pd

from src.core.database.compat_exports import export_legacy_student_csvs
from src.core.database.service import DatabaseService
from src.ui.attendance_view import AttendanceView
from src.ui.legacy_attendance_view import AttendanceView as LegacyAttendanceView
from src.ui.legacy_student_registration import StudentRegistrationView as LegacyRegistrationView
from src.ui.student_registration import StudentRegistrationView


def test_public_attendance_view_overrides_legacy_persistence():
    assert issubclass(AttendanceView, LegacyAttendanceView)
    assert AttendanceView.mark_attendance is not LegacyAttendanceView.mark_attendance
    assert AttendanceView._save_attendance is not LegacyAttendanceView._save_attendance
    assert AttendanceView.load_students is not LegacyAttendanceView.load_students


def test_public_registration_view_overrides_legacy_persistence():
    assert issubclass(StudentRegistrationView, LegacyRegistrationView)
    assert StudentRegistrationView.save_student_details is not LegacyRegistrationView.save_student_details


def test_legacy_student_csvs_are_derived_from_sqlite(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    db = DatabaseService(db_path=tmp_path / "attendance.db")
    try:
        assert db.add_student("S42", "Ada", department="Computer Science", year="2026")
        student_details, face_data = export_legacy_student_csvs(db)

        details = pd.read_csv(student_details)
        face_rows = pd.read_csv(face_data)
        assert details.loc[0, "Name"] == "Ada"
        assert str(details.loc[0, "ID"]) == "S42"
        assert face_rows.loc[0, "Course"] == "Computer Science"
        assert str(face_rows.loc[0, "Year"]) == "2026"
    finally:
        db.close()
