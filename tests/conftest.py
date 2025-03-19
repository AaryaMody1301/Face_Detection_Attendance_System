"""
Shared test fixtures for the Face Detection Attendance System.
"""
import os
import pytest
import numpy as np
import cv2


@pytest.fixture(scope="session")
def test_data_dir():
    """Create and return the path to the test data directory."""
    data_dir = os.path.join("tests", "data")
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


@pytest.fixture(scope="session")
def empty_test_dir(test_data_dir):
    """Create and return the path to an empty test directory."""
    empty_dir = os.path.join(test_data_dir, "empty")
    os.makedirs(empty_dir, exist_ok=True)
    return empty_dir


@pytest.fixture(scope="session")
def test_face_image(test_data_dir):
    """
    Create a test face image if it doesn't exist.
    
    This creates a simple, synthetic face-like pattern for testing
    rather than using a real face image.
    """
    image_path = os.path.join(test_data_dir, "test_face.jpg")
    
    # Only create the image if it doesn't exist
    if not os.path.exists(image_path):
        # Create a simple face-like pattern
        image = np.zeros((300, 300, 3), dtype=np.uint8)
        
        # Draw a circle for the face
        cv2.circle(image, (150, 150), 100, (200, 200, 200), -1)
        
        # Draw eyes
        cv2.circle(image, (120, 120), 15, (0, 0, 0), -1)
        cv2.circle(image, (180, 120), 15, (0, 0, 0), -1)
        
        # Draw mouth
        cv2.ellipse(image, (150, 180), (40, 20), 0, 0, 180, (0, 0, 0), 2)
        
        # Save the image
        cv2.imwrite(image_path, image)
    
    return image_path 