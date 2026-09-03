"""Local passive liveness detection and temporal anti-spoofing gates."""
from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from src.core.face_models import (
    LIVENESS_MODEL_CACHE_DIR,
    MINIFAS_V1SE,
    MINIFAS_V2,
    ModelUnavailableError,
    resolve_model,
)

DEFAULT_LIVENESS_THRESHOLD = 0.50
DEFAULT_LIVENESS_WINDOW = 5
DEFAULT_REQUIRED_LIVE_FRAMES = 3


@dataclass(frozen=True)
class LivenessPrediction:
    """One-frame MiniFAS anti-spoofing prediction."""

    is_live: bool
    live_score: float
    label: str
    paper_score: float
    screen_score: float


@dataclass(frozen=True)
class LivenessDecision:
    """Temporal decision for one tracked face."""

    prediction: LivenessPrediction
    passed: bool
    track_id: int
    live_frames: int
    observed_frames: int


@dataclass
class _LivenessTrack:
    location: tuple[int, int, int, int]
    samples: deque[bool]
    last_frame: int
    matched_frame: int = -1


class TemporalLivenessGate:
    """Require repeated live predictions for the same spatial face track."""

    def __init__(
        self,
        *,
        window_size: int = DEFAULT_LIVENESS_WINDOW,
        required_live_frames: int = DEFAULT_REQUIRED_LIVE_FRAMES,
        min_live_ratio: float = 0.60,
        iou_threshold: float = 0.30,
        max_stale_frames: int = 8,
    ) -> None:
        self.window_size = max(1, int(window_size))
        self.required_live_frames = max(1, min(int(required_live_frames), self.window_size))
        self.min_live_ratio = min(1.0, max(0.0, float(min_live_ratio)))
        self.iou_threshold = min(1.0, max(0.0, float(iou_threshold)))
        self.max_stale_frames = max(1, int(max_stale_frames))
        self._frame_index = 0
        self._next_track_id = 1
        self._tracks: dict[int, _LivenessTrack] = {}

    @staticmethod
    def _iou(
        first: tuple[int, int, int, int],
        second: tuple[int, int, int, int],
    ) -> float:
        top_a, right_a, bottom_a, left_a = first
        top_b, right_b, bottom_b, left_b = second
        inter_left = max(left_a, left_b)
        inter_top = max(top_a, top_b)
        inter_right = min(right_a, right_b)
        inter_bottom = min(bottom_a, bottom_b)
        inter_w = max(0, inter_right - inter_left)
        inter_h = max(0, inter_bottom - inter_top)
        intersection = inter_w * inter_h
        if intersection <= 0:
            return 0.0
        area_a = max(0, right_a - left_a) * max(0, bottom_a - top_a)
        area_b = max(0, right_b - left_b) * max(0, bottom_b - top_b)
        union = area_a + area_b - intersection
        return float(intersection / union) if union > 0 else 0.0

    def begin_frame(self) -> None:
        """Advance temporal state before processing one camera frame."""
        self._frame_index += 1
        stale = [
            track_id
            for track_id, track in self._tracks.items()
            if self._frame_index - track.last_frame > self.max_stale_frames
        ]
        for track_id in stale:
            self._tracks.pop(track_id, None)

    def _match_track(self, location: tuple[int, int, int, int]) -> int | None:
        best_id = None
        best_iou = self.iou_threshold
        for track_id, track in self._tracks.items():
            if track.matched_frame == self._frame_index:
                continue
            overlap = self._iou(location, track.location)
            if overlap >= best_iou:
                best_iou = overlap
                best_id = track_id
        return best_id

    def update(
        self,
        location: tuple[int, int, int, int],
        prediction: LivenessPrediction,
    ) -> LivenessDecision:
        """Update the best spatial track and return its temporal live decision."""
        track_id = self._match_track(location)
        if track_id is None:
            track_id = self._next_track_id
            self._next_track_id += 1
            self._tracks[track_id] = _LivenessTrack(
                location=location,
                samples=deque(maxlen=self.window_size),
                last_frame=self._frame_index,
            )

        track = self._tracks[track_id]
        track.location = location
        track.last_frame = self._frame_index
        track.matched_frame = self._frame_index
        track.samples.append(bool(prediction.is_live))

        live_frames = sum(track.samples)
        observed = len(track.samples)
        live_ratio = live_frames / observed if observed else 0.0
        passed = (
            prediction.is_live
            and observed >= self.required_live_frames
            and live_frames >= self.required_live_frames
            and live_ratio >= self.min_live_ratio
        )
        return LivenessDecision(
            prediction=prediction,
            passed=passed,
            track_id=track_id,
            live_frames=live_frames,
            observed_frames=observed,
        )

    def reset(self) -> None:
        self._frame_index = 0
        self._next_track_id = 1
        self._tracks.clear()


@dataclass(frozen=True)
class GuardedFaceResult:
    """Recognition result paired with its liveness gate outcome."""

    location: tuple[int, int, int, int]
    name: str
    student_id: str
    recognition_score: float
    liveness: LivenessDecision


