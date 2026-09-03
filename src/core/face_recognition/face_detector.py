"""Compatibility import for the canonical YuNet + SFace engine."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from src.core.face_engine import DEFAULT_GALLERY_PATH, FaceEngine


class FaceDetector(FaceEngine):
    """Historical detector name with canonical gallery compatibility."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if DEFAULT_GALLERY_PATH.is_file():
            super().load_model(DEFAULT_GALLERY_PATH)

    def save_model(self, model_path: str | Path) -> bool:
        """Save the requested compatibility file and refresh the canonical gallery."""
        requested = Path(model_path)
        saved = super().save_model(requested)
        if not saved:
            return False
        if requested.expanduser().resolve() != DEFAULT_GALLERY_PATH.expanduser().resolve():
            return super().save_model(DEFAULT_GALLERY_PATH)
        return True

    def load_model(self, model_path: str | Path) -> bool:
        """Load a requested SFace gallery, falling back to the canonical location."""
        if super().load_model(model_path):
            return True
        requested = Path(model_path).expanduser().resolve()
        canonical = DEFAULT_GALLERY_PATH.expanduser().resolve()
        if requested != canonical and DEFAULT_GALLERY_PATH.is_file():
            return super().load_model(DEFAULT_GALLERY_PATH)
        return False


__all__ = ["FaceEngine", "FaceDetector"]
