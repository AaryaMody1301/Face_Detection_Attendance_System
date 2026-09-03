"""Phase 2 tests for the canonical database service."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from src.core.database.repository import SCHEMA_VERSION
from src.core.database.service import DatabaseService
from src.database.db_handler import AttendanceDB
from src.database.db_manager import DatabaseManager
from src.database.enhanced_db import EnhancedDB
from src.database.sqlite_handler import SQLiteHandler


def test_legacy_database_names_share_one_service():
    assert issubclass(AttendanceDB, DatabaseService)
    assert issubclass(DatabaseManager, DatabaseService)
    assert issubclass(EnhancedDB, DatabaseService)
    assert issubclass(SQLiteHandler, DatabaseService)


def test_fresh_database_enables_integrity_and_unique_attendance(tmp_path: Path):
    db = DatabaseService(db_path=tmp_path / "attendance.db")
    try:
        assert db.conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert db.conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
        assert db.conn.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION

        assert db.add_student("A001", "Ada")
        assert db.mark_attendance(
            "A001", "Ada", subject="Python", date="2026-09-03", time="09:00:00"
        )
        assert db.mark_attendance(
            "A001",
            "Ada",
            subject="Python",
            date="2026-09-03",
            time="09:05:00",
            status="Late",
        )

        rows = db.conn.execute("SELECT time, status FROM attendance").fetchall()
        assert len(rows) == 1
        assert tuple(rows[0]) == ("09:05:00", "Late")
        assert db.conn.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        db.close()


def test_legacy_schema_is_migrated_without_losing_attendance(tmp_path: Path):
    db_path = tmp_path / "legacy.db"
    legacy = sqlite3.connect(db_path)
    legacy.executescript(
        """
        CREATE TABLE students (
            id INTEGER PRIMARY KEY,
            enrollment TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL
        );
        CREATE TABLE subjects (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL
        );
        CREATE TABLE attendance (
            id INTEGER PRIMARY KEY,
            student_id INTEGER,
            subject TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL
        );
        INSERT INTO students(id, enrollment, name) VALUES (7, 'S007', 'Grace');
        INSERT INTO subjects(id, name) VALUES (1, 'Databases');
        INSERT INTO attendance(student_id, subject, date, time)
        VALUES (7, 'Databases', '2026-09-02', '10:15:00');
        """
    )
    legacy.commit()
    legacy.close()

    db = DatabaseService(db_path=db_path)
    try:
        assert db.conn.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
        student = db.get_student_by_id("S007")
        assert student is not None
        assert student["Name"] == "Grace"

        records = db.get_attendance_records(subject="Databases", date="2026-09-02")
        assert len(records) == 1
        exported_group = next(iter(records.values()))
        assert exported_group.iloc[0]["Enrollment"] == "S007"
        assert db.conn.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        db.close()


def test_csv_is_regenerated_from_database_source_of_truth(tmp_path: Path):
    db = DatabaseService(db_path=tmp_path / "attendance.db", base_dir=tmp_path)
    try:
        export_path = db.create_attendance_record(
            "Analytics", "2026-09-03", "11-00-00"
        )
        assert db.mark_attendance(
            "S100",
            "Lin",
            subject="Analytics",
            date="2026-09-03",
            time="11:00:00",
            file_path=export_path,
        )
        assert db.mark_attendance(
            "S100",
            "Lin",
            subject="Analytics",
            date="2026-09-03",
            time="11:10:00",
            file_path=export_path,
            status="Late",
        )

        exported = pd.read_csv(export_path)
        assert len(exported) == 1
        assert exported.iloc[0]["Status"] == "Late"
        assert exported.iloc[0]["Time"] == "11:10:00"
    finally:
        db.close()
