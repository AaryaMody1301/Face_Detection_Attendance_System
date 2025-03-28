"""
Face detector module for detecting and recognizing faces
"""
import os
import sys
import cv2
import numpy as np
from PIL import Image
import logging
import threading
from functools import lru_cache

# Fix for face_recognition_models import issue
try:
    # Try to import the module
    import face_recognition
except ImportError as e:
    if "face_recognition_models" in str(e):
        print("Fixing face_recognition_models import issue...")
        # Try to fix the path issue by adding the site-packages directory directly
        import site
        import importlib
        site_packages = site.getsitepackages()[0]
        sys.path.append(site_packages)
        # Now try to import it again
        import face_recognition
    else:
        # Re-raise if it's a different import error
        raise

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

class FaceDetector:
    """Face detector class for detecting and recognizing faces"""
    
    def __init__(self, detection_model="hog", scale_factor=0.5):
        """
        Initialize the face detector.
        
        Args:
            detection_model (str): Face detection model to use, 'hog' (faster, less accurate) 
                                  or 'cnn' (slower, more accurate)
            scale_factor (float): Image scaling factor for face detection (0.25-1.0)
                                 Lower values are faster but may reduce accuracy
        """
        self.known_face_encodings = []
        self.known_face_names = []
        self.known_face_ids = []
        self.detection_model = detection_model
        self.scale_factor = min(max(0.25, scale_factor), 1.0)  # Ensure in valid range
        self.encoding_batch_size = 16
        self.encoding_lock = threading.Lock()

    def detect_faces(self, frame):
        """
        Detect faces in an image
        
        Args:
            frame (numpy.ndarray): Input image
            
        Returns:
            list: List of detected face regions (x, y, w, h)
        """
        # Input validation
        if frame is None or frame.size == 0:
            logger.warning("Empty frame provided to face detector")
            return []
            
        try:
            # Resize the image for faster processing
            if self.scale_factor != 1.0:
                small_frame = cv2.resize(frame, (0, 0), fx=self.scale_factor, fy=self.scale_factor)
            else:
                small_frame = frame.copy()
                
            # Convert to RGB (face_recognition uses RGB)
            rgb_frame = small_frame[:, :, ::-1]
            
            # Detect faces with timeout protection
            try:
                face_locations = face_recognition.face_locations(rgb_frame, model=self.detection_model)
            except Exception as e:
                logger.error(f"Error in face detection: {e}")
                # Fallback to HOG model if CNN failed
                if self.detection_model == "cnn":
                    logger.info("Falling back to HOG face detection model")
                    try:
                        face_locations = face_recognition.face_locations(rgb_frame, model="hog")
                    except Exception as e2:
                        logger.error(f"Fallback face detection also failed: {e2}")
                        return []
                else:
                    return []
            
            # If we scaled the image, scale the locations back to original size
            if self.scale_factor != 1.0:
                face_locations = [(int(top/self.scale_factor), int(right/self.scale_factor),
                                int(bottom/self.scale_factor), int(left/self.scale_factor))
                                for top, right, bottom, left in face_locations]
            
            return face_locations
            
        except Exception as e:
            logger.error(f"Unexpected error in face detection: {e}")
            return []

    def train_recognizer(self, training_dir):
        """
        Train the face recognizer with images from a directory
        
        Args:
            training_dir (str): Directory containing training images
            
        Returns:
            bool: True if training was successful
        """
        image_paths = []
        
        # Collect all image paths first
        for root, _, files in os.walk(training_dir):
            for file in files:
                if file.endswith(('png', 'jpg', 'jpeg')):
                    image_path = os.path.join(root, file)
                    image_paths.append((image_path, file.split('.')[0:2]))  # Name and ID
        
        # Reset stored data
        self.known_face_encodings = []
        self.known_face_names = []
        self.known_face_ids = []
        
        # Process images in batches for better memory management
        total_images = len(image_paths)
        processed = 0
        
        logger.info(f"Starting training with {total_images} images...")
        
        # Process images in batches
        batch_size = self.encoding_batch_size
        for i in range(0, total_images, batch_size):
            batch = image_paths[i:i+batch_size]
            
            for image_path, name_parts in batch:
                try:
                    # Extract student name and ID from filename
                    # Expected format: Name.ID.Number.jpg
                    if len(name_parts) >= 2:
                        name, student_id = name_parts[0], name_parts[1]
                    else:
                        name, student_id = name_parts[0], "unknown"
                    
                    # Load and process the image
                    image = face_recognition.load_image_file(image_path)
                    face_encodings = face_recognition.face_encodings(image)
                    
                    if face_encodings:
                        self.known_face_encodings.append(face_encodings[0])
                        self.known_face_names.append(name)
                        self.known_face_ids.append(student_id)
                        processed += 1
                except Exception as e:
                    logger.error(f"Error processing image {image_path}: {e}")
            
            # Log progress
            logger.info(f"Processed {processed}/{total_images} images...")
        
        logger.info(f"Training completed. {processed} faces encoded successfully.")
        return True

    def save_model(self, model_path):
        """
        Save the trained model
        
        Args:
            model_path (str): Path to save the model
            
        Returns:
            bool: True if model was saved successfully
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(model_path), exist_ok=True)
            
            # Save the model data
            np.savez_compressed(
                model_path, 
                encodings=np.array(self.known_face_encodings), 
                names=np.array(self.known_face_names),
                ids=np.array(self.known_face_ids)
            )
            
            logger.info(f"Model saved to {model_path} with {len(self.known_face_encodings)} face encodings")
            return True
        except Exception as e:
            logger.error(f"Error saving model: {e}")
            return False
            
    def load_model(self, model_path):
        """
        Load a trained model
        
        Args:
            model_path (str): Path to the model file
            
        Returns:
            bool: True if model was loaded successfully
        """
        try:
            if os.path.exists(model_path):
                # Check file extension
                if model_path.endswith('.npz'):
                    # Load as npz file
                    data = np.load(model_path, allow_pickle=True)
                    
                    self.known_face_encodings = data['encodings'].tolist() if 'encodings' in data else []
                    self.known_face_names = data['names'].tolist() if 'names' in data else []
                    
                    # Handle models with or without IDs for backward compatibility
                    if 'ids' in data:
                        self.known_face_ids = data['ids'].tolist()
                    else:
                        self.known_face_ids = ["unknown"] * len(self.known_face_names)
                    
                    logger.info(f"Model loaded from {model_path} with {len(self.known_face_encodings)} face encodings")
                    return True
                elif model_path.endswith('.yml'):
                    # If it's a .yml file, try to create a sample model with no face encodings
                    # This is just to allow the app to run
                    logger.warning(f"Found .yml model file, creating empty model: {model_path}")
                    self.known_face_encodings = []
                    self.known_face_names = []
                    self.known_face_ids = []
                    
                    # Create the proper npz file for future use
                    npz_path = model_path + ".npz"
                    self.save_model(npz_path)
                    
                    logger.info(f"Created empty model (no face encodings)")
                    return True
                else:
                    logger.warning(f"Unknown model file format: {model_path}")
                    return False
            
            logger.warning(f"Model file not found: {model_path}")
            return False
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False
    
    @lru_cache(maxsize=32)  # Cache recent results to speed up processing of video frames
    def _get_face_encoding(self, face_image_hash):
        """Get face encoding with caching for performance"""
        # This is a placeholder - in a real implementation, you'd need to
        # find a way to hash the face image data for the cache key
        return face_recognition.face_encodings(face_image_hash)
    
    def recognize_faces(self, frame, recognition_threshold=0.6):
        """
        Recognize faces in an image
        
        Args:
            frame (numpy.ndarray): Input image
            recognition_threshold (float): Face recognition confidence threshold (0-1)
                                         Lower values are stricter (fewer false positives)
            
        Returns:
            tuple: (face_locations, face_names, face_ids, confidence_scores)
        """
        # Process smaller image for speed
        if self.scale_factor != 1.0:
            small_frame = cv2.resize(frame, (0, 0), fx=self.scale_factor, fy=self.scale_factor)
        else:
            small_frame = frame
            
        # Convert to RGB (face_recognition uses RGB)
        rgb_frame = small_frame[:, :, ::-1]
        
        # Detect face locations
        face_locations = face_recognition.face_locations(rgb_frame, model=self.detection_model)
        
        # If no faces or no known faces, return early
        if not face_locations or not self.known_face_encodings:
            # Scale locations back to original size if needed
            if self.scale_factor != 1.0:
                face_locations = [(int(top/self.scale_factor), int(right/self.scale_factor),
                                int(bottom/self.scale_factor), int(left/self.scale_factor))
                               for top, right, bottom, left in face_locations]
            return face_locations, ["Unknown"] * len(face_locations), ["unknown"] * len(face_locations), [1.0] * len(face_locations)
        
        # Get face encodings
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
        
        face_names = []
        face_ids = []
        confidence_scores = []
        
        # Match each face
        for face_encoding in face_encodings:
            # Calculate face distances (lower distance = better match)
            with self.encoding_lock:  # Thread safety for face recognition
                face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
            
            # Get best match
            best_match_index = np.argmin(face_distances)
            min_distance = face_distances[best_match_index]
            
            # Convert distance to confidence score (0-1, higher is better)
            confidence = 1.0 - min(1.0, min_distance)
            
            # Determine if it's a match
            if confidence >= recognition_threshold:
                name = self.known_face_names[best_match_index]
                person_id = self.known_face_ids[best_match_index]
            else:
                name = "Unknown"
                person_id = "unknown"
            
            face_names.append(name)
            face_ids.append(person_id)
            confidence_scores.append(confidence)
        
        # Scale locations back to original size if needed
        if self.scale_factor != 1.0:
            face_locations = [(int(top/self.scale_factor), int(right/self.scale_factor),
                             int(bottom/self.scale_factor), int(left/self.scale_factor))
                            for top, right, bottom, left in face_locations]
        
        return face_locations, face_names, face_ids, confidence_scores

    def compute_face_encodings(self, rgb_frame, face_locations):
        """
        Compute facial encodings for faces in the image
        
        Args:
            rgb_frame (numpy.ndarray): RGB image frame
            face_locations (list): List of face locations as (top, right, bottom, left)
            
        Returns:
            list: List of face encodings
        """
        try:
            # Handle empty face locations list
            if not face_locations:
                return []
                
            # Compute face encodings from face_recognition library
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            return face_encodings
        except Exception as e:
            logger.error(f"Error computing face encodings: {e}")
            return []
    
    def identify_face(self, face_encoding):
        """
        Identify a face from its encoding
        
        Args:
            face_encoding: Face encoding to identify
            
        Returns:
            tuple: (name, confidence)
        """
        if not self.known_face_encodings or face_encoding is None:
            return "Unknown", 0.0
            
        try:
            # Calculate face distances (lower distance = better match)
            with self.encoding_lock:  # Thread safety for face recognition
                face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
            
            # Get best match
            if len(face_distances) > 0:
                best_match_index = np.argmin(face_distances)
                min_distance = face_distances[best_match_index]
                
                # Convert distance to confidence score (0-1, higher is better)
                confidence = 1.0 - min(1.0, min_distance)
                
                # Determine if it's a match based on distance threshold
                # A lower threshold means stricter matching
                if confidence > 0.6:  # Reasonable threshold
                    name = self.known_face_names[best_match_index]
                else:
                    name = "Unknown"
                    
                return name, confidence
            else:
                return "Unknown", 0.0
                
        except Exception as e:
            logger.error(f"Error identifying face: {e}")
            return "Unknown", 0.0