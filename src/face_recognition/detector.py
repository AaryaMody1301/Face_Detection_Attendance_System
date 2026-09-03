"""Legacy detector module routed through the canonical YuNet + SFace engine."""

from src.core.face_engine import FaceEngine
from src.core.face_recognition.face_detector import FaceDetector

__all__ = ["FaceEngine", "FaceDetector"]
