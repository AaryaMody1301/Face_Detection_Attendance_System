"""Compatibility bridge for the original classic UI camera loop."""
from __future__ import annotations

from typing import Any

from src.core.face_recognition.face_detector import FaceDetector


class ClassicFaceDetector(FaceDetector):
    """Expose the two-list result shape expected only by ``src.ui.app``."""

    def recognize_faces(
        self,
        frame: Any,
        confidence_threshold: float | None = None,
    ) -> tuple[list[Any], list[str]]:
        results = super().recognize_faces(frame, confidence_threshold=confidence_threshold)
        return (
            [result[0] for result in results],
            [result[1] for result in results],
        )


__all__ = ["ClassicFaceDetector"]
