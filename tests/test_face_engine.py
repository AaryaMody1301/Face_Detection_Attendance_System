"""Phase 3 regression tests for YuNet, SFace, and verified model resolution."""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pytest

from src.core.face_engine import FaceEngine
from src.core.face_models import (
    SFACE,
    YUNET,
    ModelSpec,
    ModelUnavailableError,
    resolve_model,
)


class FakeDetector:
    def __init__(self) -> None:
        self.input_size = None

    def setInputSize(self, size) -> None:
        self.input_size = size

    def detect(self, _frame):
        face = np.asarray(
            [
                10,
                20,
                50,
                60,
                20,
                35,
                45,
                35,
                32,
                50,
                23,
                65,
                42,
                65,
                0.98,
            ],
            dtype=np.float32,
        )
        return 1, np.asarray([face], dtype=np.float32)


class FakeRecognizer:
    def __init__(self, feature=(1.0, 0.0)) -> None:
        self.feature_vector = np.asarray([feature], dtype=np.float32)

    def alignCrop(self, image, _face):
        return image

    def feature(self, _aligned):
        return self.feature_vector

    def match(self, query, candidate, _distance_type):
        return float(np.dot(query.reshape(-1), candidate.reshape(-1)))


def test_yunet_detection_preserves_legacy_box_shape_without_model_download():
    engine = FaceEngine(auto_download_models=False)
    engine._detector = FakeDetector()

    frame = np.zeros((100, 120, 3), dtype=np.uint8)
    assert engine.detect_faces(frame) == [(20, 60, 80, 10)]
    assert engine._detector.input_size == (120, 100)


def test_sface_recognition_returns_gallery_identity():
    engine = FaceEngine(auto_download_models=False)
    engine._detector = FakeDetector()
    engine._recognizer = FakeRecognizer()
    engine._set_gallery(np.asarray([[1.0, 0.0]], dtype=np.float32), ["Ada"], ["S001"])

    frame = np.zeros((100, 120, 3), dtype=np.uint8)
    result = engine.recognize_faces(frame)

    assert len(result) == 1
    location, name, student_id, confidence = result[0]
    assert location == (20, 60, 80, 10)
    assert name == "Ada"
    assert student_id == "S001"
    assert confidence == pytest.approx(1.0)


def test_gallery_round_trip_uses_npz_without_pickle(tmp_path: Path):
    path = tmp_path / "face_gallery.npz"
    engine = FaceEngine(auto_download_models=False)
    engine._set_gallery(
        np.asarray([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32),
        ["Ada", "Grace"],
        ["S001", "S002"],
    )
    assert engine.save_model(path)

    loaded = FaceEngine(auto_download_models=False)
    assert loaded.load_model(path)
    assert loaded.known_face_names == ["Ada", "Grace"]
    assert loaded.known_face_ids == ["S001", "S002"]
    assert np.allclose(loaded.known_face_encodings[0], [1.0, 0.0])


def test_cached_model_must_match_pinned_hash_and_size(tmp_path: Path, monkeypatch):
    payload = b"tiny-model"
    spec = ModelSpec(
        name="test-model",
        relative_path="models/test/model.onnx",
        sha256=hashlib.sha256(payload).hexdigest(),
        size=len(payload),
        env_var="TEST_FACE_MODEL",
    )
    monkeypatch.delenv(spec.env_var, raising=False)
    cached = tmp_path / spec.filename
    cached.write_bytes(payload)

    assert resolve_model(spec, cache_dir=tmp_path, allow_download=False) == cached.resolve()


def test_corrupt_cached_model_is_rejected_offline(tmp_path: Path, monkeypatch):
    payload = b"expected"
    spec = ModelSpec(
        name="test-model",
        relative_path="models/test/model.onnx",
        sha256=hashlib.sha256(payload).hexdigest(),
        size=len(payload),
        env_var="TEST_FACE_MODEL",
    )
    monkeypatch.delenv(spec.env_var, raising=False)
    cached = tmp_path / spec.filename
    cached.write_bytes(b"corrupt!")

    with pytest.raises(ModelUnavailableError):
        resolve_model(spec, cache_dir=tmp_path, allow_download=False)
    assert not cached.exists()


def test_official_model_metadata_is_pinned():
    assert YUNET.sha256 == "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"
    assert YUNET.size == 232589
    assert SFACE.sha256 == "0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79"
    assert SFACE.size == 38696353
