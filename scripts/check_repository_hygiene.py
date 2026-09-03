"""Fail when unsafe runtime data or production placeholders are tracked."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

FORBIDDEN_PREFIXES = (
    "Attendance/",
    "Data/",
    "StudentDetails/",
    "TrainingImage/",
    "TrainingImageLabel/",
    "backups/",
    "src/data/training_images/",
)
FORBIDDEN_EXACT = {
    "attendance.db",
    "config/credentials.json",
    "config/users.json",
    "data/students.csv",
    "src/models/face_recognizer.yml",
}
FORBIDDEN_SUFFIXES = (".db", ".sqlite", ".sqlite3")
FORBIDDEN_SOURCE_SNIPPETS = {
    'auth_system.login("admin", "admin")': "test-only automatic admin login",
    "aws_access_key='your-access-key'": "placeholder AWS credential",
    "aws_secret_key='your-secret-key'": "placeholder AWS credential",
    "from src.utils.cloud_sync import CloudSync": "retired cloud integration import",
}


def tracked_files() -> list[str]:
    result = subprocess.run(["git", "ls-files"], check=True, capture_output=True, text=True)
    return [line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]


def main() -> int:
    violations: list[str] = []
    tracked = tracked_files()
    for path in tracked:
        if path in FORBIDDEN_EXACT:
            violations.append(path)
            continue
        if path.startswith(FORBIDDEN_PREFIXES):
            violations.append(path)
            continue
        if path.lower().endswith(FORBIDDEN_SUFFIXES):
            violations.append(path)

    for path in tracked:
        if not path.endswith((".py", ".json", ".yml", ".yaml")):
            continue
        try:
            text = Path(path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for snippet, reason in FORBIDDEN_SOURCE_SNIPPETS.items():
            if snippet in text:
                violations.append(f"{path}: {reason}")

    if violations:
        print("Repository hygiene check failed:")
        for path in sorted(set(violations)):
            print(f"  - {path}")
        return 1

    print("Repository hygiene check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
