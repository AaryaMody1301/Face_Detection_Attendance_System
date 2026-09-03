"""Phase 4 regression tests for MiniFAS liveness and guarded recognition."""
from __future__ import annotations

import numpy as np
import pytest

from src.core.face_engine import FaceEngine
from src.core.face_models import MINIFAS_V1SE, MINIFAS_V2
from src.core.liveness import (
    LivenessPrediction,
    MiniFASLiveness,
    TemporalLivenessGate,
    recognize_faces_guarded,
)


class FakeNet:
    def __init__(self, logits: tuple[float, float, float]) -> None:
        self.logits = np.asarray([logits], dtype=np.float32)
        self.input_shape = None

    def setInput(self, tensor) -> None:
        self.input_shape = tuple(tensor.shape)

    def forward(self):
        return self.logits.copy()


class FakeDetector:
    def setInputSize(self, _size) -> None:
        return None

    def detect(self, _frame):
        face = np.asarray(
            [
                20,
                20,
                60,
                60,
                35,
                40,
                65,
                40,
                50,
                52,
                38,
                67,
                62,
                67,
                0.99,
            ],
            dtype=np.float32,
        )
        return 1, np.asarray([face], dtype=np.float32)


class FakeRecognizer:
    def alignCrop(self, image, _face):
        return image

    def feature(self, _aligned):
        return np.asarray([[1.0, 0.0]], dtype=np.float32)

    def match(self, query, candidate, _distance_type):
        return float(np.dot(query.reshape(-1), candidate.reshape(-1)))


class StubLiveness:
    def __init__(self, prediction: LivenessPrediction) -> None:
        self.prediction = prediction

    def predict(self, _frame, _location):
        return self.prediction


def _prediction(*, live: bool, score: float = 0.9) -> LivenessPrediction:
    return LivenessPrediction(
        is_live=live,
        live_score=score if live else 0.05,
        label="live" if live else "paper",
        paper_score=0.05 if live else 0.90,
        screen_score=0.05,
    )


def test_minifas_ensemble_uses_bgr_80px_inputs_and_real_class_one():
    v2 = FakeNet((0.0, 5.0, 0.0))
    v1se = FakeNet((0.0, 4.0, 0.0))
    engine = MiniFASLiveness(auto_download_models=False)
    engine._models = [(v2, 2.7), (v1se, 4.0)]

    frame = np.zeros((200, 200, 3), dtype=np.uint8)
    prediction = engine.predict(frame, (50, 150, 150, 50))

    assert prediction.is_live
    assert prediction.label == "live"
    assert prediction.live_score > 0.95
    assert v2.input_shape == (1, 3, 80, 80)
    assert v1se.input_shape == (1, 3, 80, 80)


def test_minifas_blocks_spoof_when_live_class_is_not_dominant():
    engine = MiniFASLiveness(auto_download_models=False)
    engine._models = [
        (FakeNet((5.0, 0.0, 0.0)), 2.7),
        (FakeNet((4.0, 0.0, 0.0)), 4.0),
    ]

    prediction = engine.predict(np.zeros((160, 160, 3), dtype=np.uint8), (40, 120, 120, 40))

    assert not prediction.is_live
    assert prediction.label == "paper"
    assert prediction.live_score < 0.05


def test_temporal_gate_requires_repeated_live_frames_and_current_live_frame():
    gate = TemporalLivenessGate(window_size=5, required_live_frames=3)
    location = (20, 80, 80, 20)

    decisions = []
    for _ in range(3):
        gate.begin_frame()
        decisions.append(gate.update(location, _prediction(live=True)))

    assert not decisions[0].passed
    assert not decisions[1].passed
    assert decisions[2].passed
    assert decisions[2].live_frames == 3

    gate.begin_frame()
    spoof = gate.update(location, _prediction(live=False))
    assert not spoof.passed
    assert spoof.prediction.label == "paper"


def test_guarded_recognition_skips_sface_until_liveness_passes():
    engine = FaceEngine(auto_download_models=False)
    engine._detector = FakeDetector()
    engine._recognizer = FakeRecognizer()
    engine._set_gallery(np.asarray([[1.0, 0.0]], dtype=np.float32), ["Ada"], ["S001"])
    frame = np.zeros((120, 120, 3), dtype=np.uint8)

    blocked = recognize_faces_guarded(
        engine,
        frame,
        StubLiveness(_prediction(live=False)),
        TemporalLivenessGate(window_size=1, required_live_frames=1),
    )
    assert blocked[0].name == "Unknown"
    assert not blocked[0].liveness.passed

    allowed = recognize_faces_guarded(
        engine,
        frame,
        StubLiveness(_prediction(live=True)),
        TemporalLivenessGate(window_size=1, required_live_frames=1),
    )
    assert allowed[0].liveness.passed
    assert allowed[0].name == "Ada"
    assert allowed[0].student_id == "S001"
    assert allowed[0].recognition_score == pytest.approx(1.0)


def test_minifas_model_metadata_is_pinned():
    assert MINIFAS_V2.sha256 == "b32929adc2d9c34b9486f8c4c7bc97c1b69bc0ea9befefc380e4faae4e463907"
    assert MINIFAS_V2.size == 1743581
    assert MINIFAS_V1SE.sha256 == "ebab7f90c7833fbccd46d3a555410e78d969db5438e169b6524be444862b3676"
    assert MINIFAS_V1SE.size == 1742335
    assert "yakhyo/face-anti-spoofing/releases/download/weights" in MINIFAS_V2.url
