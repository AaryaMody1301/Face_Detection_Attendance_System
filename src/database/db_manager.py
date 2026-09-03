"""Legacy DatabaseManager adapter for the canonical repository."""

from src.core.database.repository import AttendanceRepository


class DatabaseManager(AttendanceRepository):
    """Backward-compatible manager exposing the repository query API."""


__all__ = ["DatabaseManager"]
