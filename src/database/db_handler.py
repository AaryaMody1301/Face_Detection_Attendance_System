"""Legacy AttendanceDB adapter for the canonical repository."""

from src.core.database.repository import AttendanceRepository


class AttendanceDB(AttendanceRepository):
    """Backward-compatible name for :class:`AttendanceRepository`."""


__all__ = ["AttendanceDB"]