class MiniFASLiveness:
    """CPU-friendly MiniFASNet V2 + V1SE ensemble using OpenCV DNN."""

    _MODEL_CONFIG = (
        (MINIFAS_V2, 2.7),
        (MINIFAS_V1SE, 4.0),
    )

    def __init__(
        self,
        *,
        live_threshold: float = DEFAULT_LIVENESS_THRESHOLD,
        auto_download_models: bool = True,
        v2_model_path: str | Path | None = None,
        v1se_model_path: str | Path | None = None,
    ) -> None:
        self.live_threshold = min(1.0, max(0.0, float(live_threshold)))
        self.auto_download_models = bool(auto_download_models)
        self._explicit_paths = {
            MINIFAS_V2.name: Path(v2_model_path).expanduser() if v2_model_path else None,
            MINIFAS_V1SE.name: Path(v1se_model_path).expanduser() if v1se_model_path else None,
        }
        self._models: list[tuple[Any, float]] = []
        self._model_lock = threading.RLock()
        self.inference_times: deque[float] = deque(maxlen=30)

    def _resolve_path(self, spec) -> Path:
        explicit = self._explicit_paths.get(spec.name)
        if explicit is not None:
            path = explicit.resolve()
            if not path.is_file():
                raise ModelUnavailableError(f"Missing {spec.name} liveness model: {path}")
            return path
        return resolve_model(
            spec,
            cache_dir=LIVENESS_MODEL_CACHE_DIR,
            allow_download=self.auto_download_models,
        )

    def ensure_models(self) -> None:
        """Load both pinned MiniFAS models, downloading verified copies if needed."""
        if self._models:
            return
        with self._model_lock:
            if self._models:
                return
            loaded = []
            for spec, scale in self._MODEL_CONFIG:
                model_path = self._resolve_path(spec)
                try:
                    loaded.append((cv2.dnn.readNetFromONNX(str(model_path)), scale))
                except cv2.error as exc:
                    raise ModelUnavailableError(
                        f"OpenCV could not load the pinned {spec.name} model: {model_path}"
                    ) from exc
            self._models = loaded

    @staticmethod
    def _scaled_crop(
        frame: np.ndarray,
        location: tuple[int, int, int, int],
        scale: float,
    ) -> np.ndarray:
        top, right, bottom, left = location
        box_w = max(1, right - left)
        box_h = max(1, bottom - top)
        src_h, src_w = frame.shape[:2]

        bounded_scale = min(
            (src_h - 1) / box_h,
            (src_w - 1) / box_w,
            float(scale),
        )
        new_w = box_w * bounded_scale
        new_h = box_h * bounded_scale
        center_x = left + box_w / 2
        center_y = top + box_h / 2

        x1 = center_x - new_w / 2
        y1 = center_y - new_h / 2
        x2 = center_x + new_w / 2
        y2 = center_y + new_h / 2

        if x1 < 0:
            x2 -= x1
            x1 = 0
        if y1 < 0:
            y2 -= y1
            y1 = 0
        if x2 > src_w - 1:
            x1 -= x2 - src_w + 1
            x2 = src_w - 1
        if y2 > src_h - 1:
            y1 -= y2 - src_h + 1
            y2 = src_h - 1

        ix1 = max(0, int(x1))
        iy1 = max(0, int(y1))
        ix2 = min(src_w - 1, int(x2))
        iy2 = min(src_h - 1, int(y2))
        crop = frame[iy1 : iy2 + 1, ix1 : ix2 + 1]
        if crop.size == 0:
            raise ValueError("Face crop is empty")
        return cv2.resize(crop, (80, 80))

    @staticmethod
    def _softmax(logits: np.ndarray) -> np.ndarray:
        values = np.asarray(logits, dtype=np.float32).reshape(1, -1)
        values = values - np.max(values, axis=1, keepdims=True)
        exp_values = np.exp(values)
        return exp_values / np.sum(exp_values, axis=1, keepdims=True)

    def predict(
        self,
        frame: np.ndarray,
        location: tuple[int, int, int, int],
    ) -> LivenessPrediction:
        """Classify one YuNet face box as live, paper spoof, or screen spoof."""
        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
            raise ValueError("Liveness requires a non-empty BGR frame")
        self.ensure_models()

        start = time.perf_counter()
        probabilities = np.zeros(3, dtype=np.float32)
        with self._model_lock:
            for net, scale in self._models:
                crop = self._scaled_crop(frame, location, scale)
                tensor = np.transpose(crop.astype(np.float32), (2, 0, 1))[None, ...]
                net.setInput(tensor)
                probabilities += self._softmax(net.forward()).reshape(-1)[:3]
        probabilities /= max(1, len(self._models))
        self.inference_times.append(time.perf_counter() - start)

        label_index = int(np.argmax(probabilities))
        live_score = float(probabilities[1])
        label = ("paper", "live", "screen")[label_index]
        return LivenessPrediction(
            is_live=label_index == 1 and live_score >= self.live_threshold,
            live_score=live_score,
            label=label,
            paper_score=float(probabilities[0]),
            screen_score=float(probabilities[2]),
        )

    def get_performance_stats(self) -> dict[str, float | int]:
        average = sum(self.inference_times) / max(1, len(self.inference_times))
        return {
            "avg_liveness_time": average,
            "samples": len(self.inference_times),
        }

    def cleanup(self) -> None:
        self.inference_times.clear()
        with self._model_lock:
            self._models = []
