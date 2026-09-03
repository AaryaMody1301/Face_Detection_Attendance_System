"""Compatibility bridge for the original classic UI camera loop."""
from __future__ import annotations

from typing import Any

from src.core.face_recognition.face_detector import FaceDetector
from src.core.liveness import MiniFASLiveness, TemporalLivenessGate, recognize_faces_guarded


class ClassicFaceDetector(FaceDetector):
    """Keep the classic two-list API while requiring live faces before recognition."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._classic_liveness = MiniFASLiveness()
        self._classic_liveness_gate = TemporalLivenessGate()

    def recognize_faces(
        self,
        frame: Any,
        confidence_threshold: float | None = None,
    ) -> tuple[list[Any], list[str]]:
        results = recognize_faces_guarded(
            self,
            frame,
            self._classic_liveness,
            self._classic_liveness_gate,
            confidence_threshold=confidence_threshold,
        )
        return (
            [result.location for result in results],
            [result.name if result.liveness.passed else "Unknown" for result in results],
        )

    def cleanup(self) -> None:
        self._classic_liveness_gate.reset()
        self._classic_liveness.cleanup()
        super().cleanup()


__all__ = ["ClassicFaceDetector"]