"""Deterministic compatibility tests for the canonical face engine."""

import numpy as np

from src.face_recognition.detector import FaceDetector


def test_detector_initialization_is_lazy_and_maps_legacy_hog_to_yunet():
    detector = FaceDetector(auto_download_models=False)
    assert detector.known_face_encodings == []
    assert detector.known_face_names == []
    assert detector.known_face_ids == []
    assert detector.detection_model == "yunet"
    assert detector.recognition_method == "sface"
    assert detector.model_ready is False


def test_detect_faces_rejects_empty_frame_without_loading_models():
    detector = FaceDetector(auto_download_models=False)
    assert detector.detect_faces(np.array([], dtype=np.uint8)) == []
    assert detector.model_ready is False
