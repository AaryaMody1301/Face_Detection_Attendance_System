"""Legacy SQLiteHandler adapter for the canonical database service."""

from src.core.database.service import DatabaseService


class SQLiteHandler(DatabaseService):
    """Backward-compatible name for :class:`DatabaseService`."""


__all__ = ["SQLiteHandler"]
