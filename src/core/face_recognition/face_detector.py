"""Compatibility import for the canonical YuNet + SFace engine."""
from __future__ import annotations

from typing import Any

from src.core.face_engine import DEFAULT_GALLERY_PATH, FaceEngine


class FaceDetector(FaceEngine):
    """Historical detector name that loads the canonical gallery when available."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if DEFAULT_GALLERY_PATH.is_file():
            self.load_model(DEFAULT_GALLERY_PATH)


__all__ = ["FaceEngine", "FaceDetector"]
