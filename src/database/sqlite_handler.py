"""Legacy SQLiteHandler adapter for the canonical repository."""

from src.core.database.repository import AttendanceRepository


class SQLiteHandler(AttendanceRepository):
    """Backward-compatible name for :class:`AttendanceRepository`."""


__all__ = ["SQLiteHandler"]
