"""Load retained UI code without restoring the removed dlib dependency."""
from __future__ import annotations

import importlib
import importlib.util
import sys
from types import ModuleType
from typing import Any


def _load_legacy_attendance_view() -> type[Any]:
    """Import the legacy visual class while neutralizing its unused hard import."""
    module_name = "face_recognition"
    has_dependency = importlib.util.find_spec(module_name) is not None
    if not has_dependency:
        sys.modules[module_name] = ModuleType(module_name)

    try:
        module = importlib.import_module("src.ui.legacy_attendance_view")
        return module.AttendanceView
    finally:
        if not has_dependency:
            sys.modules.pop(module_name, None)


LegacyAttendanceView = _load_legacy_attendance_view()

__all__ = ["LegacyAttendanceView"]
