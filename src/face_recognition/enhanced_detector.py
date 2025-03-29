"""
Enhanced Face Detector with improved recognition algorithms
"""
import os
import sys
import cv2
import numpy as np
import time
import logging
import threading
from collections import deque
from functools import lru_cache
import pickle

# Improved face recognition with deep learning
try:
    import face_recognition
    import dlib
    HAVE_FACE_RECOGNITION = True
except ImportError:
    HAVE_FACE_RECOGNITION = False
    print("Warning: face_recognition module not found. Using OpenCV only.")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

class EnhancedFaceDetector:
    """Enhanced face detector class with multiple detection methods"""
    
    def __init__(self, 
                detection_method="auto", 
                recognition_method="hybrid", 
                scale_factor=0.5,
                min_face_size=30,
                confidence_threshold=0.6):
        """
        Initialize the enhanced face detector.
        
        Args:
            detection_method: Face detection method to use
                - "auto": Will use the best available method
                - "hog": HOG-based detector (faster but less accurate)
                - "cnn": CNN-based detector (more accurate but slower)
                - "haarcascade": Traditional OpenCV Haar Cascade detector
                - "dnn": OpenCV DNN-based detector
            recognition_method: Face recognition method
                - "hybrid": Uses multiple recognition methods for better accuracy
                - "lbph": Local Binary Pattern Histogram (OpenCV)
                - "embedding": Face embeddings from face_recognition library
            scale_factor: Image scaling factor for processing (0.25-1.0)
            min_face_size: Minimum face size in pixels
            confidence_threshold: Confidence threshold for recognition (0.0-1.0)
        """
        self.detection_method = detection_method
        self.recognition_method = recognition_method
        self.scale_factor = min(max(0.25, scale_factor), 1.0)  # Ensure valid range
        self.min_face_size = min_face_size
        self.confidence_threshold = confidence_threshold
        
        # Initialize face data storage
        self.known_face_encodings = []
        self.known_face_names = []
        self.known_face_ids = []
        
        # Face embedding model from face_recognition if available
        self._have_face_recognition = HAVE_FACE_RECOGNITION
        
        # Initialize face detection methods
        self._init_face_detectors()
        
        # Initialize recognition models
        self._init_recognition_models()
        
        # Threading safety
        self.encoding_lock = threading.Lock()
        
        # Performance monitoring
        self.detection_times = deque(maxlen=30)
        self.recognition_times = deque(maxlen=30)
    
    def _init_face_detectors(self):
        """Initialize multiple face detection methods"""
        self.detection_models = {}
        
        # Initialize Haar cascade detector
        try:
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            if not os.path.exists(cascade_path):
                cascade_path = 'haarcascade_frontalface_default.xml'
                
            self.detection_models['haarcascade'] = cv2.CascadeClassifier(cascade_path)
            
            if self.detection_models['haarcascade'].empty():
                logger.warning("Failed to load Haar cascade classifier")
                self.detection_models['haarcascade'] = None
            else:
                logger.info(f"Loaded Haar cascade classifier from {cascade_path}")
                
        except Exception as e:
            logger.error(f"Error initializing Haar cascade detector: {e}")
            self.detection_models['haarcascade'] = None
        
        # Initialize DNN detector if available
        try:
            prototxt_path = 'models/deploy.prototxt'
            model_path = 'models/res10_300x300_ssd_iter_140000.caffemodel'
            
            # Check if model files exist
            dnn_available = os.path.exists(prototxt_path) and os.path.exists(model_path)
            
            if dnn_available:
                self.detection_models['dnn'] = cv2.dnn.readNetFromCaffe(prototxt_path, model_path)
                logger.info("Loaded DNN face detector model")
            else:
                logger.warning("DNN face detector model files not found")
                self.detection_models['dnn'] = None
        except Exception as e:
            logger.error(f"Error initializing DNN detector: {e}")
            self.detection_models['dnn'] = None
        
        # Initialize face_recognition detectors if available
        if self._have_face_recognition:
            # HOG detector is part of face_recognition
            self.detection_models['hog'] = 'hog'
            logger.info("HOG face detector available")
            
            # CNN detector requires GPU for reasonable performance
            # Only initialize if GPU might be available
            try:
                # Check if GPU might be available for dlib
                if 'gpu' in dlib.cuda.get_num_devices() > 0:
                    self.detection_models['cnn'] = 'cnn'
                    logger.info("CNN face detector available with GPU")
                else:
                    logger.info("No GPU detected, CNN face detector might be slow")
                    # Still add it, but with a warning
                    self.detection_models['cnn'] = 'cnn'
            except:
                logger.warning("Could not initialize CNN detector, using HOG only")
        else:
            logger.warning("face_recognition library not available")
            
        # Determine the best available detector based on system capabilities
        if self.detection_method == "auto":
            # Choose best available method
            if self._have_face_recognition:
                try:
                    if dlib.cuda.get_num_devices() > 0:
                        self.detection_method = "cnn"  # Use CNN if GPU available
                    else:
                        self.detection_method = "hog"  # Use HOG as fallback
                except:
                    self.detection_method = "hog"  # Use HOG if can't check GPU
            elif self.detection_models['dnn'] is not None:
                self.detection_method = "dnn"  # Use DNN if available
            elif self.detection_models['haarcascade'] is not None:
                self.detection_method = "haarcascade"  # Use Haar as last resort
            else:
                raise RuntimeError("No face detection methods available")
                
        logger.info(f"Using {self.detection_method} as primary face detection method")
    
    def _init_recognition_models(self):
        """Initialize face recognition models"""
        self.recognition_models = {}
        
        # Initialize LBPH Recognizer
        try:
            self.recognition_models['lbph'] = cv2.face.LBPHFaceRecognizer_create()
            logger.info("Initialized LBPH face recognizer")
        except Exception as e:
            logger.error(f"Error initializing LBPH recognizer: {e}")
            self.recognition_models['lbph'] = None
        
        # Initialize face embeddings model if face_recognition is available
        if self._have_face_recognition:
            self.recognition_models['embedding'] = True
            logger.info("Face embedding recognition available")
        else:
            self.recognition_models['embedding'] = None
            
        # Set primary recognition method
        if self.recognition_method == "hybrid":
            # Will use both methods and combine results
            pass
        elif self.recognition_method == "lbph":
            # Just use LBPH
            if self.recognition_models['lbph'] is None:
                raise RuntimeError("LBPH recognition requested but not available")
        elif self.recognition_method == "embedding":
            # Just use embeddings
            if self.recognition_models['embedding'] is None:
                raise RuntimeError("Embedding recognition requested but not available")
        else:
            raise ValueError(f"Unknown recognition method: {self.recognition_method}")
    
    def detect_faces(self, frame):
        """
        Detect faces in an image using the selected detection method
        
        Args:
            frame: Input image frame (numpy array)
            
        Returns:
            list: Detected face regions as (x, y, w, h) tuples
        """
        if frame is None or frame.size == 0:
            return []
        
        start_time = time.time()
        face_locations = []
        
        try:
            # Scale down image for faster processing if needed
            if self.scale_factor != 1.0:
                small_frame = cv2.resize(
                    frame, (0, 0), 
                    fx=self.scale_factor, 
                    fy=self.scale_factor,
                    interpolation=cv2.INTER_AREA
                )
            else:
                small_frame = frame.copy()
            
            # Detect using the selected method
            if self.detection_method in ["hog", "cnn"] and self._have_face_recognition:
                # Use face_recognition library
                rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
                
                # Detect faces
                locations = face_recognition.face_locations(rgb_frame, model=self.detection_method)
                
                # Convert from (top, right, bottom, left) to (x, y, w, h)
                for (top, right, bottom, left) in locations:
                    x, y = left, top
                    w, h = right - left, bottom - top
                    face_locations.append((x, y, w, h))
                    
            elif self.detection_method == "dnn" and self.detection_models['dnn'] is not None:
                # Use OpenCV DNN detector
                detector = self.detection_models['dnn']
                h, w = small_frame.shape[:2]
                
                # Create blob and set input
                blob = cv2.dnn.blobFromImage(
                    small_frame, 1.0, (300, 300), 
                    [104, 117, 123], 
                    False, False
                )
                detector.setInput(blob)
                
                # Detect faces
                detections = detector.forward()
                
                # Process detections
                for i in range(detections.shape[2]):
                    confidence = detections[0, 0, i, 2]
                    
                    # Filter by confidence
                    if confidence > self.confidence_threshold:
                        # Get bounding box
                        box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                        x1, y1, x2, y2 = box.astype("int")
                        
                        # Calculate dimensions
                        x, y = max(0, x1), max(0, y1)
                        w, h = min(w - x, x2 - x1), min(h - y, y2 - y1)
                        
                        # Add face location if it meets minimum size
                        if w >= self.min_face_size and h >= self.min_face_size:
                            face_locations.append((x, y, w, h))
                
            elif self.detection_method == "haarcascade" and self.detection_models['haarcascade'] is not None:
                # Use OpenCV Haar Cascade detector
                detector = self.detection_models['haarcascade']
                
                # Convert to grayscale
                gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
                
                # Detect faces with progressively less strict parameters if needed
                for scale in [1.1, 1.2, 1.3]:
                    for min_neighbors in [5, 4, 3]:
                        # Skip if we already found faces
                        if face_locations:
                            break
                            
                        faces = detector.detectMultiScale(
                            gray,
                            scaleFactor=scale,
                            minNeighbors=min_neighbors,
                            minSize=(int(self.min_face_size * self.scale_factor), 
                                   int(self.min_face_size * self.scale_factor))
                        )
                        
                        if len(faces) > 0:
                            face_locations = list(faces)
                            break
            else:
                # Fallback to OpenCV Haar cascade if method not available
                logger.warning(f"Detection method {self.detection_method} not available, falling back to Haar cascade")
                
                if self.detection_models['haarcascade'] is not None:
                    gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
                    faces = self.detection_models['haarcascade'].detectMultiScale(
                        gray,
                        scaleFactor=1.2,
                        minNeighbors=4,
                        minSize=(int(self.min_face_size * self.scale_factor), 
                               int(self.min_face_size * self.scale_factor))
                    )
                    
                    if len(faces) > 0:
                        face_locations = list(faces)
            
            # Scale locations back to original size
            if self.scale_factor != 1.0 and face_locations:
                face_locations = [
                    (int(x / self.scale_factor), 
                     int(y / self.scale_factor),
                     int(w / self.scale_factor),
                     int(h / self.scale_factor)) 
                    for (x, y, w, h) in face_locations
                ]
        
        except Exception as e:
            logger.error(f"Error in face detection: {e}")
            face_locations = []
        
        # Update performance metrics
        detection_time = time.time() - start_time
        self.detection_times.append(detection_time)
        
        return face_locations
    
    def compute_face_embeddings(self, frame, face_locations):
        """
        Compute face embeddings for detected faces
        
        Args:
            frame: Input image frame
            face_locations: List of face locations (x, y, w, h)
            
        Returns:
            list: Face embeddings for each face
        """
        if not self._have_face_recognition or not face_locations:
            return []
        
        try:
            # Convert to RGB (face_recognition uses RGB)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Convert (x, y, w, h) to (top, right, bottom, left)
            face_locs = [(y, x+w, y+h, x) for (x, y, w, h) in face_locations]
            
            # Compute face encodings
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locs)
            return face_encodings
            
        except Exception as e:
            logger.error(f"Error computing face embeddings: {e}")
            return []
    
    def recognize_face(self, frame, face_location):
        """
        Recognize a face in an image
        
        Args:
            frame: Input image frame
            face_location: Face location as (x, y, w, h)
            
        Returns:
            dict: Recognition result with name, ID, confidence
        """
        start_time = time.time()
        result = {
            'success': False,
            'name': "Unknown",
            'student_id': "unknown",
            'confidence': 0.0,
        }
        
        try:
            x, y, w, h = face_location
            
            # Extract face region
            face_img = frame[y:y+h, x:x+w].copy()
            
            # Use hybrid approach if configured
            if self.recognition_method == "hybrid" and self._have_face_recognition:
                # First try embedding-based recognition
                rgb_face = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
                top, right, bottom, left = 0, w, h, 0  # Full face region
                
                # Get embeddings
                face_encodings = face_recognition.face_encodings(rgb_face, [(top, right, bottom, left)])
                
                if face_encodings:
                    embedding_result = self._recognize_with_embeddings(face_encodings[0])
                    
                    if embedding_result['confidence'] >= self.confidence_threshold:
                        # Good match with embeddings
                        result = embedding_result
                    else:
                        # Try LBPH as backup if available
                        if self.recognition_models['lbph'] is not None:
                            lbph_result = self._recognize_with_lbph(face_img)
                            
                            # If LBPH is more confident, use that
                            if lbph_result['confidence'] > embedding_result['confidence']:
                                result = lbph_result
                            else:
                                result = embedding_result
            elif self.recognition_method == "embedding" and self._have_face_recognition:
                # Only use embedding-based recognition
                rgb_face = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
                top, right, bottom, left = 0, w, h, 0  # Full face region
                
                # Get embeddings
                face_encodings = face_recognition.face_encodings(rgb_face, [(top, right, bottom, left)])
                
                if face_encodings:
                    result = self._recognize_with_embeddings(face_encodings[0])
            elif self.recognition_method == "lbph" and self.recognition_models['lbph'] is not None:
                # Only use LBPH recognition
                result = self._recognize_with_lbph(face_img)
        
        except Exception as e:
            logger.error(f"Error in face recognition: {e}")
        
        # Update performance metrics
        recognition_time = time.time() - start_time
        self.recognition_times.append(recognition_time)
        
        return result
    
    def _recognize_with_embeddings(self, face_encoding):
        """
        Recognize a face using face embeddings
        
        Args:
            face_encoding: Face encoding to identify
            
        Returns:
            dict: Recognition result
        """
        result = {
            'success': False,
            'name': "Unknown",
            'student_id': "unknown",
            'confidence': 0.0,
        }
        
        # Need known face data to compare against
        if not self.known_face_encodings:
            return result
        
        with self.encoding_lock:  # Thread safety
            # Calculate face distances (lower = better match)
            face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
            
            if len(face_distances) > 0:
                # Find best match
                best_match_index = np.argmin(face_distances)
                min_distance = face_distances[best_match_index]
                
                # Convert distance to confidence (0-1, higher is better)
                confidence = 1.0 - min(1.0, min_distance)
                
                # If confidence is good enough
                if confidence >= self.confidence_threshold:
                    result['success'] = True
                    result['name'] = self.known_face_names[best_match_index]
                    result['student_id'] = self.known_face_ids[best_match_index]
                    result['confidence'] = confidence
        
        return result
    
    def _recognize_with_lbph(self, face_img):
        """
        Recognize a face using LBPH
        
        Args:
            face_img: Face image to identify
            
        Returns:
            dict: Recognition result
        """
        result = {
            'success': False,
            'name': "Unknown",
            'student_id': "unknown",
            'confidence': 0.0,
        }
        
        # Check if LBPH model is available and has been trained
        if (self.recognition_models['lbph'] is None or 
            not hasattr(self.recognition_models['lbph'], 'predict')):
            return result
        
        try:
            # Convert to grayscale if needed
            if len(face_img.shape) > 2:
                gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
            else:
                gray = face_img
            
            # Resize to a standard size for recognition
            gray = cv2.resize(gray, (100, 100))
            
            # Predict with LBPH
            label, confidence = self.recognition_models['lbph'].predict(gray)
            
            # LBPH confidence is lower = better, convert to 0-1 scale
            normalized_confidence = max(0, min(100, 100 - confidence)) / 100.0
            
            if normalized_confidence >= self.confidence_threshold and label >= 0:
                # Convert label to name and ID
                if 0 <= label < len(self.known_face_ids):
                    result['success'] = True
                    result['name'] = self.known_face_names[label]
                    result['student_id'] = self.known_face_ids[label]
                    result['confidence'] = normalized_confidence
        
        except Exception as e:
            logger.error(f"Error in LBPH recognition: {e}")
        
        return result
    
    def train_recognizer(self, training_dir):
        """
        Train the face recognizer with images from a directory
        
        Args:
            training_dir: Path to directory containing training images
            
        Returns:
            bool: True if training was successful
        """
        if not os.path.exists(training_dir):
            logger.error(f"Training directory {training_dir} does not exist")
            return False
        
        start_time = time.time()
        
        # Reset face data
        self.known_face_encodings = []
        self.known_face_names = []
        self.known_face_ids = []
        
        # Track IDs for LBPH training
        id_map = {}
        next_id = 0
        
        # LBPH training data
        lbph_faces = []
        lbph_labels = []
        
        # Find all image files
        image_files = []
        for root, _, files in os.walk(training_dir):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                    file_path = os.path.join(root, file)
                    
                    # Extract name and ID from filename (Format: Name.ID.Number.jpg)
                    name_parts = file.split('.')[0:2]
                    
                    if len(name_parts) >= 2:
                        name, student_id = name_parts[0], name_parts[1]
                    else:
                        name, student_id = name_parts[0], "unknown"
                        
                    image_files.append((file_path, name, student_id))
        
        if not image_files:
            logger.error(f"No images found in {training_dir}")
            return False
        
        logger.info(f"Training recognizer with {len(image_files)} images...")
        
        processed = 0
        skipped = 0
        
        # Process each image
        for file_path, name, student_id in image_files:
            try:
                # Load image
                image = cv2.imread(file_path)
                
                if image is None:
                    logger.warning(f"Could not load image: {file_path}")
                    skipped += 1
                    continue
                
                # Detect face in the image
                face_locations = self.detect_faces(image)
                
                if not face_locations or len(face_locations) == 0:
                    logger.warning(f"No face found in {file_path}")
                    skipped += 1
                    continue
                
                # Get the largest face if multiple
                if len(face_locations) > 1:
                    face_locations.sort(key=lambda f: f[2] * f[3], reverse=True)
                
                # Extract face region
                x, y, w, h = face_locations[0]
                face_img = image[y:y+h, x:x+w]
                
                # Train embedding recognizer if available
                if self._have_face_recognition:
                    # Convert to RGB
                    rgb_face = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
                    
                    # Get face encoding
                    encodings = face_recognition.face_encodings(rgb_face)
                    
                    if encodings:
                        self.known_face_encodings.append(encodings[0])
                        self.known_face_names.append(name)
                        self.known_face_ids.append(student_id)
                
                # Train LBPH recognizer
                if self.recognition_models['lbph'] is not None:
                    # Convert to grayscale
                    gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
                    
                    # Resize to standard size
                    gray = cv2.resize(gray, (100, 100))
                    
                    # Get numeric ID for student
                    key = f"{name}_{student_id}"
                    if key not in id_map:
                        id_map[key] = next_id
                        next_id += 1
                    
                    numeric_id = id_map[key]
                    
                    # Add to LBPH training data
                    lbph_faces.append(gray)
                    lbph_labels.append(numeric_id)
                
                processed += 1
                
                # Log progress periodically
                if processed % 20 == 0:
                    logger.info(f"Processed {processed} images...")
            
            except Exception as e:
                logger.error(f"Error processing image {file_path}: {e}")
                skipped += 1
        
        # Train LBPH model if we have data
        if self.recognition_models['lbph'] is not None and lbph_faces:
            try:
                logger.info("Training LBPH recognizer...")
                self.recognition_models['lbph'].train(
                    lbph_faces, 
                    np.array(lbph_labels)
                )
                logger.info("LBPH training complete")
            except Exception as e:
                logger.error(f"Error training LBPH recognizer: {e}")
        
        # Finalize training
        training_time = time.time() - start_time
        logger.info(f"Training completed in {training_time:.2f} seconds.")
        logger.info(f"Processed {processed} images, skipped {skipped} images.")
        
        return processed > 0
    
    def save_model(self, model_path):
        """
        Save the trained model to a file
        
        Args:
            model_path: Path to save the model
            
        Returns:
            bool: True if the model was saved successfully
        """
        # Make sure directory exists
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        
        try:
            # Save model data
            model_data = {
                'known_face_names': self.known_face_names,
                'known_face_ids': self.known_face_ids,
                'have_face_recognition': self._have_face_recognition,
                'recognition_method': self.recognition_method,
            }
            
            # Add face encodings if available
            if self._have_face_recognition and self.known_face_encodings:
                model_data['known_face_encodings'] = np.array(self.known_face_encodings)
            
            # Save to .npz file for efficiency and compatibility
            np_path = f"{model_path}.npz"
            np.savez_compressed(np_path, **model_data)
            
            # Save LBPH model if available
            if self.recognition_models['lbph'] is not None:
                self.recognition_models['lbph'].save(model_path)
            
            logger.info(f"Model saved to {model_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving model: {e}")
            return False
    
    def load_model(self, model_path):
        """
        Load a trained model from a file
        
        Args:
            model_path: Path to the model file
            
        Returns:
            bool: True if the model was loaded successfully
        """
        try:
            # First check for NPZ file (our enhanced format)
            np_path = f"{model_path}.npz"
            
            if os.path.exists(np_path):
                # Load model data from NPZ
                data = np.load(np_path, allow_pickle=True)
                
                # Load face recognition data if available
                if 'known_face_names' in data:
                    self.known_face_names = data['known_face_names'].tolist()
                
                if 'known_face_ids' in data:
                    self.known_face_ids = data['known_face_ids'].tolist()
                
                # Load face encodings if available
                if 'known_face_encodings' in data and self._have_face_recognition:
                    self.known_face_encodings = data['known_face_encodings'].tolist()
            
            # Load LBPH model if available
            if self.recognition_models['lbph'] is not None:
                try:
                    self.recognition_models['lbph'].read(model_path)
                    logger.info(f"Loaded LBPH model from {model_path}")
                except Exception as lbph_error:
                    logger.warning(f"Could not load LBPH model: {lbph_error}")
            
            logger.info(f"Model loaded from {model_path} with {len(self.known_face_names)} faces")
            return len(self.known_face_names) > 0
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False
    
    def set_detection_method(self, method):
        """
        Set the face detection method
        
        Args:
            method: Face detection method
        """
        valid_methods = ["auto", "hog", "cnn", "haarcascade", "dnn"]
        
        if method not in valid_methods:
            logger.warning(f"Invalid detection method: {method}. Must be one of {valid_methods}")
            return False
        
        self.detection_method = method
        logger.info(f"Detection method set to {method}")
        
        # If auto, determine best method
        if method == "auto":
            self._init_face_detectors()
        
        return True
    
    def set_recognition_method(self, method):
        """
        Set the face recognition method
        
        Args:
            method: Face recognition method
        """
        valid_methods = ["hybrid", "lbph", "embedding"]
        
        if method not in valid_methods:
            logger.warning(f"Invalid recognition method: {method}. Must be one of {valid_methods}")
            return False
        
        self.recognition_method = method
        logger.info(f"Recognition method set to {method}")
        return True
    
    def set_confidence_threshold(self, threshold):
        """
        Set the confidence threshold for face recognition
        
        Args:
            threshold: Confidence threshold (0-100)
        """
        # Convert percentage to float 0-1
        threshold_float = float(threshold) / 100.0
        threshold_float = max(0.0, min(1.0, threshold_float))
        
        self.confidence_threshold = threshold_float
        logger.info(f"Confidence threshold set to {threshold_float:.2f} ({threshold}%)")
        return True
    
    def recognize_faces(self, frame):
        """
        Detect and recognize faces in an image
        
        Args:
            frame: Input image frame
            
        Returns:
            tuple: (face_locations, face_names, face_ids, confidences)
        """
        if frame is None or frame.size == 0:
            return [], [], [], []
        
        # Detect faces
        face_locations = self.detect_faces(frame)
        
        face_names = []
        face_ids = []
        confidences = []
        
        # Recognize each face
        for face_location in face_locations:
            result = self.recognize_face(frame, face_location)
            
            face_names.append(result['name'])
            face_ids.append(result['student_id'])
            confidences.append(result['confidence'])
        
        return face_locations, face_names, face_ids, confidences
    
    def get_performance_stats(self):
        """
        Get performance statistics
        
        Returns:
            dict: Performance statistics
        """
        stats = {
            'detection_time': 0,
            'recognition_time': 0,
            'total_time': 0,
            'fps': 0,
        }
        
        # Calculate average detection time
        if self.detection_times:
            stats['detection_time'] = sum(self.detection_times) / len(self.detection_times)
        
        # Calculate average recognition time
        if self.recognition_times:
            stats['recognition_time'] = sum(self.recognition_times) / len(self.recognition_times)
        
        # Calculate total processing time and FPS
        stats['total_time'] = stats['detection_time'] + stats['recognition_time']
        
        if stats['total_time'] > 0:
            stats['fps'] = 1.0 / stats['total_time']
        
        return stats