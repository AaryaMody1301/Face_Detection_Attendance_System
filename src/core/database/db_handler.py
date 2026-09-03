"""Compatibility import for the canonical database service."""

from src.core.database.service import DatabaseHandler, DatabaseService

AttendanceRepository = DatabaseService

__all__ = ["AttendanceRepository", "DatabaseHandler", "DatabaseService"]
