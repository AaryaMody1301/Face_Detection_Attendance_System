"""Legacy AttendanceDB adapter for the canonical database service."""

from src.core.database.service import DatabaseService


class AttendanceDB(DatabaseService):
    """Backward-compatible name for :class:`DatabaseService`."""


__all__ = ["AttendanceDB"]
