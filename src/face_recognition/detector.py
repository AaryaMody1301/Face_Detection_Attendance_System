"""
Face detector module for detecting and recognizing faces
"""
import os
import cv2
import numpy as np
from PIL import Image
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

class FaceDetector:
    """Face detector class for detecting and recognizing faces"""
    
    def __init__(self, cascade_path="haarcascade_frontalface_default.xml"):
        """
        Initialize the face detector
        
        Args:
            cascade_path (str): Path to the Haar cascade file
        """
        try:
            if not os.path.exists(cascade_path):
                # Try with absolute path if relative path doesn't work
                script_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
                cascade_path = os.path.join(project_root, cascade_path)
                
                # Try alternative cascade file if the default one is not found
                if not os.path.exists(cascade_path):
                    alt_cascade_path = os.path.join(project_root, "haarcascade_frontalface_alt.xml")
                    if os.path.exists(alt_cascade_path):
                        cascade_path = alt_cascade_path
                    else:
                        logger.error(f"Cascade file not found: {cascade_path}")
                        raise FileNotFoundError(f"Cascade file not found: {cascade_path}")
                
            logger.info(f"Loading cascade file: {cascade_path}")
            self.detector = cv2.CascadeClassifier(cascade_path)
            
            if self.detector.empty():
                logger.error(f"Failed to load cascade classifier from {cascade_path}")
                raise RuntimeError(f"Failed to load cascade classifier from {cascade_path}")
                
            logger.info("Creating face recognizer")
            # Check if cv2.face is available in OpenCV contrib, else use a fallback
            if hasattr(cv2, 'face'):
                self.recognizer = cv2.face.LBPHFaceRecognizer_create(
                    radius=2,           # Use a smaller radius for better detail
                    neighbors=8,        # Standard number of neighbors
                    grid_x=8,           # More grid cells for better accuracy
                    grid_y=8,           # More grid cells for better accuracy
                    threshold=100       # Default threshold
                )
            else:
                # For newer OpenCV versions with different organization
                try:
                    # Try to import the face module directly
                    from cv2 import face
                    self.recognizer = face.LBPHFaceRecognizer_create(
                        radius=2, neighbors=8, grid_x=8, grid_y=8, threshold=100
                    )
                except (ImportError, AttributeError):
                    logger.warning("OpenCV face module not found, using fallback recognition")
                    # Simple fallback for testing (will need to be replaced with actual recognition)
                    from sklearn.neighbors import KNeighborsClassifier
                    self.recognizer = KNeighborsClassifier(n_neighbors=5, weights='distance')
                    self._using_sklearn = True
                    self._faces_data = []
                    self._faces_labels = []
            
        except Exception as e:
            logger.error(f"Error initializing face detector: {e}")
            raise
        
    def detect_faces(self, image):
        """
        Detect faces in an image
        
        Args:
            image (numpy.ndarray): Input image
            
        Returns:
            list: List of detected face regions (x, y, w, h)
        """
        try:
            # Check if image is valid
            if image is None or image.size == 0:
                logger.error("Invalid image provided to detect_faces")
                return []
                
            # Convert color image to grayscale if needed
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
            
            # Apply histogram equalization for better contrast
            gray = cv2.equalizeHist(gray)
            
            # Detect faces with different parameters to improve detection
            faces = self.detector.detectMultiScale(
                gray, 
                scaleFactor=1.1,     # Smaller scale factor for better detection
                minNeighbors=5,      # Higher for better quality detections
                minSize=(30, 30),    # Minimum face size
                flags=cv2.CASCADE_SCALE_IMAGE
            )
            
            # If no faces detected, try with different parameters
            if len(faces) == 0:
                faces = self.detector.detectMultiScale(
                    gray, 
                    scaleFactor=1.2,   # Try with a larger scale factor
                    minNeighbors=3,    # Lower neighbor threshold for better detection
                    minSize=(20, 20),  # Smaller minimum face size
                    flags=cv2.CASCADE_SCALE_IMAGE
                )
            
            logger.debug(f"Detected {len(faces)} faces")
            return faces
            
        except Exception as e:
            logger.error(f"Error detecting faces: {e}")
            return []
    
    def train_recognizer(self, training_dir, labels_file=None):
        """
        Train the face recognizer with images from a directory
        
        Args:
            training_dir (str): Directory containing training images
            labels_file (str, optional): File containing labels for images
            
        Returns:
            bool: True if training was successful
        """
        try:
            logger.info(f"Training recognizer with images from {training_dir}")
            faces, ids = self.get_images_and_labels(training_dir)
            
            if len(faces) == 0:
                logger.error("No faces found in training data")
                return False
                
            logger.info(f"Training with {len(faces)} face samples")
            
            # Handle different recognizer types
            if hasattr(self, "_using_sklearn") and self._using_sklearn:
                # Reshape faces for sklearn
                faces_reshaped = [cv2.resize(f, (100, 100)).flatten() for f in faces]
                self._faces_data = faces_reshaped
                self._faces_labels = ids
                self.recognizer.fit(faces_reshaped, ids)
            else:
                # OpenCV recognizer
                self.recognizer.train(faces, np.array(ids, dtype=np.int32))
                
            logger.info("Training completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error training recognizer: {e}")
            return False
    
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
            logger.info(f"Saving model to {model_path}")
            
            # Handle different recognizer types
            if hasattr(self, "_using_sklearn") and self._using_sklearn:
                import pickle
                with open(model_path, 'wb') as f:
                    pickle.dump({
                        'model': self.recognizer,
                        'faces_data': self._faces_data,
                        'faces_labels': self._faces_labels
                    }, f)
            else:
                self.recognizer.write(model_path)
                
            logger.info("Model saved successfully")
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
            if not os.path.isfile(model_path):
                logger.error(f"Model file not found: {model_path}")
                return False
                
            logger.info(f"Loading model from {model_path}")
            
            # Handle different recognizer types
            if hasattr(self, "_using_sklearn") and self._using_sklearn:
                import pickle
                with open(model_path, 'rb') as f:
                    data = pickle.load(f)
                    self.recognizer = data['model']
                    self._faces_data = data['faces_data']
                    self._faces_labels = data['faces_labels']
            else:
                self.recognizer.read(model_path)
                
            logger.info("Model loaded successfully")
            return True
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False
    
    def recognize_face(self, image, confidence_threshold=60):
        """
        Recognize a face in an image
        
        Args:
            image (numpy.ndarray): Input image
            confidence_threshold (int): Threshold for confidence in recognition
                                       (lower value = stricter matching)
            
        Returns:
            tuple: (id, confidence) or (None, None) if no face is recognized
        """
        try:
            if image is None or image.size == 0:
                logger.error("Invalid image provided to recognize_face")
                return None, None
                
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
            
            # Apply histogram equalization to improve recognition
            gray = cv2.equalizeHist(gray)
            
            faces = self.detect_faces(gray)
            
            if len(faces) == 0:
                logger.debug("No faces detected for recognition")
                return None, None
            
            # Sort faces by area (largest first)
            faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
            
            # Recognize the largest face
            x, y, w, h = faces[0]
            face_roi = gray[y:y+h, x:x+w]
            
            # Standardize face size for more consistent recognition
            face_roi = cv2.resize(face_roi, (100, 100))
            
            # Handle different recognizer types
            if hasattr(self, "_using_sklearn") and self._using_sklearn:
                # Flatten the face
                face_flat = face_roi.flatten().reshape(1, -1)
                # Predict
                face_id = self.recognizer.predict(face_flat)[0]
                # Calculate confidence (distance to nearest neighbor)
                neighbors = self.recognizer.kneighbors(face_flat, return_distance=True)
                confidence = neighbors[0][0][0] * 100  # Scale to match OpenCV's confidence range
            else:
                # OpenCV recognizer
                face_id, confidence = self.recognizer.predict(face_roi)
            
            logger.debug(f"Face recognition result: ID={face_id}, Confidence={confidence}")
            
            # Lower confidence value means better match in OpenCV's LBPH
            if confidence < confidence_threshold:
                return face_id, confidence
            else:
                return None, confidence
                
        except Exception as e:
            logger.error(f"Error recognizing face: {e}")
            return None, None
    
    def get_images_and_labels(self, path):
        """
        Get images and labels from a directory
        
        Args:
            path (str): Path to directory containing images
            
        Returns:
            tuple: (faces, ids) where faces are image arrays and ids are corresponding ids
        """
        image_paths = [os.path.join(path, f) for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
        face_samples = []
        ids = []
        
        logger.info(f"Processing {len(image_paths)} images for training")
        
        for image_path in image_paths:
            try:
                # Skip non-image files
                if not any(image_path.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png']):
                    continue
                
                logger.debug(f"Processing image: {image_path}")
                pil_image = Image.open(image_path).convert('L')
                image_np = np.array(pil_image, 'uint8')
                
                # Apply histogram equalization for better contrast
                image_np = cv2.equalizeHist(image_np)
                
                # Extract ID from filename (format: Name.ID.sequence.jpg)
                filename = os.path.basename(image_path)
                parts = filename.split('.')
                if len(parts) >= 2:
                    try:
                        id_num = int(parts[1])
                    except ValueError:
                        logger.warning(f"Invalid ID in filename: {filename}")
                        continue
                else:
                    logger.warning(f"Invalid filename format: {filename}")
                    continue
                
                # Detect faces in the image
                faces = self.detector.detectMultiScale(
                    image_np,
                    scaleFactor=1.1,
                    minNeighbors=5,
                    minSize=(30, 30),
                    flags=cv2.CASCADE_SCALE_IMAGE
                )
                
                # If no faces detected, try with different parameters
                if len(faces) == 0:
                    faces = self.detector.detectMultiScale(
                        image_np,
                        scaleFactor=1.2,
                        minNeighbors=3,
                        minSize=(20, 20),
                        flags=cv2.CASCADE_SCALE_IMAGE
                    )
                
                # If still no faces detected, skip this image
                if len(faces) == 0:
                    logger.warning(f"No face detected in {image_path}")
                    continue
                    
                # Use the largest face if multiple faces are detected
                if len(faces) > 1:
                    faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
                    logger.debug(f"Multiple faces ({len(faces)}) detected in {image_path}, using largest")
                
                # Extract face region
                for (x, y, w, h) in faces[:1]:  # Only use the first (largest) face
                    face_roi = image_np[y:y+h, x:x+w]
                    
                    # Standardize face size for better training
                    face_roi = cv2.resize(face_roi, (100, 100))
                    
                    face_samples.append(face_roi)
                    ids.append(id_num)
                    logger.debug(f"Added face with ID {id_num}")
                    break
                    
            except Exception as e:
                logger.error(f"Error processing {image_path}: {e}")
                
        logger.info(f"Processed {len(face_samples)} face samples with {len(set(ids))} unique IDs")
        return face_samples, ids