"""Canonical runtime paths for the application.

All mutable application data should live below ``DATA_ROOT``. The location can
be overridden with ``FACE_ATTENDANCE_DATA_DIR`` for packaged or multi-user
installs while preserving the repository's historical ``Data`` default.
"""
from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = Path(
    os.environ.get("FACE_ATTENDANCE_DATA_DIR", PROJECT_ROOT / "Data")
).expanduser().resolve()

DATABASE_PATH = DATA_ROOT / "attendance.db"
EXPORTS_DIR = DATA_ROOT / "exports"
ATTENDANCE_EXPORTS_DIR = EXPORTS_DIR / "attendance"
STUDENT_EXPORTS_DIR = EXPORTS_DIR / "students"
TRAINING_IMAGES_DIR = DATA_ROOT / "training_images"
TRAINING_MODELS_DIR = DATA_ROOT / "models"
LOGS_DIR = DATA_ROOT / "logs"


def ensure_runtime_dirs() -> None:
    """Create canonical mutable-data directories if they do not yet exist."""
    for path in (
        DATA_ROOT,
        EXPORTS_DIR,
        ATTENDANCE_EXPORTS_DIR,
        STUDENT_EXPORTS_DIR,
        TRAINING_IMAGES_DIR,
        TRAINING_MODELS_DIR,
        LOGS_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)
