"""Compatibility aliases for the production authentication service."""

from src.auth.auth_system import AuthResult, AuthSystem

SimpleAuth = AuthSystem
SimpleAuthSystem = AuthSystem

__all__ = ["AuthResult", "AuthSystem", "SimpleAuth", "SimpleAuthSystem"]
