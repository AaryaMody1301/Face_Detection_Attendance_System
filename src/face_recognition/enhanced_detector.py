"""Legacy enhanced detector routed through the canonical YuNet + SFace engine."""

from src.core.face_engine import FaceEngine


class EnhancedFaceDetector(FaceEngine):
    """Compatibility name for callers that requested the former enhanced detector."""


FaceDetector = EnhancedFaceDetector

__all__ = ["EnhancedFaceDetector", "FaceDetector", "FaceEngine"]
