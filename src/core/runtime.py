"""Runtime bootstrap helpers for source checkouts and frozen desktop builds."""
from __future__ import annotations

import importlib
import json
import os
import platform
import shutil
import sys
from importlib import metadata
from pathlib import Path
from typing import Any

from src.core.paths import (
    ASSETS_ROOT,
    CONFIG_DIR,
    DATA_ROOT,
    DEFAULT_CONFIG_PATH,
    IS_FROZEN,
    PROJECT_ROOT,
    ensure_runtime_dirs,
)
from src.core.version import get_version

SUPPORTED_APPLICATION_IMPORTS = (
    "src.auth.auth_system",
    "src.core.database.service",
    "src.core.face_engine",
    "src.core.liveness",
    "src.ui.access_policy",
    "src.ui.attendance_reporting",
    "src.ui.auth_gate",
    "src.ui.attendance_view",
    "src.ui.dashboard_view",
    "src.ui.analytics_dashboard",
    "src.ui.student_registration",
    "src.ui.training_view",
    "src.ui.settings",
    "src.ui.modern_app",
    "src.ui.modern_launcher",
)


def _copy_tree_if_available(source: Path, destination: Path) -> None:
    if not source.is_dir():
        return
    destination.mkdir(parents=True, exist_ok=True)
    for item in source.rglob("*"):
        relative = item.relative_to(source)
        target = destination / relative
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)


def prepare_runtime_environment() -> Path:
    """Create writable runtime state and seed bundled read-only resources."""
    ensure_runtime_dirs()

    if IS_FROZEN or os.environ.get("FACE_ATTENDANCE_DATA_DIR"):
        _copy_tree_if_available(ASSETS_ROOT, DATA_ROOT / "assets")
        runtime_config = CONFIG_DIR / "config.json"
        if DEFAULT_CONFIG_PATH.is_file() and not runtime_config.exists():
            shutil.copy2(DEFAULT_CONFIG_PATH, runtime_config)
        os.chdir(DATA_ROOT)

    return DATA_ROOT


def _package_version(distribution: str, import_name: str | None = None) -> str:
    try:
        return metadata.version(distribution)
    except metadata.PackageNotFoundError:
        if import_name:
            try:
                module = importlib.import_module(import_name)
                return str(getattr(module, "__version__", "unknown"))
            except ImportError:
                return "missing"
        return "unknown"


def application_import_self_test() -> dict[str, Any]:
    """Import every supported production surface without opening a GUI."""
    modules: dict[str, str] = {}
    for module_name in SUPPORTED_APPLICATION_IMPORTS:
        try:
            importlib.import_module(module_name)
            modules[module_name] = "ok"
        except Exception as exc:  # noqa: BLE001 - diagnostic boundary
            modules[module_name] = f"{type(exc).__name__}: {exc}"
    return {
        "ok": all(result == "ok" for result in modules.values()),
        "modules": modules,
    }


def runtime_diagnostics() -> dict[str, Any]:
    """Return headless diagnostics suitable for support logs and CI smoke tests."""
    writable = False
    probe = DATA_ROOT / ".write-test"
    try:
        probe.write_text("ok", encoding="utf-8")
        writable = True
    except OSError:
        writable = False
    finally:
        probe.unlink(missing_ok=True)

    return {
        "app_version": get_version(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "frozen": IS_FROZEN,
        "executable": sys.executable,
        "resource_root": str(PROJECT_ROOT),
        "data_root": str(DATA_ROOT),
        "data_root_writable": writable,
        "opencv": _package_version("opencv-contrib-python", "cv2"),
        "customtkinter": _package_version("customtkinter", "customtkinter"),
        "numpy": _package_version("numpy", "numpy"),
        "platformdirs": _package_version("platformdirs", "platformdirs"),
    }


def print_runtime_diagnostics() -> None:
    print(json.dumps(runtime_diagnostics(), indent=2, sort_keys=True))


__all__ = [
    "SUPPORTED_APPLICATION_IMPORTS",
    "application_import_self_test",
    "prepare_runtime_environment",
    "print_runtime_diagnostics",
    "runtime_diagnostics",
]
