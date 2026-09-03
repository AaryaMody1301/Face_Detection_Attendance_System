"""Pure reporting helpers shared by the production dashboard and analytics views."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

_PERIOD_DAYS = {
    "week": 7,
    "month": 30,
    "semester": 180,
    "year": 365,
}


@dataclass(frozen=True)
class DashboardSnapshot:
    """Database-backed values rendered by the main dashboard."""

    total_records: int
    enrolled_students: int
    today_records: int
    subject_count: int
    attendance_by_date: tuple[tuple[str, int], ...]
    attendance_by_subject: tuple[tuple[str, int], ...]
    recent_records: tuple[dict[str, str], ...]


def period_start(period: str, *, today: date | None = None) -> str | None:
    """Return an inclusive ISO start date for a named reporting period."""
    key = period.strip().lower()
    if key in {"all", "all time", ""}:
        return None
    days = _PERIOD_DAYS.get(key)
    if days is None:
        raise ValueError(f"Unsupported reporting period: {period}")
    anchor = today or date.today()
    return (anchor - timedelta(days=days - 1)).isoformat()


def load_analytics_data(
    db: Any,
    *,
    subject: str | None = None,
    period: str = "month",
    today: date | None = None,
) -> pd.DataFrame:
    """Load filtered attendance from the canonical database service."""
    selected_subject = None if subject in (None, "", "All") else subject
    start_date = period_start(period, today=today)
    frame = db._attendance_dataframe(subject=selected_subject, start_date=start_date)
    return frame.copy()


def build_dashboard_snapshot(
    db: Any,
    *,
    trend_period: str = "week",
    today: date | None = None,
    recent_limit: int = 8,
) -> DashboardSnapshot:
    """Build a complete dashboard snapshot from SQLite-backed service methods."""
    anchor = today or date.today()
    all_attendance = db._attendance_dataframe()
    students = db.get_student_details()
    subjects = db.get_subjects()

    if all_attendance.empty:
        return DashboardSnapshot(
            total_records=0,
            enrolled_students=int(len(students)),
            today_records=0,
            subject_count=int(len(subjects)),
            attendance_by_date=(),
            attendance_by_subject=(),
            recent_records=(),
        )

    normalized = all_attendance.copy()
    normalized["Date"] = normalized["Date"].astype(str)
    today_records = int((normalized["Date"] == anchor.isoformat()).sum())

    start_date = period_start(trend_period, today=anchor)
    trend = normalized
    if start_date is not None:
        trend = trend[trend["Date"] >= start_date]

    by_date = tuple(
        (str(day), int(count))
        for day, count in trend.groupby("Date").size().sort_index().items()
    )
    by_subject = tuple(
        (str(subject_name), int(count))
        for subject_name, count in (
            normalized.groupby("Subject").size().sort_values(ascending=False).head(8).items()
        )
    )

    recent_columns = ["Name", "Subject", "Date", "Time", "Status"]
    recent_records = tuple(
        {column: str(row.get(column, "")) for column in recent_columns}
        for row in normalized.head(max(0, recent_limit)).to_dict("records")
    )

    return DashboardSnapshot(
        total_records=int(len(normalized)),
        enrolled_students=int(len(students)),
        today_records=today_records,
        subject_count=int(len(subjects)),
        attendance_by_date=by_date,
        attendance_by_subject=by_subject,
        recent_records=recent_records,
    )


def export_attendance_data(frame: pd.DataFrame, destination: str | Path) -> Path:
    """Export the currently filtered analytics dataset to CSV."""
    path = Path(destination).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = ["Enrollment", "Name", "Subject", "Date", "Time", "Status", "Method"]
    frame.reindex(columns=columns).to_csv(path, index=False)
    return path
