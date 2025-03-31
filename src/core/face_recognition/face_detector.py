"""
Unified Face Detector

This module provides a face detection and recognition system that works with both UI variants.
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

# Try to import face_recognition
try:
    import face_recognition
    import dlib
    HAVE_FACE_RECOGNITION = True
except ImportError:
    HAVE_FACE_RECOGNITION = False
    print("Warning: face_recognition module not found. Using OpenCV only.")

# Configure logging
logger = logging.getLogger(__name__)

class FaceDetector:
    """Unified face detector class with multiple detection methods"""
    
    def __init__(self, 
                detection_method="auto", 
                recognition_method="hybrid", 
                scale_factor=0.5,
                min_face_size=30,
                confidence_threshold=0.6):
        """
        Initialize the face detector.
        
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
            try:
                # Check if GPU might be available for dlib
                if hasattr(dlib.cuda, 'get_num_devices') and dlib.cuda.get_num_devices() > 0:
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
                    if hasattr(dlib.cuda, 'get_num_devices') and dlib.cuda.get_num_devices() > 0:
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
        Detect faces in an image
        
        Args:
            frame (numpy.ndarray): Input image
            
        Returns:
            list: List of detected face locations
        """
        # Input validation
        if frame is None or frame.size == 0:
            logger.warning("Empty frame provided to face detector")
            return []
            
        try:
            # Start timing
            start_time = time.time()
            
            # Resize the image for faster processing
            if self.scale_factor != 1.0:
                small_frame = cv2.resize(frame, (0, 0), fx=self.scale_factor, fy=self.scale_factor)
            else:
                small_frame = frame.copy()
                
            face_locations = []
            
            # Use the appropriate detection method
            if self.detection_method in ['hog', 'cnn'] and self._have_face_recognition:
                # Convert to RGB for face_recognition library
                rgb_frame = small_frame[:, :, ::-1]
                
                # Use face_recognition library
                try:
                    face_locations = face_recognition.face_locations(rgb_frame, model=self.detection_method)
                except Exception as e:
                    logger.error(f"Error in face_recognition detection: {e}")
                    # Fall back to HOG if CNN failed
                    if self.detection_method == "cnn":
                        try:
                            face_locations = face_recognition.face_locations(rgb_frame, model="hog")
                        except Exception as e2:
                            logger.error(f"Fallback HOG detection also failed: {e2}")
                
            elif self.detection_method == "haarcascade" and self.detection_models['haarcascade'] is not None:
                # Convert to grayscale for Haar cascade
                gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
                
                # Detect faces using Haar cascade
                faces = self.detection_models['haarcascade'].detectMultiScale(
                    gray,
                    scaleFactor=1.1,
                    minNeighbors=5,
                    minSize=(int(self.min_face_size * self.scale_factor), int(self.min_face_size * self.scale_factor))
                )
                
                # Convert to face_recognition format (top, right, bottom, left)
                face_locations = [(y, x+w, y+h, x) for (x, y, w, h) in faces]
                
            elif self.detection_method == "dnn" and self.detection_models['dnn'] is not None:
                # Use DNN-based detector
                try:
                    height, width = small_frame.shape[:2]
                    blob = cv2.dnn.blobFromImage(small_frame, 1.0, (300, 300), (104.0, 177.0, 123.0))
                    
                    self.detection_models['dnn'].setInput(blob)
                    detections = self.detection_models['dnn'].forward()
                    
                    face_locations = []
                    
                    # Extract face locations with confidence above threshold
                    for i in range(detections.shape[2]):
                        confidence = detections[0, 0, i, 2]
                        
                        if confidence > 0.5:  # Confidence threshold
                            # Get face coordinates
                            box = detections[0, 0, i, 3:7] * np.array([width, height, width, height])
                            (left, top, right, bottom) = box.astype("int")
                            
                            # Ensure coordinates are within frame
                            left = max(0, left)
                            top = max(0, top)
                            right = min(width, right)
                            bottom = min(height, bottom)
                            
                            # Convert to face_recognition format (top, right, bottom, left)
                            face_locations.append((top, right, bottom, left))
                except Exception as e:
                    logger.error(f"Error in DNN face detection: {e}")
            
            # If we used a scaled image, scale the locations back to original size
            if self.scale_factor != 1.0 and face_locations:
                face_locations = [(int(top/self.scale_factor), int(right/self.scale_factor),
                                  int(bottom/self.scale_factor), int(left/self.scale_factor))
                                 for top, right, bottom, left in face_locations]
            
            # Record detection time
            self.detection_times.append(time.time() - start_time)
            
            return face_locations
            
        except Exception as e:
            logger.error(f"Unexpected error in face detection: {e}")
            return []

    def compute_face_embeddings(self, frame, face_locations):
        """
        Compute face embeddings for the given face locations
        
        Args:
            frame (numpy.ndarray): Input image
            face_locations (list): List of face locations
            
        Returns:
            list: List of face embeddings
        """
        if not self._have_face_recognition:
            logger.warning("Face recognition library not available for computing embeddings")
            return []
            
        if not face_locations:
            return []
            
        try:
            # Convert to RGB (face_recognition uses RGB)
            rgb_frame = frame[:, :, ::-1]
            
            # Compute face encodings
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            
            return face_encodings
        except Exception as e:
            logger.error(f"Error computing face embeddings: {e}")
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
                    # Expected format: Name.ID.Number.jpg
                    parts = file.split('.')
                    if len(parts) >= 3:
                        name, student_id = parts[0], parts[1]
                        image_paths.append((image_path, name, student_id))
                    else:
                        logger.warning(f"Skipping {file}: doesn't match expected format Name.ID.Number.jpg")
        
        # Reset stored data
        self.known_face_encodings = []
        self.known_face_names = []
        self.known_face_ids = []
        
        # Process images in batches for better memory management
        total_images = len(image_paths)
        processed = 0
        failed = 0
        
        logger.info(f"Starting training with {total_images} images...")
        
        # Process images in batches
        batch_size = 16  # Process 16 images at a time
        for i in range(0, total_images, batch_size):
            batch = image_paths[i:i+batch_size]
            
            for image_path, name, student_id in batch:
                try:
                    # Different approaches depending on available libraries
                    if self._have_face_recognition:
                        # Load and process the image with face_recognition
                        image = face_recognition.load_image_file(image_path)
                        face_encodings = face_recognition.face_encodings(image)
                        
                        if face_encodings:
                            self.known_face_encodings.append(face_encodings[0])
                            self.known_face_names.append(name)
                            self.known_face_ids.append(student_id)
                            processed += 1
                        else:
                            logger.warning(f"No face found in {image_path}")
                            failed += 1
                    else:
                        # Fallback to OpenCV approach
                        image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
                        if image is None:
                            raise ValueError(f"Could not read image: {image_path}")
                            
                        # Detect face with Haar cascade
                        cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                        faces = cascade.detectMultiScale(image, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
                        
                        if len(faces) > 0:
                            # Use the first face
                            x, y, w, h = faces[0]
                            face_img = image[y:y+h, x:x+w]
                            
                            # Store face image for LBPH
                            if self.recognition_models['lbph'] is not None:
                                # Resize to standard size for consistency
                                face_img = cv2.resize(face_img, (100, 100))
                                
                                # Add to training data
                                self.known_face_encodings.append(face_img)
                                self.known_face_names.append(name)
                                self.known_face_ids.append(student_id)
                                processed += 1
                        else:
                            logger.warning(f"No face found in {image_path}")
                            failed += 1
                except Exception as e:
                    logger.error(f"Error processing image {image_path}: {e}")
                    failed += 1
            
            # Log progress
            logger.info(f"Processed {processed}/{total_images} images...")
        
        # Train LBPH recognizer if needed
        if not self._have_face_recognition and self.recognition_models['lbph'] is not None and processed > 0:
            try:
                # Prepare data for LBPH
                faces = []
                labels = []
                label_map = {}
                
                for i, (face_img, name, _) in enumerate(zip(self.known_face_encodings, self.known_face_names, self.known_face_ids)):
                    if name not in label_map:
                        label_map[name] = len(label_map)
                    
                    label = label_map[name]
                    faces.append(face_img)
                    labels.append(label)
                
                # Train LBPH
                self.recognition_models['lbph'].train(faces, np.array(labels))
                
                # Store label mapping
                self.label_map = label_map
                self.reverse_label_map = {v: k for k, v in label_map.items()}
                
                logger.info(f"Trained LBPH recognizer with {len(faces)} faces")
            except Exception as e:
                logger.error(f"Error training LBPH recognizer: {e}")
        
        logger.info(f"Training completed. {processed} faces encoded successfully. {failed} faces failed.")
        return processed > 0

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
            
            # Save differently based on recognition method
            if self._have_face_recognition:
                # Save face embeddings
                model_data = {
                    'encodings': np.array(self.known_face_encodings),
                    'names': np.array(self.known_face_names),
                    'ids': np.array(self.known_face_ids),
                    'method': 'embedding'
                }
                
                with open(model_path, 'wb') as f:
                    pickle.dump(model_data, f)
            elif self.recognition_models['lbph'] is not None:
                # Save LBPH model
                self.recognition_models['lbph'].save(model_path + '.lbph')
                
                # Save label mapping
                label_map_data = {
                    'label_map': self.label_map,
                    'names': np.array(self.known_face_names),
                    'ids': np.array(self.known_face_ids),
                    'method': 'lbph'
                }
                
                with open(model_path + '.labels', 'wb') as f:
                    pickle.dump(label_map_data, f)
            else:
                logger.error("No recognition model available to save")
                return False
            
            logger.info(f"Model saved to {model_path} with {len(self.known_face_names)} faces")
            return True
        except Exception as e:
            logger.error(f"Error saving model: {e}")
            return False

    def load_model(self, model_path):
        """
        Load a trained model
        
        Args:
            model_path (str): Path to the model
            
        Returns:
            bool: True if model was loaded successfully
        """
        try:
            if not os.path.exists(model_path):
                logger.error(f"Model file not found: {model_path}")
                return False
            
            # Try loading as pickle file first
            try:
                with open(model_path, 'rb') as f:
                    model_data = pickle.load(f)
                
                if isinstance(model_data, dict) and 'method' in model_data:
                    # Modern format with method information
                    if model_data['method'] == 'embedding':
                        self.known_face_encodings = model_data['encodings'].tolist()
                        self.known_face_names = model_data['names'].tolist()
                        self.known_face_ids = model_data['ids'].tolist()
                        logger.info(f"Loaded {len(self.known_face_names)} face embeddings")
                        return True
                    elif model_data['method'] == 'lbph':
                        # Should not happen - LBPH models are saved differently
                        logger.warning("Incorrect LBPH model format")
                        return False
                else:
                    # Older format without method information
                    # Assume it's face_recognition embeddings
                    self.known_face_encodings = model_data['encodings'].tolist()
                    self.known_face_names = model_data['names'].tolist()
                    self.known_face_ids = model_data['ids'].tolist() if 'ids' in model_data else self.known_face_names
                    logger.info(f"Loaded {len(self.known_face_names)} face embeddings (legacy format)")
                    return True
            except:
                # Not a pickle file, try LBPH format
                if os.path.exists(model_path + '.lbph') and os.path.exists(model_path + '.labels'):
                    # Load LBPH model
                    self.recognition_models['lbph'].read(model_path + '.lbph')
                    
                    # Load label mapping
                    with open(model_path + '.labels', 'rb') as f:
                        label_data = pickle.load(f)
                    
                    self.label_map = label_data['label_map']
                    self.reverse_label_map = {v: k for k, v in self.label_map.items()}
                    self.known_face_names = label_data['names'].tolist()
                    self.known_face_ids = label_data['ids'].tolist()
                    
                    logger.info(f"Loaded LBPH model with {len(self.known_face_names)} faces")
                    return True
                else:
                    # Try loading as NumPy array format (oldest format)
                    try:
                        data = np.load(model_path + '.npz')
                        self.known_face_encodings = data['encodings'].tolist()
                        self.known_face_names = data['names'].tolist()
                        self.known_face_ids = data['ids'].tolist() if 'ids' in data else self.known_face_names
                        logger.info(f"Loaded {len(self.known_face_names)} face encodings (numpy format)")
                        return True
                    except:
                        logger.error(f"Unrecognized model format: {model_path}")
                        return False
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False

    def recognize_faces(self, frame, confidence_threshold=None):
        """
        Detect and recognize faces in an image
        
        Args:
            frame (numpy.ndarray): Input image
            confidence_threshold (float, optional): Override default confidence threshold
            
        Returns:
            list: List of tuples (face_location, name, student_id, confidence)
        """
        if confidence_threshold is None:
            confidence_threshold = self.confidence_threshold
            
        # Start timing
        start_time = time.time()
        
        # Detect faces
        face_locations = self.detect_faces(frame)
        
        results = []
        
        if not face_locations:
            return results
            
        # Recognize each face
        if self._have_face_recognition:
            # Compute face encodings
            rgb_frame = frame[:, :, ::-1]
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            
            # Match each face
            for face_location, face_encoding in zip(face_locations, face_encodings):
                name, student_id, confidence = self._recognize_with_embeddings(face_encoding)
                
                if confidence >= confidence_threshold:
                    results.append((face_location, name, student_id, confidence))
                else:
                    results.append((face_location, "Unknown", "", 0.0))
        else:
            # Use LBPH recognition
            for face_location in face_locations:
                # Extract face region
                top, right, bottom, left = face_location
                face_img = frame[top:bottom, left:right]
                
                # Convert to grayscale
                gray_face = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
                
                # Resize to standard size
                gray_face = cv2.resize(gray_face, (100, 100))
                
                # Recognize with LBPH
                name, student_id, confidence = self._recognize_with_lbph(gray_face)
                
                if confidence >= confidence_threshold:
                    results.append((face_location, name, student_id, confidence))
                else:
                    results.append((face_location, "Unknown", "", 0.0))
        
        # Record recognition time
        self.recognition_times.append(time.time() - start_time)
        
        return results

    def _recognize_with_embeddings(self, face_encoding):
        """
        Recognize a face using embeddings from face_recognition
        
        Args:
            face_encoding: Face encoding to recognize
            
        Returns:
            tuple: (name, student_id, confidence)
        """
        if not self.known_face_encodings:
            return "Unknown", "", 0.0
            
        # Calculate distances
        face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
        
        if len(face_distances) == 0:
            return "Unknown", "", 0.0
            
        # Find the best match
        best_match_index = np.argmin(face_distances)
        
        # Convert distance to confidence (0-1)
        # face_distance is between 0-1, where lower values are better matches
        # we convert it to a confidence score where higher values are better
        confidence = 1.0 - min(face_distances[best_match_index], 1.0)
        
        if confidence >= self.confidence_threshold:
            name = self.known_face_names[best_match_index]
            student_id = self.known_face_ids[best_match_index]
            return name, student_id, confidence
        else:
            return "Unknown", "", confidence

    def _recognize_with_lbph(self, face_img):
        """
        Recognize a face using LBPH
        
        Args:
            face_img: Grayscale face image to recognize
            
        Returns:
            tuple: (name, student_id, confidence)
        """
        if self.recognition_models['lbph'] is None:
            return "Unknown", "", 0.0
            
        try:
            # Recognize face
            label, distance = self.recognition_models['lbph'].predict(face_img)
            
            # Convert distance to confidence (0-1)
            # LBPH distance is unbounded, so we need to convert it
            # Lower distances are better, typical good matches are <50
            confidence = max(0.0, min(1.0, 1.0 - (distance / 100.0)))
            
            if confidence >= self.confidence_threshold:
                # Get name from label
                if hasattr(self, 'reverse_label_map') and label in self.reverse_label_map:
                    name = self.reverse_label_map[label]
                    # Find the index of this name to get the student ID
                    try:
                        idx = self.known_face_names.index(name)
                        student_id = self.known_face_ids[idx]
                    except:
                        student_id = ""
                    
                    return name, student_id, confidence
            
            return "Unknown", "", confidence
        except Exception as e:
            logger.error(f"Error in LBPH recognition: {e}")
            return "Unknown", "", 0.0

    def get_performance_stats(self):
        """
        Get performance statistics
        
        Returns:
            dict: Performance statistics
        """
        detection_avg = sum(self.detection_times) / max(1, len(self.detection_times))
        recognition_avg = sum(self.recognition_times) / max(1, len(self.recognition_times))
        
        return {
            'detection_method': self.detection_method,
            'recognition_method': self.recognition_method,
            'avg_detection_time': detection_avg,
            'avg_recognition_time': recognition_avg,
            'faces_stored': len(self.known_face_names)
        }

    def cleanup(self):
        """Release resources"""
        # Clear face data
        self.known_face_encodings = []
        self.known_face_names = []
        self.known_face_ids = []
        
        # Clear performance data
        self.detection_times.clear()
        self.recognition_times.clear()
        
        # Force garbage collection
        import gc
        gc.collect() 