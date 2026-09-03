from __future__ import annotations

import json

from src.auth.auth_system import AuthSystem


def test_passwords_are_stored_as_salted_scrypt(tmp_path):
    users_file = tmp_path / "users.json"
    auth = AuthSystem(users_file=users_file)

    result = auth.create_user(
        "admin",
        "correct-horse-battery-staple",
        role="admin",
        full_name="Administrator",
    )

    assert result.success is True
    payload = json.loads(users_file.read_text(encoding="utf-8"))
    record = payload["admin"]
    assert record["password_scheme"] == "scrypt-v1"
    assert "password" not in record
    assert "correct-horse-battery-staple" not in users_file.read_text(encoding="utf-8")
    assert auth.login("admin", "correct-horse-battery-staple") is True
    assert auth.get_current_user()["role"] == "admin"
    assert auth.login("admin", "wrong-password") is False


def test_legacy_plaintext_password_is_migrated_after_successful_login(tmp_path):
    users_file = tmp_path / "users.json"
    users_file.write_text(
        json.dumps(
            {
                "legacy": {
                    "id": 1,
                    "password": "legacy-password",
                    "role": "admin",
                    "full_name": "Legacy Admin",
                }
            }
        ),
        encoding="utf-8",
    )

    auth = AuthSystem(users_file=users_file)
    assert auth.login("legacy", "legacy-password") is True

    record = json.loads(users_file.read_text(encoding="utf-8"))["legacy"]
    assert "password" not in record
    assert record["password_scheme"] == "scrypt-v1"
    assert "password_hash" in record
    assert "password_salt" in record
