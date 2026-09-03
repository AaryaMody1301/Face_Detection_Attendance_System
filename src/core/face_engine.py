"""Canonical face-engine facade.

Phase 2 consolidates every UI/controller on one API while intentionally keeping
the existing recognition algorithm underneath. The algorithm itself is replaced
in Phase 3, so this facade preserves legacy constructor/method signatures now.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import cv2

from src.core.face_recognition.face_detector import FaceDetector as _LegacyFaceDetector
from src.core.paths import TRAINING_MODELS_DIR, ensure_runtime_dirs

logger = logging.getLogger(__name__)


class FaceEngine:
    """Single face detection/recognition API used by the application."""

    def __init__(
        self,
        detection_method: str = "auto",
        recognition_method: str = "hybrid",
        scale_factor: float = 0.5,
        min_face_size: int = 30,
        confidence_threshold: float = 0.6,
        **legacy_options: Any,
    ) -> None:
        ensure_runtime_dirs()

        detection_method = legacy_options.pop("detection_model", detection_method)
        detection_method = legacy_options.pop("method", detection_method)
        confidence_threshold = legacy_options.pop("threshold", confidence_threshold)
        legacy_options.pop("students_csv_path", None)

        if detection_method == "haar":
            detection_method = "haarcascade"
        elif detection_method == "hybrid":
            detection_method = "auto"
            recognition_method = "hybrid"

        if legacy_options:
            logger.debug("Ignoring legacy FaceDetector options: %s", sorted(legacy_options))

        self._engine = _LegacyFaceDetector(
            detection_method=detection_method,
            recognition_method=recognition_method,
            scale_factor=scale_factor,
            min_face_size=min_face_size,
            confidence_threshold=confidence_threshold,
        )

    def __getattr__(self, name: str) -> Any:
        """Delegate compatible attributes to the retained Phase-1 implementation."""
        return getattr(self._engine, name)

    @property
    def detection_model(self) -> str:
        """Legacy name for the active detection method."""
        return self._engine.detection_method

    @staticmethod
    def _normalize_frame(frame: Any) -> Any:
        if frame is not None and getattr(frame, "ndim", 0) == 2:
            return cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        return frame

    def detect_faces(self, frame: Any) -> list[Any]:
        return self._engine.detect_faces(self._normalize_frame(frame))

    def detect_faces_only(self, frame: Any) -> list[Any]:
        """Compatibility alias used by an older migration guide/API."""
        return self.detect_faces(frame)

    def recognize_faces(self, frame: Any, confidence_threshold: float | None = None) -> list[Any]:
        return self._engine.recognize_faces(
            self._normalize_frame(frame),
            confidence_threshold=confidence_threshold,
        )

    def detect_and_recognize(self, frame: Any) -> list[Any]:
        """Compatibility alias for combined detection and recognition."""
        return self.recognize_faces(frame)

    def recognize_face(self, frame: Any) -> dict[str, Any] | None:
        """Return the best recognized face in the controller-friendly shape."""
        recognized = [
            result for result in self.recognize_faces(frame)
            if len(result) >= 4 and result[1] != "Unknown" and result[2]
        ]
        if not recognized:
            return None
        _, name, student_id, confidence = max(recognized, key=lambda item: item[3])
        return {
            "student_id": student_id,
            "name": name,
            "confidence": float(confidence),
        }

    def train_recognizer(self, training_dir: str | Path) -> bool:
        return self._engine.train_recognizer(str(training_dir))

    def train_model(
        self,
        training_images_path: str | Path,
        training_labels_path: str | Path | None = None,
    ) -> dict[str, Any]:
        """Train and persist through the canonical API used by controllers."""
        success = self.train_recognizer(training_images_path)
        if not success:
            return {"success": False, "message": "No usable training faces were found."}

        output_dir = Path(training_labels_path) if training_labels_path else TRAINING_MODELS_DIR
        output_dir.mkdir(parents=True, exist_ok=True)
        model_path = output_dir / "face_model.pkl"
        saved = self.save_model(model_path)
        return {
            "success": bool(saved),
            "data": {"model_path": str(model_path)},
            "message": "Model trained and saved." if saved else "Model trained but could not be saved.",
        }

    def save_model(self, model_path: str | Path) -> bool:
        return self._engine.save_model(str(model_path))

    def load_model(self, model_path: str | Path) -> bool:
        return self._engine.load_model(str(model_path))

    def cleanup(self) -> None:
        self._engine.cleanup()


# Temporary compatibility name. Legacy modules re-export this alias so there is
# still exactly one constructed engine path across UI/controller entry points.
FaceDetector = FaceEngine
