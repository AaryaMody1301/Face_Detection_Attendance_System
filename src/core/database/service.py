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

    def _create_schema(self) -> None:
        """Create canonical objects without ``executescript`` transaction side effects."""
        statements = (
            """
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                enrollment TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                email TEXT,
                department TEXT,
                year TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_updated TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                subject_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Present',
                method TEXT NOT NULL DEFAULT 'face',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE RESTRICT,
                UNIQUE(student_id, subject_id, date)
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(date)",
            "CREATE INDEX IF NOT EXISTS idx_attendance_student ON attendance(student_id)",
            "CREATE INDEX IF NOT EXISTS idx_attendance_subject ON attendance(subject_id)",
        )
        for statement in statements:
            self.conn.execute(statement)
        self.conn.execute("INSERT OR IGNORE INTO subjects(name) VALUES ('General')")

    def _migrate_schema(self) -> None:
        """Wrap destructive legacy upgrades in an explicit SQLite transaction."""
        attendance_cols = (
            {
                row[1]
                for row in self.conn.execute("PRAGMA table_info(attendance)").fetchall()
            }
            if self._table_exists("attendance")
            else set()
        )
        student_cols = (
            {row[1] for row in self.conn.execute("PRAGMA table_info(students)").fetchall()}
            if self._table_exists("students")
            else set()
        )
        canonical = (
            {"id", "enrollment", "name", "is_active"}.issubset(student_cols)
            and {"student_id", "subject_id", "date", "time", "status"}.issubset(
                attendance_cols
            )
        )
        has_legacy_tables = any(
            self._table_exists(name)
            for name in ("students", "attendance", "subjects", "courses")
        )

        if canonical or not has_legacy_tables:
            super()._migrate_schema()
            return

        self.conn.execute("PRAGMA foreign_keys = OFF")
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            super()._migrate_schema()
        except Exception:
            if self.conn.in_transaction:
                self.conn.rollback()
            raise
        finally:
            if self.conn.in_transaction:
                self.conn.commit()
            self.conn.execute("PRAGMA foreign_keys = ON")

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
            "total_attendance": len(df),
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
