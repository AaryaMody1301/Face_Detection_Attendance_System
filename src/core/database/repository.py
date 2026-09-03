"""Canonical SQLite repository for students, subjects, and attendance.

SQLite is the source of truth. CSV files are generated only as derived exports
for compatibility with older UI/CLI flows.
"""
from __future__ import annotations

import logging
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

import pandas as pd

from src.core.paths import (
    ATTENDANCE_EXPORTS_DIR,
    DATABASE_PATH,
    STUDENT_EXPORTS_DIR,
    ensure_runtime_dirs,
)

logger = logging.getLogger(__name__)
SCHEMA_VERSION = 2


class AttendanceRepository:
    """Single database service used by every application surface."""

    def __init__(self, db_path: str | Path | None = None, base_dir: str | Path | None = None, **_: Any):
        ensure_runtime_dirs()

        if db_path is None and base_dir is not None:
            db_path = Path(base_dir) / "Data" / "attendance.db"
        self.db_path = str(Path(db_path or DATABASE_PATH).expanduser().resolve())
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        # Compatibility attributes used by older tests and UI modules.
        export_root = Path(base_dir).resolve() if base_dir is not None else Path(self.db_path).parent / "exports"
        self.student_details_dir = str(export_root / "StudentDetails")
        self.attendance_dir = str(export_root / "Attendance")
        Path(self.student_details_dir).mkdir(parents=True, exist_ok=True)
        Path(self.attendance_dir).mkdir(parents=True, exist_ok=True)

        self._lock = threading.RLock()
        self.conn = sqlite3.connect(
            self.db_path,
            timeout=30.0,
            check_same_thread=False,
        )
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self._configure_connection()
        self._migrate_schema()

    @property
    def connection(self) -> sqlite3.Connection:
        """Compatibility alias used by the former EnhancedDB implementation."""
        return self.conn

    def _configure_connection(self) -> None:
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA busy_timeout = 30000")
        self.conn.execute("PRAGMA journal_mode = WAL")

    def _table_exists(self, name: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (name,),
        ).fetchone()
        return row is not None

    def _create_schema(self) -> None:
        self.conn.executescript(
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
            );

            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

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
            );

            CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(date);
            CREATE INDEX IF NOT EXISTS idx_attendance_student ON attendance(student_id);
            CREATE INDEX IF NOT EXISTS idx_attendance_subject ON attendance(subject_id);
            """
        )
        self.conn.execute("INSERT OR IGNORE INTO subjects(name) VALUES ('General')")

    @staticmethod
    def _row_value(row: dict[str, Any], *names: str, default: Any = None) -> Any:
        for name in names:
            if name in row and row[name] not in (None, ""):
                return row[name]
        return default

    def _read_table(self, name: str) -> list[dict[str, Any]]:
        if not self._table_exists(name):
            return []
        return [dict(row) for row in self.conn.execute(f'SELECT * FROM "{name}"').fetchall()]

    def _migrate_schema(self) -> None:
        """Migrate known legacy schemas to the canonical schema atomically."""
        attendance_cols = {
            row[1] for row in self.conn.execute("PRAGMA table_info(attendance)").fetchall()
        } if self._table_exists("attendance") else set()
        student_cols = {
            row[1] for row in self.conn.execute("PRAGMA table_info(students)").fetchall()
        } if self._table_exists("students") else set()

        canonical = (
            {"id", "enrollment", "name", "is_active"}.issubset(student_cols)
            and {"student_id", "subject_id", "date", "time", "status"}.issubset(attendance_cols)
        )
        if canonical:
            self._create_schema()
            self.conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            self.conn.commit()
            return

        if not any(self._table_exists(name) for name in ("students", "attendance", "subjects", "courses")):
            with self.conn:
                self._create_schema()
                self.conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            return

        legacy_students = self._read_table("students")
        legacy_attendance = self._read_table("attendance")
        legacy_subjects = self._read_table("subjects")
        legacy_courses = self._read_table("courses")

        student_id_to_enrollment: dict[str, str] = {}
        course_id_to_name: dict[str, str] = {}
        for row in legacy_courses:
            course_id = str(self._row_value(row, "id", default="")).strip()
            course_name = str(self._row_value(row, "name", default=course_id or "General")).strip()
            if course_id:
                course_id_to_name[course_id] = course_name

        self.conn.execute("PRAGMA foreign_keys = OFF")
        try:
            with self.conn:
                # Drop only the competing legacy data tables. Authentication tables are untouched.
                for table in ("attendance", "subjects", "courses", "students"):
                    if self._table_exists(table):
                        self.conn.execute(f'DROP TABLE "{table}"')
                self._create_schema()

                for row in legacy_students:
                    legacy_id = str(self._row_value(row, "id", default="")).strip()
                    enrollment = str(
                        self._row_value(row, "enrollment", "student_id", "id", default="")
                    ).strip()
                    name = str(self._row_value(row, "name", "full_name", default=enrollment)).strip()
                    if not enrollment:
                        continue
                    self.conn.execute(
                        """
                        INSERT OR IGNORE INTO students(
                            enrollment, name, email, department, year, created_at, last_updated, is_active
                        ) VALUES (?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP), COALESCE(?, CURRENT_TIMESTAMP), ?)
                        """,
                        (
                            enrollment,
                            name or enrollment,
                            self._row_value(row, "email"),
                            self._row_value(row, "department", "program"),
                            self._row_value(row, "year"),
                            self._row_value(row, "created_at", "enrollment_date"),
                            self._row_value(row, "last_updated", "updated_at", "last_modified"),
                            int(self._row_value(row, "is_active", "active", default=1) or 0),
                        ),
                    )
                    if legacy_id:
                        student_id_to_enrollment[legacy_id] = enrollment

                subject_names = {
                    str(self._row_value(row, "name", default="")).strip()
                    for row in legacy_subjects
                }
                subject_names.update(name for name in course_id_to_name.values() if name)
                for row in legacy_attendance:
                    direct = str(self._row_value(row, "subject", default="")).strip()
                    course_id = str(self._row_value(row, "course_id", default="")).strip()
                    if direct:
                        subject_names.add(direct)
                    elif course_id:
                        subject_names.add(course_id_to_name.get(course_id, course_id))
                subject_names.add("General")
                self.conn.executemany(
                    "INSERT OR IGNORE INTO subjects(name) VALUES (?)",
                    [(name,) for name in sorted(name for name in subject_names if name)],
                )

                for row in legacy_attendance:
                    enrollment = str(self._row_value(row, "enrollment", default="")).strip()
                    legacy_student_id = str(self._row_value(row, "student_id", default="")).strip()
                    if not enrollment and legacy_student_id:
                        enrollment = student_id_to_enrollment.get(legacy_student_id, legacy_student_id)
                    if not enrollment:
                        continue

                    student = self.conn.execute(
                        "SELECT id FROM students WHERE enrollment=?",
                        (enrollment,),
                    ).fetchone()
                    if student is None:
                        legacy_name = str(self._row_value(row, "name", default=enrollment)).strip()
                        self.conn.execute(
                            "INSERT OR IGNORE INTO students(enrollment, name) VALUES (?, ?)",
                            (enrollment, legacy_name or enrollment),
                        )
                        student = self.conn.execute(
                            "SELECT id FROM students WHERE enrollment=?",
                            (enrollment,),
                        ).fetchone()
                    if student is None:
                        continue

                    subject = str(self._row_value(row, "subject", default="")).strip()
                    course_id = str(self._row_value(row, "course_id", default="")).strip()
                    if not subject:
                        subject = course_id_to_name.get(course_id, course_id) if course_id else "General"
                    self.conn.execute("INSERT OR IGNORE INTO subjects(name) VALUES (?)", (subject,))
                    subject_row = self.conn.execute(
                        "SELECT id FROM subjects WHERE name=?",
                        (subject,),
                    ).fetchone()
                    date = str(self._row_value(row, "date", default="")).strip()
                    time_value = str(self._row_value(row, "time", default="00:00:00")).strip()
                    if not date or subject_row is None:
                        continue
                    self.conn.execute(
                        """
                        INSERT OR IGNORE INTO attendance(
                            student_id, subject_id, date, time, status, method
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            student[0],
                            subject_row[0],
                            date,
                            time_value or "00:00:00",
                            str(self._row_value(row, "status", default="Present")),
                            str(self._row_value(row, "method", default="legacy")),
                        ),
                    )

                self.conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        finally:
            self.conn.execute("PRAGMA foreign_keys = ON")

        violations = self.conn.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise sqlite3.IntegrityError(f"Foreign-key violations after migration: {violations}")
        logger.info("Migrated database to schema version %s", SCHEMA_VERSION)

    @contextmanager
    def get_connection(self) -> Iterator[sqlite3.Connection]:
        """Yield the canonical connection for legacy manager callers."""
        with self._lock:
            yield self.conn

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Execute a transaction with automatic rollback on failure."""
        with self._lock:
            try:
                self.conn.execute("BEGIN")
                yield self.conn
                self.conn.commit()
            except Exception:
                self.conn.rollback()
                raise

    def execute_query(
        self,
        query: str,
        params: tuple[Any, ...] = (),
        fetch_all: bool = False,
        fetch_one: bool = False,
        commit: bool = False,
        use_cache: bool = False,
    ) -> Any:
        """Execute SQL for compatibility with the former DatabaseManager API."""
        del use_cache
        with self._lock:
            cursor = self.conn.execute(query, params)
            if commit:
                self.conn.commit()
            if fetch_one:
                return cursor.fetchone()
            if fetch_all:
                return cursor.fetchall()
            return cursor.rowcount

    def add_student(self, enrollment: str, name: str, **fields: Any) -> bool:
        try:
            with self.conn:
                self.conn.execute(
                    """
                    INSERT INTO students(enrollment, name, email, department, year)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(enrollment) DO UPDATE SET
                        name=excluded.name,
                        email=COALESCE(excluded.email, students.email),
                        department=COALESCE(excluded.department, students.department),
                        year=COALESCE(excluded.year, students.year),
                        last_updated=CURRENT_TIMESTAMP,
                        is_active=1
                    """,
                    (
                        str(enrollment),
                        str(name),
                        fields.get("email"),
                        fields.get("department"),
                        fields.get("year"),
                    ),
                )
            return True
        except sqlite3.Error as exc:
            logger.error("Error adding student %s: %s", enrollment, exc)
            return False

    def get_student_details(self, enrollment: str | None = None) -> pd.DataFrame:
        query = "SELECT enrollment AS Enrollment, name AS Name, email, department, year, is_active FROM students"
        params: list[Any] = []
        if enrollment:
            query += " WHERE enrollment = ?"
            params.append(enrollment)
        query += " ORDER BY Name"
        return pd.read_sql_query(query, self.conn, params=params)

    def _get_or_create_subject_id(self, subject: str) -> int:
        subject = subject.strip() or "General"
        self.conn.execute("INSERT OR IGNORE INTO subjects(name) VALUES (?)", (subject,))
        row = self.conn.execute("SELECT id FROM subjects WHERE name=?", (subject,)).fetchone()
        if row is None:
            raise sqlite3.IntegrityError(f"Could not create subject: {subject}")
        return int(row[0])

    def mark_attendance(
        self,
        enrollment: str,
        name: str,
        subject: str | None = None,
        date: str | None = None,
        time: str | None = None,
        time_str: str | None = None,
        file_path: str | None = None,
        status: str = "Present",
        method: str = "face",
        confidence: float | None = None,
        **_: Any,
    ) -> bool:
        del confidence
        now = datetime.now()
        date = date or now.strftime("%Y-%m-%d")
        time_value = time or time_str or now.strftime("%H:%M:%S")
        subject = subject or self._subject_from_export_path(file_path) or "General"

        if not self.add_student(enrollment, name):
            return False
        try:
            with self.conn:
                student = self.conn.execute(
                    "SELECT id FROM students WHERE enrollment=?",
                    (str(enrollment),),
                ).fetchone()
                if student is None:
                    return False
                subject_id = self._get_or_create_subject_id(subject)
                self.conn.execute(
                    """
                    INSERT INTO attendance(student_id, subject_id, date, time, status, method)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(student_id, subject_id, date) DO UPDATE SET
                        time=excluded.time,
                        status=excluded.status,
                        method=excluded.method
                    """,
                    (student[0], subject_id, date, time_value, status, method),
                )
            if file_path:
                self.export_attendance_csv(file_path, subject=subject, date=date)
            return True
        except sqlite3.Error as exc:
            logger.error("Error marking attendance for %s: %s", enrollment, exc)
            return False

    @staticmethod
    def _subject_from_export_path(file_path: str | None) -> str | None:
        if not file_path:
            return None
        stem = Path(file_path).stem
        return stem.split("_", 1)[0] if stem else None

    def create_attendance_record(self, subject: str, date: str | None = None, time: str | None = None, time_str: str | None = None) -> str:
        """Create a derived CSV export path for a legacy attendance session."""
        now = datetime.now()
        date = date or now.strftime("%Y-%m-%d")
        time_value = time or time_str or now.strftime("%H-%M-%S")
        safe_time = time_value.replace(":", "-")
        path = Path(self.attendance_dir) / f"{subject}_{date}_{safe_time}.csv"
        self.export_attendance_csv(path, subject=subject, date=date)
        return str(path)

    def _attendance_dataframe(
        self,
        subject: str | None = None,
        date: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        enrollment: str | None = None,
    ) -> pd.DataFrame:
        query = """
            SELECT s.enrollment AS Enrollment, s.name AS Name, sub.name AS Subject,
                   a.date AS Date, a.time AS Time, a.status AS Status, a.method AS Method
            FROM attendance a
            JOIN students s ON s.id = a.student_id
            JOIN subjects sub ON sub.id = a.subject_id
            WHERE 1=1
        """
        params: list[Any] = []
        if subject:
            query += " AND sub.name = ?"
            params.append(subject)
        if date:
            query += " AND a.date = ?"
            params.append(date)
        if start_date:
            query += " AND a.date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND a.date <= ?"
            params.append(end_date)
        if enrollment:
            query += " AND s.enrollment = ?"
            params.append(enrollment)
        query += " ORDER BY a.date DESC, a.time DESC, s.name"
        return pd.read_sql_query(query, self.conn, params=params)

    def get_attendance_records(
        self,
        subject: str | None = None,
        date: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        student_id: str | None = None,
        enrollment: str | None = None,
        **_: Any,
    ) -> dict[str, pd.DataFrame]:
        df = self._attendance_dataframe(
            subject=subject,
            date=date,
            start_date=start_date,
            end_date=end_date,
            enrollment=enrollment or student_id,
        )
        if df.empty:
            return {}
        records: dict[str, pd.DataFrame] = {}
        for (subject_name, day), group in df.groupby(["Subject", "Date"], sort=False):
            records[f"{subject_name}_{day}.csv"] = group.reset_index(drop=True)
        return records

    def get_all_attendance_records(self) -> dict[str, pd.DataFrame]:
        return self.get_attendance_records()

    def export_attendance_csv(
        self,
        file_path: str | Path | None = None,
        subject: str | None = None,
        date: str | None = None,
        enrollment: str | None = None,
    ) -> str:
        """Regenerate a CSV export from the database source of truth."""
        df = self._attendance_dataframe(subject=subject, date=date, enrollment=enrollment)
        if file_path is None:
            stem = subject or "attendance"
            suffix = date or datetime.now().strftime("%Y-%m-%d")
            file_path = ATTENDANCE_EXPORTS_DIR / f"{stem}_{suffix}.csv"
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        columns = ["Enrollment", "Name", "Date", "Time", "Status"]
        export_df = df.reindex(columns=columns) if not df.empty else pd.DataFrame(columns=columns)
        export_df.to_csv(path, index=False)
        return str(path)

    def export_students_csv(self, file_path: str | Path | None = None) -> str:
        df = self.get_student_details()[["Enrollment", "Name"]]
        path = Path(file_path or (STUDENT_EXPORTS_DIR / "StudentDetails.csv"))
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False)
        return str(path)

    def get_attendance_record(self, file_path: str | Path) -> pd.DataFrame | None:
        path = Path(file_path)
        if not path.is_file():
            return None
        return pd.read_csv(path)

    def add_subject(self, name: str) -> bool:
        try:
            with self.conn:
                self.conn.execute("INSERT OR IGNORE INTO subjects(name) VALUES (?)", (name.strip(),))
            return True
        except sqlite3.Error as exc:
            logger.error("Error adding subject %s: %s", name, exc)
            return False

    def get_subjects(self) -> list[str]:
        rows = self.conn.execute("SELECT name FROM subjects ORDER BY name").fetchall()
        return [str(row[0]) for row in rows]

    def remove_subject(self, name: str) -> bool:
        try:
            with self.conn:
                used = self.conn.execute(
                    """
                    SELECT 1 FROM attendance a
                    JOIN subjects s ON s.id = a.subject_id
                    WHERE s.name=? LIMIT 1
                    """,
                    (name,),
                ).fetchone()
                if used:
                    return False
                self.conn.execute("DELETE FROM subjects WHERE name=?", (name,))
            return True
        except sqlite3.Error as exc:
            logger.error("Error removing subject %s: %s", name, exc)
            return False

    def optimize_database(self, force: bool = False) -> bool:
        del force
        try:
            with self._lock:
                self.conn.execute("PRAGMA optimize")
            return True
        except sqlite3.Error as exc:
            logger.error("Database optimization failed: %s", exc)
            return False

    def close(self) -> None:
        with self._lock:
            if self.conn:
                self.conn.close()


DatabaseHandler = AttendanceRepository
