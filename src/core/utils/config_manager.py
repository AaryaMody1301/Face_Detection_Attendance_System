"""Canonical configuration management for the desktop application."""
from __future__ import annotations

import copy
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.core.paths import CONFIG_DIR, DEFAULT_CONFIG_PATH, EXPORTS_DIR, ensure_runtime_dirs
from src.core.version import get_version

logger = logging.getLogger(__name__)


def _defaults() -> dict[str, Any]:
    return {
        "app": {"name": "Face Detection Attendance System", "version": get_version()},
        "ui": {
            "type": "modern",
            "theme": "system",
            "color_theme": "blue",
            "font_size": "medium",
            "animations": True,
        },
        "camera": {
            "device_id": 0,
            "id": 0,
            "resolution": {"width": 640, "height": 480},
            "fps": 30,
        },
        "face_detection": {
            "detection_method": "yunet",
            "confidence_threshold": 0.90,
            "min_face_size": 20,
        },
        "face_recognition": {
            "method": "sface",
            "threshold": 0.363,
            "multi_detection": True,
        },
        "liveness": {
            "enabled": True,
            "threshold": 0.50,
            "window": 5,
            "required_live_frames": 3,
        },
        "attendance": {
            "auto_export_csv": True,
            "duplicate_timeout": 600,
            "default_subject": "General",
        },
        "backup": {
            "auto_backup": True,
            "frequency_days": 7,
            "retention_days": 30,
        },
        "training": {"max_images": 50, "interval": 0.5},
    }


def _deep_update(target: dict[str, Any], source: dict[str, Any]) -> None:
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_update(target[key], value)
        else:
            target[key] = value


class ConfigManager:
    """Load and persist user configuration under the canonical data root."""

    def __init__(self, config_file: str | Path | None = None, config_path: str | Path | None = None):
        ensure_runtime_dirs()
        requested = config_path if config_path is not None else config_file
        self.config_file = Path(requested or (CONFIG_DIR / "config.json")).expanduser().resolve()
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.defaults = _defaults()
        self.config: dict[str, Any] = {}
        self.load()

    def _seed_config(self) -> dict[str, Any]:
        config = copy.deepcopy(self.defaults)
        if DEFAULT_CONFIG_PATH.is_file() and DEFAULT_CONFIG_PATH.resolve() != self.config_file:
            try:
                seed = json.loads(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
                if isinstance(seed, dict):
                    _deep_update(config, seed)
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning("Could not read bundled config seed: %s", exc)
        return config

    def _normalize(self) -> None:
        _deep_update(self.config, {})
        defaults = copy.deepcopy(self.defaults)
        _deep_update(defaults, self.config)
        self.config = defaults

        # These backends are no longer configurable alternatives. Preserve user
        # thresholds and UI preferences, but keep runtime algorithms canonical.
        self.config.setdefault("app", {})["version"] = get_version()
        self.config.setdefault("ui", {})["type"] = "modern"
        self.config.setdefault("face_detection", {})["detection_method"] = "yunet"
        self.config.setdefault("face_recognition", {})["method"] = "sface"
        self.config.setdefault("liveness", {})["enabled"] = True

    def load(self) -> bool:
        try:
            if self.config_file.is_file():
                payload = json.loads(self.config_file.read_text(encoding="utf-8"))
                self.config = payload if isinstance(payload, dict) else {}
            else:
                self.config = self._seed_config()
            self._normalize()
            return self.save()
        except (OSError, json.JSONDecodeError) as exc:
            logger.error("Could not load config %s: %s", self.config_file, exc)
            self.config = copy.deepcopy(self.defaults)
            return False

    def save(self) -> bool:
        temporary = self.config_file.with_suffix(self.config_file.suffix + ".tmp")
        try:
            self._normalize()
            temporary.write_text(json.dumps(self.config, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            temporary.replace(self.config_file)
            return True
        except OSError as exc:
            temporary.unlink(missing_ok=True)
            logger.error("Could not save config %s: %s", self.config_file, exc)
            return False

    def get(self, key: str | None = None, default: Any = None) -> Any:
        if key is None:
            return copy.deepcopy(self.config)
        value: Any = self.config
        try:
            for part in key.split("."):
                value = value[part]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key: str, value: Any) -> bool:
        if not key:
            return False
        parts = key.split(".")
        target = self.config
        for part in parts[:-1]:
            child = target.get(part)
            if not isinstance(child, dict):
                child = {}
                target[part] = child
            target = child
        target[parts[-1]] = value
        return self.save()

    def update_config(self, new_config: dict[str, Any]) -> bool:
        _deep_update(self.config, new_config)
        return self.save()

    def reset(self, key: str | None = None) -> bool:
        if key is None:
            self.config = copy.deepcopy(self.defaults)
            return self.save()
        parts = key.split(".")
        default_value: Any = self.defaults
        try:
            for part in parts:
                default_value = default_value[part]
        except (KeyError, TypeError):
            return False
        return self.set(key, copy.deepcopy(default_value))

    def restore_defaults(self) -> bool:
        return self.reset()

    def export(self, export_path: str | Path | None = None) -> str | None:
        if export_path is None:
            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            export_path = EXPORTS_DIR / "config" / f"config_export_{timestamp}.json"
        path = Path(export_path).expanduser().resolve()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(self.config, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            return str(path)
        except OSError as exc:
            logger.error("Could not export config: %s", exc)
            return None

    def import_config(self, import_path: str | Path) -> bool:
        path = Path(import_path).expanduser().resolve()
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.error("Could not import config %s: %s", path, exc)
            return False
        if not isinstance(payload, dict):
            return False
        self.config = payload
        self._normalize()
        return self.save()

    def get_config(self) -> dict[str, Any]:
        return copy.deepcopy(self.config)


__all__ = ["ConfigManager"]
