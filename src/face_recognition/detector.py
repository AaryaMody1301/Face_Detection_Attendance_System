"""Legacy detector module routed through the canonical FaceEngine."""

from typing import Any

from src.core.face_engine import FaceEngine


class FaceDetector(FaceEngine):
    """Compatibility adapter preserving the historical HOG default."""

    def __init__(
        self,
        detection_model: str = "hog",
        scale_factor: float = 0.5,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            detection_model=detection_model,
            scale_factor=scale_factor,
            **kwargs,
        )


__all__ = ["FaceEngine", "FaceDetector"]
