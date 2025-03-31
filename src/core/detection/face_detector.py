"""
Unified Face Detection and Recognition Module
This module provides face detection and recognition capabilities
to be used by both UI implementations.
"""
import os
import cv2
import numpy as np
import logging
from PIL import Image
import pickle

# Set up logger
logger = logging.getLogger(__name__)

class FaceDetector:
    """
    Face detection and recognition using OpenCV and face_recognition library
    if available, with fallback to Haar cascades.
    """
    
    def __init__(self):
        """Initialize the face detector"""
        # Initialize variables
        self.recognizer = None
        self.faceCascade = None
        self.confidence_threshold = 60
        self._initialize_detectors()
        self.face_recognition_available = self._check_face_recognition()
        
    def _check_face_recognition(self):
        """Check if face_recognition library is available"""
        try:
            import face_recognition
            logger.info("face_recognition library is available")
            return True
        except ImportError:
            logger.warning("face_recognition library is not available. Using OpenCV cascades.")
            return False
    
    def _initialize_detectors(self):
        """Initialize face detection models"""
        try:
            # Create LBPH face recognizer
            self.recognizer = cv2.face.LBPHFaceRecognizer_create()
            
            # Load Haar cascade classifier
            cascade_path = self._get_cascade_path()
            if os.path.exists(cascade_path):
                self.faceCascade = cv2.CascadeClassifier(cascade_path)
            else:
                logger.warning(f"Haar cascade file not found: {cascade_path}")
                # Try to use a cascade from OpenCV's data directory
                self.faceCascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        except Exception as e:
            logger.error(f"Error initializing face detectors: {e}")
            raise
    
    def _get_cascade_path(self):
        """Get the path to the Haar cascade file"""
        # Try to find cascade file in several locations
        possible_paths = [
            os.path.join("models", "haarcascade_frontalface_default.xml"),
            os.path.join("data", "haarcascade_frontalface_default.xml"),
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml',
        ]
        
        # Return first path that exists
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # If no path found, return the default path
        return os.path.join("models", "haarcascade_frontalface_default.xml")
    
    def set_confidence_threshold(self, threshold):
        """
        Set the confidence threshold for face recognition
        
        Args:
            threshold (float): Lower values are stricter (0-100)
        """
        self.confidence_threshold = threshold
    
    def detect_faces(self, gray_img):
        """
        Detect faces in a grayscale image
        
        Args:
            gray_img (numpy.ndarray): Grayscale image
            
        Returns:
            list: List of (x, y, w, h) face rectangles
        """
        try:
            if self.face_recognition_available:
                try:
                    import face_recognition
                    # Convert grayscale to RGB for face_recognition library
                    if len(gray_img.shape) == 2:
                        rgb_img = cv2.cvtColor(gray_img, cv2.COLOR_GRAY2RGB)
                    else:
                        rgb_img = cv2.cvtColor(gray_img, cv2.COLOR_BGR2RGB)
                    
                    # Find face locations
                    face_locations = face_recognition.face_locations(rgb_img, model="hog")
                    
                    # Convert from (top, right, bottom, left) to (x, y, w, h)
                    faces = []
                    for face in face_locations:
                        top, right, bottom, left = face
                        x, y = left, top
                        w, h = right - left, bottom - top
                        faces.append((x, y, w, h))
                    
                    return faces
                except Exception as e:
                    logger.warning(f"Error using face_recognition library: {e}")
                    # Fall back to OpenCV cascades
            
            # Use OpenCV cascade classifier as fallback
            if self.faceCascade is not None:
                faces = self.faceCascade.detectMultiScale(
                    gray_img,
                    scaleFactor=1.3,
                    minNeighbors=5,
                    minSize=(30, 30),
                    flags=cv2.CASCADE_SCALE_IMAGE
                )
                return faces if len(faces) > 0 else []
            else:
                logger.error("No face detector available")
                return []
        except Exception as e:
            logger.error(f"Error detecting faces: {e}")
            return []
    
    def train_recognizer(self, data_folder):
        """
        Train the face recognizer with the images in the given folder
        
        Args:
            data_folder (str): Path to the folder containing face images
            
        Returns:
            bool: Success or failure
        """
        try:
            if not os.path.isdir(data_folder):
                logger.error(f"Training data folder not found: {data_folder}")
                return False
            
            # Get all image paths
            image_paths = [os.path.join(data_folder, f) for f in os.listdir(data_folder)
                        if os.path.isfile(os.path.join(data_folder, f)) and
                        f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            
            if not image_paths:
                logger.error("No images found for training")
                return False
            
            # Initialize lists for training data
            faces = []
            ids = []
            labels = {}  # Map from ID to name
            
            # Read images and extract faces and IDs
            for image_path in image_paths:
                try:
                    # Expected format: Name.ID.sequence.jpg
                    filename = os.path.basename(image_path)
                    parts = filename.split('.')
                    
                    if len(parts) >= 3:
                        name = parts[0]
                        student_id = parts[1]
                        
                        # Store label mapping
                        labels[student_id] = name
                        
                        # Read image and convert to grayscale
                        img = cv2.imread(image_path)
                        if img is None:
                            logger.warning(f"Could not read image: {image_path}")
                            continue
                            
                        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                        
                        # Extract face if needed
                        detected_faces = self.detect_faces(gray)
                        
                        if len(detected_faces) > 0:
                            # Use the largest face if multiple are found
                            detected_faces = sorted(detected_faces, key=lambda f: f[2] * f[3], reverse=True)
                            (x, y, w, h) = detected_faces[0]
                            face_img = gray[y:y+h, x:x+w]
                        else:
                            # Assume the entire image is a face (already cropped)
                            face_img = gray
                        
                        # Standardize size
                        face_img = cv2.resize(face_img, (200, 200))
                        
                        # Add to training data
                        faces.append(face_img)
                        ids.append(int(student_id))
                        
                except Exception as e:
                    logger.warning(f"Error processing image {image_path}: {e}")
            
            if not faces:
                logger.error("No valid faces found for training")
                return False
            
            # Train the recognizer
            self.recognizer.train(faces, np.array(ids))
            
            # Save the labels
            self._save_labels(labels)
            
            return True
            
        except Exception as e:
            logger.error(f"Error training recognizer: {e}")
            return False
    
    def _save_labels(self, labels):
        """Save the ID to name mappings"""
        try:
            # Ensure directory exists
            os.makedirs("TrainingImageLabel", exist_ok=True)
            
            # Save labels to a pickle file
            with open(os.path.join("TrainingImageLabel", "labels.pkl"), 'wb') as f:
                pickle.dump(labels, f)
                
        except Exception as e:
            logger.error(f"Error saving labels: {e}")
    
    def _load_labels(self):
        """Load the ID to name mappings"""
        try:
            # Path to labels file
            labels_path = os.path.join("TrainingImageLabel", "labels.pkl")
            
            if os.path.exists(labels_path):
                with open(labels_path, 'rb') as f:
                    return pickle.load(f)
            else:
                logger.warning(f"Labels file not found: {labels_path}")
                return {}
                
        except Exception as e:
            logger.error(f"Error loading labels: {e}")
            return {}
    
    def save_model(self, model_path):
        """
        Save the trained model to a file
        
        Args:
            model_path (str): Path where to save the model
            
        Returns:
            bool: Success or failure
        """
        try:
            # Make sure directory exists
            os.makedirs(os.path.dirname(model_path), exist_ok=True)
            
            # Save the model
            self.recognizer.write(model_path)
            
            # Also save as .yml.npz for compatibility with newer OpenCV versions
            if not model_path.endswith('.npz'):
                npz_path = model_path + '.npz'
                self.recognizer.write(npz_path)
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving model: {e}")
            return False
    
    def load_model(self, model_path):
        """
        Load a trained model from a file
        
        Args:
            model_path (str): Path to the model file
            
        Returns:
            bool: Success or failure
        """
        try:
            # First try to load the model directly
            try:
                self.recognizer.read(model_path)
                return True
            except cv2.error:
                # If that fails, try alternate paths/formats
                npz_path = model_path + '.npz'
                if os.path.exists(npz_path):
                    self.recognizer.read(npz_path)
                    return True
                
                # Try alternate case
                if model_path.endswith('trainner.yml'):
                    alt_path = model_path.replace('trainner.yml', 'Trainner.yml')
                    if os.path.exists(alt_path):
                        self.recognizer.read(alt_path)
                        return True
                
                # Try alternative format
                yml_path = model_path.replace('.npz', '')
                if os.path.exists(yml_path):
                    self.recognizer.read(yml_path)
                    return True
                    
                logger.error(f"Model file not found: {model_path}")
                return False
                
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False
    
    def recognize_faces(self, img):
        """
        Detect and recognize faces in an image
        
        Args:
            img (numpy.ndarray): Input image
            
        Returns:
            tuple: (face_locations, face_names)
        """
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            face_locations = []
            face_names = []
            
            if self.face_recognition_available:
                try:
                    import face_recognition
                    
                    # Convert to RGB for face_recognition library
                    rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    
                    # Find face locations
                    face_locations = face_recognition.face_locations(rgb_img, model="hog")
                    
                    # For each face, attempt to recognize
                    for face in face_locations:
                        top, right, bottom, left = face
                        
                        # Extract face ROI
                        face_img = gray[top:bottom, left:right]
                        
                        # Resize for the recognizer
                        if face_img.size > 0:
                            face_img = cv2.resize(face_img, (200, 200))
                            
                            # Predict
                            try:
                                if self.recognizer:
                                    id_, confidence = self.recognizer.predict(face_img)
                                    
                                    # Lower confidence means better match in OpenCV
                                    if confidence < 100 - self.confidence_threshold:
                                        # Get name from ID
                                        labels = self._load_labels()
                                        name = labels.get(str(id_), f"ID:{id_}")
                                        face_names.append(name)
                                    else:
                                        face_names.append("Unknown")
                                else:
                                    face_names.append("Unknown")
                            except Exception as e:
                                logger.warning(f"Error in recognition: {e}")
                                face_names.append("Unknown")
                        else:
                            face_names.append("Unknown")
                            
                    return face_locations, face_names
                
                except Exception as e:
                    logger.warning(f"Error using face_recognition library: {e}")
                    # Fall back to OpenCV
            
            # Use OpenCV cascade as fallback
            faces = self.detect_faces(gray)
            
            # Convert format and recognize each face
            for (x, y, w, h) in faces:
                face_img = gray[y:y+h, x:x+w]
                
                # Resize for the recognizer
                face_img = cv2.resize(face_img, (200, 200))
                
                try:
                    if self.recognizer:
                        id_, confidence = self.recognizer.predict(face_img)
                        
                        # Lower confidence means better match in OpenCV
                        if confidence < 100 - self.confidence_threshold:
                            # Get name from ID
                            labels = self._load_labels()
                            name = labels.get(str(id_), f"ID:{id_}")
                        else:
                            name = "Unknown"
                    else:
                        name = "Unknown"
                except Exception as e:
                    logger.warning(f"Error in recognition: {e}")
                    name = "Unknown"
                
                # Add to results
                face_locations.append((y, x+w, y+h, x))  # Format: (top, right, bottom, left)
                face_names.append(name)
            
            return face_locations, face_names
            
        except Exception as e:
            logger.error(f"Error recognizing faces: {e}")
            return [], []
        
    def draw_face_rectangles(self, img, face_locations, face_names):
        """
        Draw rectangles and labels around detected faces
        
        Args:
            img (numpy.ndarray): Input image
            face_locations (list): List of face locations
            face_names (list): List of face names
            
        Returns:
            numpy.ndarray: Image with rectangles and labels drawn
        """
        try:
            # Make a copy of the image
            img_copy = img.copy()
            
            # Draw a rectangle around each face along with the name
            for (top, right, bottom, left), name in zip(face_locations, face_names):
                # Draw rectangle
                color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
                cv2.rectangle(img_copy, (left, top), (right, bottom), color, 2)
                
                # Draw label background
                cv2.rectangle(img_copy, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
                
                # Draw name
                font = cv2.FONT_HERSHEY_DUPLEX
                cv2.putText(img_copy, name, (left + 6, bottom - 6), font, 0.8, (255, 255, 255), 1)
            
            return img_copy
            
        except Exception as e:
            logger.error(f"Error drawing face rectangles: {e}")
            return img