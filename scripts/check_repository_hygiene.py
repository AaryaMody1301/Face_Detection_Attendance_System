"""Fail when unsafe runtime data or retired production surfaces are tracked."""
from __future__ import annotations

import subprocess
import sys

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
    "src/auth/auth_manager.py",
    "src/auth/login_screen.py",
    "src/ui/app.py",
    "src/ui/classic_app.py",
    "src/ui/classic_launcher.py",
    "src/ui/dashboard.py",
    "src/ui/login_screen.py",
    "src/ui/login_view.py",
    "src/ui/login_window.py",
    "src/ui/main_view.py",
    "src/ui/main_window.py",
    "src/ui/student_portal.py",
    "src/ui/ui_selector.py",
    "src/utils/analytics_dashboard.py",
    "src/utils/attendance_analytics.py",
    "src/utils/cloud_sync.py",
    "src/utils/credentials_manager.py",
}
FORBIDDEN_SUFFIXES = (".db", ".sqlite", ".sqlite3")


def tracked_files() -> list[str]:
    result = subprocess.run(["git", "ls-files"], check=True, capture_output=True, text=True)
    return [line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]


def main() -> int:
    violations: list[str] = []
    for path in tracked_files():
        if path in FORBIDDEN_EXACT:
            violations.append(path)
            continue
        if path.startswith(FORBIDDEN_PREFIXES):
            violations.append(path)
            continue
        if path.lower().endswith(FORBIDDEN_SUFFIXES):
            violations.append(path)

    if violations:
        print("Repository hygiene check failed:")
        for path in sorted(set(violations)):
            print(f"  - {path}")
        return 1

    print("Repository hygiene check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
