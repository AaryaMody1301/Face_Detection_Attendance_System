"""Legacy EnhancedDB adapter for the canonical repository."""

from src.core.database.repository import AttendanceRepository


class EnhancedDB(AttendanceRepository):
    """Backward-compatible name for :class:`AttendanceRepository`."""


__all__ = ["EnhancedDB"]
