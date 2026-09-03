"""Resilient OpenCV camera capture with backend fallback and reconnect support."""
from __future__ import annotations

import logging
import platform
import time
from collections.abc import Callable, Iterable
from typing import Any

import cv2

logger = logging.getLogger(__name__)

CaptureFactory = Callable[..., Any]


class ResilientCamera:
    """Small ``cv2.VideoCapture`` compatible wrapper for live camera sources.

    The wrapper tries a platform-preferred backend first, falls back to OpenCV's
    default backend, and reconnects after repeated failed frame reads. It keeps
    the small method surface used by the existing UI code: ``isOpened``,
    ``read``, ``set``, ``get`` and ``release``.
    """

    def __init__(
        self,
        source: int | str = 0,
        *,
        backends: Iterable[int] | None = None,
        max_consecutive_failures: int = 3,
        reconnect_cooldown: float = 0.5,
        capture_factory: CaptureFactory = cv2.VideoCapture,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.source = source
        self.backends = tuple(backends or self._default_backends(source))
        self.max_consecutive_failures = max(1, int(max_consecutive_failures))
        self.reconnect_cooldown = max(0.0, float(reconnect_cooldown))
        self._capture_factory = capture_factory
        self._monotonic = monotonic
        self._capture: Any | None = None
        self._consecutive_failures = 0
        self._last_reconnect = float("-inf")
        self.open_attempts = 0
        self.reconnects = 0
        self.read_failures = 0

    @staticmethod
    def _default_backends(source: int | str) -> tuple[int, ...]:
        if not isinstance(source, int):
            return (cv2.CAP_ANY,)

        system = platform.system().lower()
        preferred = cv2.CAP_ANY
        if system == "windows" and hasattr(cv2, "CAP_DSHOW"):
            preferred = cv2.CAP_DSHOW
        elif system == "darwin" and hasattr(cv2, "CAP_AVFOUNDATION"):
            preferred = cv2.CAP_AVFOUNDATION
        elif system == "linux" and hasattr(cv2, "CAP_V4L2"):
            preferred = cv2.CAP_V4L2

        return (preferred, cv2.CAP_ANY) if preferred != cv2.CAP_ANY else (cv2.CAP_ANY,)

    def _new_capture(self, backend: int) -> Any:
        if backend == cv2.CAP_ANY:
            return self._capture_factory(self.source)
        return self._capture_factory(self.source, backend)

    def open(self) -> bool:
        """Open the source using preferred backends in order."""
        self.release()
        for backend in self.backends:
            self.open_attempts += 1
            try:
                capture = self._new_capture(backend)
            except (cv2.error, OSError, TypeError) as exc:
                logger.warning("Camera backend %s failed to initialize: %s", backend, exc)
                continue

            if capture is not None and capture.isOpened():
                self._capture = capture
                self._consecutive_failures = 0
                logger.info("Opened camera source %r with backend %s", self.source, backend)
                return True

            if capture is not None:
                capture.release()

        logger.error("Could not open camera source %r with any configured backend", self.source)
        return False

    def isOpened(self) -> bool:  # noqa: N802 - OpenCV compatibility surface
        return self._capture is not None and bool(self._capture.isOpened())

    def _reconnect(self) -> bool:
        now = self._monotonic()
        if now - self._last_reconnect < self.reconnect_cooldown:
            return False
        self._last_reconnect = now
        self.reconnects += 1
        logger.warning("Reconnecting camera source %r after frame-read failures", self.source)
        return self.open()

    def read(self):
        """Read one frame, reconnecting after repeated failures."""
        if not self.isOpened() and not self._reconnect():
            return False, None

        try:
            ok, frame = self._capture.read()
        except (cv2.error, OSError) as exc:
            logger.warning("Camera read raised an error: %s", exc)
            ok, frame = False, None

        if ok and frame is not None and getattr(frame, "size", 0) > 0:
            self._consecutive_failures = 0
            return True, frame

        self.read_failures += 1
        self._consecutive_failures += 1
        if self._consecutive_failures >= self.max_consecutive_failures:
            self._consecutive_failures = 0
            self._reconnect()
        return False, None

    def set(self, prop_id: int, value: float) -> bool:
        if not self.isOpened():
            return False
        try:
            return bool(self._capture.set(prop_id, value))
        except cv2.error:
            return False

    def get(self, prop_id: int) -> float:
        if not self.isOpened():
            return 0.0
        try:
            return float(self._capture.get(prop_id))
        except cv2.error:
            return 0.0

    def release(self) -> None:
        capture, self._capture = self._capture, None
        if capture is not None:
            try:
                capture.release()
            except (cv2.error, OSError):
                logger.debug("Camera release failed", exc_info=True)

    def __enter__(self) -> "ResilientCamera":
        if not self.open():
            raise RuntimeError(f"Could not open camera source {self.source!r}")
        return self

    def __exit__(self, _exc_type, _exc, _tb) -> None:
        self.release()


__all__ = ["ResilientCamera"]
