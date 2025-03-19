"""
Tests for the face detector module.
"""
import os
import pytest
import cv2
import numpy as np
from src.face_recognition.detector import FaceDetector


def test_detector_initialization():
    """Test that the detector can be initialized."""
    detector = FaceDetector()
    assert detector is not None
    assert detector.detector is not None
    assert detector.recognizer is not None


def test_detect_faces():
    """Test face detection with a sample image."""
    # Skip if not running on a system with test data
    if not os.path.exists("tests/data"):
        pytest.skip("Test data not available")
    
    # Load a test image
    image_path = os.path.join("tests/data", "test_face.jpg")
    if not os.path.exists(image_path):
        pytest.skip(f"Test image not found: {image_path}")
    
    image = cv2.imread(image_path)
    
    detector = FaceDetector()
    faces = detector.detect_faces(image)
    
    # Check that faces were detected
    assert len(faces) > 0, "No faces detected in test image"


def test_train_recognizer_no_data():
    """Test training with no data."""
    detector = FaceDetector()
    empty_dir = "tests/data/empty"
    os.makedirs(empty_dir, exist_ok=True)
    
    # Training with no data should return False
    success = detector.train_recognizer(empty_dir)
    assert not success, "Training should fail with no data" 