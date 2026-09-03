"""Legacy EnhancedDB adapter for the canonical database service."""

from src.core.database.service import DatabaseService


class EnhancedDB(DatabaseService):
    """Backward-compatible name for :class:`DatabaseService`."""


__all__ = ["EnhancedDB"]
