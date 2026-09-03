"""Deterministic tests for the legacy detector kept during Phase 1."""

import numpy as np

from src.face_recognition.detector import FaceDetector


def test_detector_initialization():
    detector = FaceDetector()
    assert detector.known_face_encodings == []
    assert detector.known_face_names == []
    assert detector.known_face_ids == []
    assert detector.detection_model == "hog"


def test_detect_faces_rejects_empty_frame():
    detector = FaceDetector()
    assert detector.detect_faces(np.array([], dtype=np.uint8)) == []
