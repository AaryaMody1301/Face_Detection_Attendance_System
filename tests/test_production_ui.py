"""Headless tests for production reporting and navigation policy."""
from __future__ import annotations

from datetime import date

import pandas as pd

from src.core.database.service import DatabaseService
from src.ui.access_policy import can_access_navigation
from src.ui.attendance_reporting import (
    build_dashboard_snapshot,
    export_attendance_data,
    load_analytics_data,
    period_start,
)


class _FakeAuth:
    def __init__(self, allowed: set[str]):
        self.allowed = allowed

    def has_permission(self, permission: str) -> bool:
        return permission in self.allowed


def test_navigation_policy_hides_and_blocks_privileged_surfaces():
    viewer = _FakeAuth({"view_attendance"})
    teacher = _FakeAuth({"view_attendance", "take_attendance", "manage_students"})
    admin = _FakeAuth(
        {"view_attendance", "take_attendance", "manage_students", "manage_settings"}
    )

    assert can_access_navigation(viewer, "Dashboard")
    assert can_access_navigation(viewer, "Analytics")
    assert not can_access_navigation(viewer, "Mark Attendance")
    assert not can_access_navigation(viewer, "Registration")
    assert not can_access_navigation(viewer, "Training")
    assert not can_access_navigation(viewer, "Settings")

    assert can_access_navigation(teacher, "Mark Attendance")
    assert can_access_navigation(teacher, "Registration")
    assert can_access_navigation(teacher, "Training")
    assert not can_access_navigation(teacher, "Settings")

    assert can_access_navigation(admin, "Settings")


def test_period_start_is_inclusive_and_supports_all_time():
    today = date(2026, 9, 3)
    assert period_start("week", today=today) == "2026-08-28"
    assert period_start("month", today=today) == "2026-08-05"
    assert period_start("all", today=today) is None


def test_dashboard_and_analytics_use_database_source_of_truth(tmp_path):
    db = DatabaseService(db_path=tmp_path / "attendance.db")
    try:
        assert db.mark_attendance(
            "S001", "Ada", subject="Python", date="2026-09-03", time="09:00:00"
        )
        assert db.mark_attendance(
            "S002", "Grace", subject="Python", date="2026-09-02", time="10:00:00"
        )
        assert db.mark_attendance(
            "S003", "Lin", subject="Databases", date="2026-08-01", time="11:00:00"
        )

        snapshot = build_dashboard_snapshot(db, trend_period="week", today=date(2026, 9, 3))
        assert snapshot.total_records == 3
        assert snapshot.enrolled_students == 3
        assert snapshot.today_records == 1
        assert dict(snapshot.attendance_by_date) == {"2026-09-02": 1, "2026-09-03": 1}
        assert dict(snapshot.attendance_by_subject) == {"Python": 2, "Databases": 1}
        assert snapshot.recent_records[0]["Name"] == "Ada"

        python_week = load_analytics_data(
            db,
            subject="Python",
            period="week",
            today=date(2026, 9, 3),
        )
        assert list(python_week["Enrollment"]) == ["S001", "S002"]
        assert set(python_week["Subject"]) == {"Python"}
    finally:
        db.close()


def test_export_attendance_data_exports_filtered_frame(tmp_path):
    frame = pd.DataFrame(
        [
            {
                "Enrollment": "S001",
                "Name": "Ada",
                "Subject": "Python",
                "Date": "2026-09-03",
                "Time": "09:00:00",
                "Status": "Present",
                "Method": "manual",
            }
        ]
    )
    destination = export_attendance_data(frame, tmp_path / "analytics.csv")
    exported = pd.read_csv(destination)
    assert list(exported.columns) == [
        "Enrollment",
        "Name",
        "Subject",
        "Date",
        "Time",
        "Status",
        "Method",
    ]
    assert exported.iloc[0]["Name"] == "Ada"
