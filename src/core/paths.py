"""Canonical resource and mutable-data paths for source and packaged builds."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from platformdirs import PlatformDirs

APP_NAME = "FaceDetectionAttendanceSystem"
APP_AUTHOR = "AaryaMody1301"
IS_FROZEN = bool(getattr(sys, "frozen", False))

_SOURCE_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = Path(getattr(sys, "_MEIPASS", _SOURCE_ROOT)).resolve()
ASSETS_ROOT = PROJECT_ROOT / "assets"
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "config.json"


def _resolve_data_root() -> Path:
    override = os.environ.get("FACE_ATTENDANCE_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()
    if IS_FROZEN:
        directories = PlatformDirs(APP_NAME, APP_AUTHOR, roaming=False)
        return Path(directories.user_data_dir).expanduser().resolve()
    return (_SOURCE_ROOT / "Data").resolve()


DATA_ROOT = _resolve_data_root()
DATABASE_PATH = DATA_ROOT / "attendance.db"
EXPORTS_DIR = DATA_ROOT / "exports"
ATTENDANCE_EXPORTS_DIR = EXPORTS_DIR / "attendance"
STUDENT_EXPORTS_DIR = EXPORTS_DIR / "students"
TRAINING_IMAGES_DIR = DATA_ROOT / "training_images"
TRAINING_MODELS_DIR = DATA_ROOT / "models"
LOGS_DIR = DATA_ROOT / "logs"
CONFIG_DIR = DATA_ROOT / "config"
BACKUPS_DIR = DATA_ROOT / "backups"

# Retained visual modules still reference these historical relative folders.
# In packaged/overridden-data mode the runtime bootstrap changes cwd to DATA_ROOT,
# keeping those writes inside the same per-user writable application directory.
LEGACY_TRAINING_IMAGES_DIR = DATA_ROOT / "TrainingImage"
LEGACY_TRAINING_MODELS_DIR = DATA_ROOT / "TrainingImageLabel"
LEGACY_ATTENDANCE_DIR = DATA_ROOT / "Attendance"
LEGACY_STUDENT_DETAILS_DIR = DATA_ROOT / "StudentDetails"


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
        CONFIG_DIR,
        BACKUPS_DIR,
        LEGACY_TRAINING_IMAGES_DIR,
        LEGACY_TRAINING_MODELS_DIR,
        LEGACY_ATTENDANCE_DIR,
        LEGACY_STUDENT_DETAILS_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)
