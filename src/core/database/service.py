"""Application-facing database service built on the canonical repository."""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

from src.core.database.repository import AttendanceRepository


class DatabaseService(AttendanceRepository):
    """Repository plus compatibility helpers used by legacy UI/model surfaces."""

    def student_exists(self, enrollment: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM students WHERE enrollment=? LIMIT 1",
            (str(enrollment),),
        ).fetchone()
        return row is not None

    def get_student_by_id(self, enrollment: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            """
            SELECT enrollment, name, email, department, year, is_active
            FROM students WHERE enrollment=?
            """,
            (str(enrollment),),
        ).fetchone()
        if row is None:
            return None
        return {
            "Enrollment": row[0],
            "Name": row[1],
            "email": row[2],
            "department": row[3],
            "year": row[4],
            "is_active": bool(row[5]),
        }

    def delete_student(self, enrollment: str) -> bool:
        try:
            with self.conn:
                cursor = self.conn.execute(
                    "DELETE FROM students WHERE enrollment=?",
                    (str(enrollment),),
                )
            return cursor.rowcount > 0
        except sqlite3.Error:
            return False

    def get_attendance_statistics(
        self,
        subject: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        df = self._attendance_dataframe(
            subject=subject,
            start_date=start_date,
            end_date=end_date,
        )
        if df.empty:
            return {
                "total_attendance": 0,
                "unique_students": 0,
                "attendance_by_date": {},
                "top_subjects": {},
            }
        return {
            "total_attendance": int(len(df)),
            "unique_students": int(df["Enrollment"].nunique()),
            "attendance_by_date": {
                str(key): int(value) for key, value in df.groupby("Date").size().items()
            },
            "top_subjects": {
                str(key): int(value)
                for key, value in df.groupby("Subject").size().sort_values(ascending=False).items()
            },
        }

    @staticmethod
    def _date_from_export_path(file_path: str | Path | None) -> str | None:
        if not file_path:
            return None
        match = re.search(r"\d{4}-\d{2}-\d{2}", Path(file_path).name)
        return match.group(0) if match else None

    def add_student_to_attendance(
        self,
        file_path: str | Path,
        enrollment: str,
        name: str,
        status: str = "Present",
    ) -> bool:
        return self.mark_attendance(
            enrollment,
            name,
            subject=self._subject_from_export_path(str(file_path)),
            date=self._date_from_export_path(file_path),
            file_path=str(file_path),
            status=status,
            method="manual",
        )

    def update_student_status(
        self,
        file_path: str | Path,
        enrollment: str,
        status: str,
    ) -> bool:
        subject = self._subject_from_export_path(str(file_path))
        date = self._date_from_export_path(file_path)
        if not subject or not date:
            return False
        try:
            with self.conn:
                cursor = self.conn.execute(
                    """
                    UPDATE attendance
                    SET status=?
                    WHERE student_id=(SELECT id FROM students WHERE enrollment=?)
                      AND subject_id=(SELECT id FROM subjects WHERE name=?)
                      AND date=?
                    """,
                    (status, str(enrollment), subject, date),
                )
            if cursor.rowcount:
                self.export_attendance_csv(file_path, subject=subject, date=date)
            return cursor.rowcount > 0
        except sqlite3.Error:
            return False

    def remove_student_from_attendance(
        self,
        file_path: str | Path,
        enrollment: str,
    ) -> bool:
        subject = self._subject_from_export_path(str(file_path))
        date = self._date_from_export_path(file_path)
        if not subject or not date:
            return False
        try:
            with self.conn:
                cursor = self.conn.execute(
                    """
                    DELETE FROM attendance
                    WHERE student_id=(SELECT id FROM students WHERE enrollment=?)
                      AND subject_id=(SELECT id FROM subjects WHERE name=?)
                      AND date=?
                    """,
                    (str(enrollment), subject, date),
                )
            self.export_attendance_csv(file_path, subject=subject, date=date)
            return cursor.rowcount > 0
        except sqlite3.Error:
            return False

    def update_attendance_record(self, file_path: str | Path, attendance_df: pd.DataFrame) -> bool:
        """Import an edited legacy export back through database writes.

        This is retained only for old attendance-editing screens. The CSV itself
        is never treated as authoritative: rows are validated and written to the
        database, then the export is regenerated from SQLite.
        """
        subject = self._subject_from_export_path(str(file_path)) or "General"
        date = self._date_from_export_path(file_path)
        if date is None:
            return False
        try:
            for _, row in attendance_df.iterrows():
                enrollment = str(row.get("Enrollment", "")).strip()
                name = str(row.get("Name", "")).strip()
                if not enrollment or not name:
                    continue
                if not self.mark_attendance(
                    enrollment,
                    name,
                    subject=subject,
                    date=str(row.get("Date", date)),
                    time=str(row.get("Time", "00:00:00")),
                    status=str(row.get("Status", "Present")),
                    method="manual-edit",
                ):
                    return False
            self.export_attendance_csv(file_path, subject=subject, date=date)
            return True
        except (KeyError, TypeError, ValueError):
            return False


DatabaseHandler = DatabaseService
