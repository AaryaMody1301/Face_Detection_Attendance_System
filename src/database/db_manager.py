"""Legacy DatabaseManager adapter for the canonical database service."""

from src.core.database.service import DatabaseService


class DatabaseManager(DatabaseService):
    """Backward-compatible manager exposing the canonical query API."""


__all__ = ["DatabaseManager"]
