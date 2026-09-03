"""Local authentication for the desktop attendance application."""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.core.paths import CONFIG_DIR, ensure_runtime_dirs

logger = logging.getLogger(__name__)

_PASSWORD_SCHEME = "scrypt-v1"
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_DKLEN = 32
_SCRYPT_MAXMEM = 64 * 1024 * 1024
_MIN_PASSWORD_LENGTH = 10


@dataclass(frozen=True)
class AuthResult:
    """Result returned by user-management operations."""

    success: bool
    message: str
    user_data: dict[str, Any] | None = None


class AuthSystem:
    """Single local authentication service used by the supported UI."""

    def __init__(
        self,
        users_file: str | Path | None = None,
        db_connection: Any | None = None,
        require_login: bool = True,
        **_: Any,
    ) -> None:
        del db_connection
        ensure_runtime_dirs()
        self.users_file = Path(users_file or (CONFIG_DIR / "users.json")).expanduser().resolve()
        self.users_file.parent.mkdir(parents=True, exist_ok=True)
        self.require_login = bool(require_login)
        self.users: dict[str, dict[str, Any]] = {}
        self.current_user: dict[str, Any] | None = None
        self._load_users()

    @staticmethod
    def _public_user(username: str, record: dict[str, Any]) -> dict[str, Any]:
        hidden = {"password", "password_hash", "password_salt", "password_scheme"}
        result = {key: value for key, value in record.items() if key not in hidden}
        result["username"] = username
        return result

    def _load_users(self) -> None:
        if not self.users_file.is_file():
            self.users = {}
            return
        try:
            payload = json.loads(self.users_file.read_text(encoding="utf-8"))
            self.users = payload if isinstance(payload, dict) else {}
        except (OSError, json.JSONDecodeError) as exc:
            logger.error("Could not load authentication state: %s", exc)
            self.users = {}

    def _save_users(self) -> bool:
        temporary = self.users_file.with_suffix(self.users_file.suffix + ".tmp")
        try:
            temporary.write_text(json.dumps(self.users, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            os.replace(temporary, self.users_file)
            return True
        except OSError as exc:
            temporary.unlink(missing_ok=True)
            logger.error("Could not save authentication state: %s", exc)
            return False

    @staticmethod
    def _derive(password: str, salt: bytes) -> bytes:
        return hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=_SCRYPT_N,
            r=_SCRYPT_R,
            p=_SCRYPT_P,
            maxmem=_SCRYPT_MAXMEM,
            dklen=_SCRYPT_DKLEN,
        )

    @classmethod
    def _password_fields(cls, password: str) -> dict[str, Any]:
        if len(password) < _MIN_PASSWORD_LENGTH:
            raise ValueError(f"Password must be at least {_MIN_PASSWORD_LENGTH} characters long")
        salt = os.urandom(16)
        digest = cls._derive(password, salt)
        return {
            "password_scheme": _PASSWORD_SCHEME,
            "password_salt": base64.b64encode(salt).decode("ascii"),
            "password_hash": base64.b64encode(digest).decode("ascii"),
        }

    @classmethod
    def _verify_scrypt(cls, record: dict[str, Any], password: str) -> bool:
        try:
            salt = base64.b64decode(str(record["password_salt"]), validate=True)
            expected = base64.b64decode(str(record["password_hash"]), validate=True)
        except (KeyError, ValueError):
            return False
        actual = cls._derive(password, salt)
        return secrets.compare_digest(actual, expected)

    @staticmethod
    def _looks_like_sha256(value: str) -> bool:
        if len(value) != 64:
            return False
        try:
            int(value, 16)
        except ValueError:
            return False
        return True

    def _verify_and_migrate(self, username: str, password: str) -> bool:
        record = self.users.get(username)
        if record is None:
            return False

        if record.get("password_scheme") == _PASSWORD_SCHEME:
            return self._verify_scrypt(record, password)

        # Phase 1 removed committed credentials, but existing local installs may
        # still carry the older SHA-256 or plaintext JSON formats. Accept them
        # once, only after a correct password is supplied, then migrate in place.
        legacy = record.get("password")
        if not isinstance(legacy, str):
            return False
        if self._looks_like_sha256(legacy):
            candidate = hashlib.sha256(password.encode("utf-8")).hexdigest()
            valid = secrets.compare_digest(candidate, legacy)
        else:
            valid = secrets.compare_digest(password, legacy)
        if not valid:
            return False

        record.pop("password", None)
        record.update(self._password_fields(password))
        if not self._save_users():
            logger.warning("Authenticated legacy user %s but could not persist scrypt migration", username)
        return True

    def authenticate(self, username: str, password: str) -> AuthResult:
        username = username.strip()
        if not username or not self._verify_and_migrate(username, password):
            return AuthResult(False, "Invalid username or password")
        user = self._public_user(username, self.users[username])
        return AuthResult(True, "Authentication successful", user)

    def login(self, username: str, password: str) -> bool:
        result = self.authenticate(username, password)
        if not result.success:
            return False
        self.current_user = dict(result.user_data or {})
        logger.info("User %s logged in", username)
        return True

    def logout(self) -> bool:
        self.current_user = None
        return True

    def is_authenticated(self) -> bool:
        return self.current_user is not None

    def is_logged_in(self) -> bool:
        return self.is_authenticated()

    def get_current_user(self) -> dict[str, Any]:
        return dict(self.current_user or {})

    def _next_id(self) -> int:
        identifiers = [int(user.get("id", 0) or 0) for user in self.users.values()]
        return max(identifiers, default=0) + 1

    def create_user(
        self,
        username: str,
        password: str,
        role: str = "user",
        full_name: str | None = None,
        email: str | None = None,
        created_by: str | None = None,
        **_: Any,
    ) -> AuthResult:
        username = username.strip()
        if not username or not username.replace("_", "").isalnum():
            return AuthResult(False, "Username may contain only letters, numbers, and underscores")
        if username in self.users:
            return AuthResult(False, "Username already exists")
        if role not in {"admin", "teacher", "user"}:
            return AuthResult(False, "Unsupported role")
        try:
            password_fields = self._password_fields(password)
        except ValueError as exc:
            return AuthResult(False, str(exc))

        record: dict[str, Any] = {
            "id": self._next_id(),
            "role": role,
            "full_name": full_name or username,
            "created_at": datetime.now(UTC).isoformat(),
            **password_fields,
        }
        if email:
            record["email"] = email
        if created_by:
            record["created_by"] = created_by
        self.users[username] = record
        if not self._save_users():
            self.users.pop(username, None)
            return AuthResult(False, "Could not save user data")
        return AuthResult(True, "User created", self._public_user(username, record))

    def register(self, username: str, password: str, full_name: str, role: str = "user") -> bool:
        return self.create_user(username, password, role=role, full_name=full_name).success

    def update_user(self, username: str, new_data: dict[str, Any]) -> AuthResult:
        record = self.users.get(username)
        if record is None:
            return AuthResult(False, "User does not exist")
        for key in ("full_name", "email", "role"):
            if key in new_data:
                record[key] = new_data[key]
        if "password" in new_data:
            try:
                record.update(self._password_fields(str(new_data["password"])))
                record.pop("password", None)
            except ValueError as exc:
                return AuthResult(False, str(exc))
        if not self._save_users():
            return AuthResult(False, "Could not save user data")
        return AuthResult(True, "User updated", self._public_user(username, record))

    def _resolve_username(self, identifier: str | int) -> str | None:
        if isinstance(identifier, str) and identifier in self.users:
            return identifier
        for username, record in self.users.items():
            if record.get("id") == identifier:
                return username
        return None

    def get_user(self, identifier: str | int) -> dict[str, Any] | None:
        username = self._resolve_username(identifier)
        if username is None:
            return None
        return self._public_user(username, self.users[username])

    def get_all_users(self) -> dict[str, dict[str, Any]]:
        return {username: self._public_user(username, record) for username, record in self.users.items()}

    def delete_user(self, identifier: str | int) -> AuthResult:
        username = self._resolve_username(identifier)
        if username is None:
            return AuthResult(False, "User does not exist")
        if self.users[username].get("role") == "admin":
            admins = [record for record in self.users.values() if record.get("role") == "admin"]
            if len(admins) <= 1:
                return AuthResult(False, "Cannot delete the only administrator")
        self.users.pop(username)
        if not self._save_users():
            return AuthResult(False, "Could not save user data")
        if self.current_user and self.current_user.get("username") == username:
            self.logout()
        return AuthResult(True, "User deleted")

    def change_password(self, identifier: str | int, old_password: str, new_password: str) -> bool:
        username = self._resolve_username(identifier)
        if username is None or not self._verify_and_migrate(username, old_password):
            return False
        try:
            self.users[username].update(self._password_fields(new_password))
        except ValueError:
            return False
        self.users[username].pop("password", None)
        return self._save_users()

    def check_if_any_user_exists(self) -> bool:
        return bool(self.users)

    def has_permission(self, permission: str) -> bool:
        user = self.current_user or {}
        role = user.get("role")
        if role == "admin":
            return True
        allowed = {
            "teacher": {"take_attendance", "view_attendance", "manage_students"},
            "user": {"view_attendance"},
        }
        return permission in allowed.get(str(role), set())

    def login_as_default_user(self) -> bool:
        """Guest/default authentication is intentionally disabled in production."""
        return False


__all__ = ["AuthResult", "AuthSystem"]
