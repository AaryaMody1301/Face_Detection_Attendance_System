"""
Face Detector module for Face Detection Attendance System
"""
import os
import cv2
import time
import logging
import numpy as np
import tkinter as tk
import threading
from PIL import Image
import pickle
from pathlib import Path
import pandas as pd
import face_recognition
import datetime
import csv

# Set up logging
logger = logging.getLogger(__name__)

class FaceDetector:
    """Face detection and recognition class"""
    
    def __init__(self, method='haar', threshold=0.6, students_csv_path=None):
        """Initialize face detector with specified detection method and threshold"""
        self.detection_method = method
        self.confidence_threshold = threshold
        self.student_data_path = students_csv_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            "data", "students.csv"
        )
        
        # Define model path and training directory
        self.model_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            "models", "face_recognizer.yml"
        )
        self.training_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            "data", "training_images"
        )
        
        # Create directories
        os.makedirs(os.path.dirname(self.student_data_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        os.makedirs(self.training_dir, exist_ok=True)
        
        # Store student data
        self.student_data = {}
        self.student_names = {}
        self._is_recognizer_trained = False
        
        # Initialize models based on detection method
        try:
            self._init_models()
            
            # Load student data
            self.student_data = self._load_student_data()
            logger.info(f"Loaded {len(self.student_data)} student records")
            
        except Exception as e:
            logger.error(f"Error initializing face detector: {e}")
            raise
    
    def _init_models(self):
        """Initialize face detection models based on selected method"""
        try:
            # Always load Haar cascade for basic detection
            cascade_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                      'models', 'haarcascade_frontalface_default.xml')
            
            if not os.path.exists(cascade_path):
                logger.error(f"Haar cascade file not found at: {cascade_path}")
                # Try to find it in OpenCV's data directory
                opencv_cascade_path = os.path.join(cv2.data.haarcascades, 'haarcascade_frontalface_default.xml')
                if os.path.exists(opencv_cascade_path):
                    logger.info(f"Using OpenCV's built-in cascade: {opencv_cascade_path}")
                    cascade_path = opencv_cascade_path
                else:
                    # If OpenCV's path is not found, try to find the file anywhere on the system
                    logger.error("OpenCV's built-in cascade not found either")
                    raise FileNotFoundError(f"Haar cascade file not found: {cascade_path}")
            
            # Load the Haar cascade
            self.face_cascade = cv2.CascadeClassifier(cascade_path)
            if self.face_cascade.empty():
                logger.error(f"Failed to load Haar cascade from {cascade_path}")
                raise ValueError("Failed to load Haar cascade classifier")
            else:
                logger.info(f"Loaded Haar cascade from {cascade_path}")
            
            # Initialize face recognizer (using LBPH for simplicity and compatibility)
            self.recognizer = cv2.face.LBPHFaceRecognizer_create()
            logger.info("Created LBPH face recognizer")
            
            # Load pre-trained model if it exists
            self._load_recognizer_if_exists()
            
            # Initialize optional methods based on configuration
            if self.detection_method in ['hog', 'cnn']:
                try:
                    import face_recognition
                    logger.info(f"Using {self.detection_method.upper()} method with face_recognition library")
                except ImportError:
                    logger.warning("face_recognition library not available, falling back to Haar cascade")
                    self.detection_method = 'haar'
        
        except Exception as e:
            logger.error(f"Error initializing face detection models: {e}")
            raise
    
    def _load_student_data(self):
        """Load student data from CSV"""
        try:
            # Create student data file if not exists
            if not os.path.exists(self.student_data_path):
                logger.info(f"Creating new student data file at {self.student_data_path}")
                os.makedirs(os.path.dirname(self.student_data_path), exist_ok=True)
                with open(self.student_data_path, 'w', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow(['ID', 'Name', 'Encoding', 'Last Updated'])
            
            # Read data from CSV
            student_data = {}
            with open(self.student_data_path, 'r') as file:
                reader = csv.DictReader(file)
                
                # Verify required columns exist
                headers = reader.fieldnames
                required_fields = ['ID', 'Name', 'Encoding']
                
                if not headers or not all(field in headers for field in required_fields):
                    logger.error(f"Student data file missing required columns: {required_fields}")
                    # Create a new file with correct headers
                    with open(self.student_data_path, 'w', newline='') as new_file:
                        writer = csv.writer(new_file)
                        writer.writerow(['ID', 'Name', 'Encoding', 'Last Updated'])
                    return {}
                
                # Process student data
                for row in reader:
                    # Skip invalid rows
                    if not row.get('ID') or not row.get('Name'):
                        logger.warning(f"Skipping invalid student record: {row}")
                        continue
                        
                    student_id = row['ID']
                    encoding_str = row.get('Encoding', '')
                    
                    if encoding_str:
                        try:
                            # Convert encoding string back to numpy array
                            encoding = np.fromstring(encoding_str.strip('[]'), sep=',')
                            student_data[student_id] = {
                                'name': row['Name'],
                                'encoding': encoding,
                                'last_updated': row.get('Last Updated', '')
                            }
                        except Exception as e:
                            logger.error(f"Error parsing encoding for student {student_id}: {e}")
                    else:
                        # Store student without encoding
                        student_data[student_id] = {
                            'name': row['Name'],
                            'encoding': None,
                            'last_updated': row.get('Last Updated', '')
                        }
                
            logger.info(f"Loaded {len(student_data)} student records")
            return student_data
            
        except Exception as e:
            logger.error(f"Error loading student data: {e}")
            return {}
    
    def _load_recognizer_if_exists(self):
        """Load the pre-trained face recognizer model if it exists"""
        try:
            # Define model path if not already defined
            if not hasattr(self, 'model_path'):
                self.model_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                    "models", "face_recognizer.yml"
                )
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
                
            if os.path.exists(self.model_path):
                self.recognizer.read(self.model_path)
                logger.info(f"Loaded face recognizer model from {self.model_path}")
                self._is_recognizer_trained = True
                return True
            else:
                logger.warning(f"No face recognizer model found at {self.model_path}")
                self._is_recognizer_trained = False
                return False
        except Exception as e:
            logger.error(f"Error loading face recognizer model: {e}")
            self._is_recognizer_trained = False
            return False
    
    def _train_recognizer_if_needed(self):
        """Train face recognizer if training data is available"""
        try:
            # Define training directory if not already defined
            if not hasattr(self, 'training_dir'):
                self.training_dir = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                    "data", "training_images"
                )
                # Create directory if it doesn't exist
                os.makedirs(self.training_dir, exist_ok=True)
                
            # Define model path if not already defined
            if not hasattr(self, 'model_path'):
                self.model_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                    "models", "face_recognizer.yml"
                )
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
                
            # Check if training directory exists
            if not os.path.exists(self.training_dir):
                logger.warning(f"Training images directory not found: {self.training_dir}")
                os.makedirs(self.training_dir, exist_ok=True)
                logger.info(f"Created training images directory: {self.training_dir}")
                
                # Try to import from backup if available
                if hasattr(self, '_import_backup_training_images') and self._import_backup_training_images():
                    logger.info("Successfully imported training images from backup")
                else:
                    logger.warning("No backup training images available")
                    return False
            
            # Count image files in training directory
            image_files = []
            for root, _, files in os.walk(self.training_dir):
                for file in files:
                    if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                        image_files.append(os.path.join(root, file))
            
            # If no images found, try to import from backup again
            if len(image_files) == 0:
                logger.warning("No training images found in main directory, trying backup...")
                if self._import_backup_training_images():
                    logger.info("Successfully imported training images from backup")
                    # Refresh image list
                    image_files = []
                    for root, _, files in os.walk(self.training_dir):
                        for file in files:
                            if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                                image_files.append(os.path.join(root, file))
                else:
                    logger.warning("No training images found and no backup available, skipping recognizer training")
                    return False
            
            # Check again if we have images
            if len(image_files) == 0:
                logger.warning("No training images found, skipping recognizer training")
                return False
            
            # Check if model exists and is newer than training images
            if os.path.exists(self.model_path):
                model_time = os.path.getmtime(self.model_path)
                newest_image_time = max(os.path.getmtime(img) for img in image_files) if image_files else 0
                
                if model_time > newest_image_time:
                    logger.info("Face recognizer model is up to date, skipping training")
                    self._is_recognizer_trained = True
                    return True
            
            # Train the recognizer with available images
            logger.info(f"Training face recognizer with {len(image_files)} images")
            
            # Collect training data
            faces = []
            labels = []
            
            for img_path in image_files:
                try:
                    # Extract student ID from filename (e.g., "1001_1.jpg" -> 1001)
                    filename = os.path.basename(img_path)
                    parent_dir = os.path.basename(os.path.dirname(img_path))
                    
                    # Try different methods to get the student ID
                    student_id = None
                    
                    # First try the directory name (preferred method)
                    try:
                        student_id = int(parent_dir)
                    except ValueError:
                        # If directory name is not a number, try to extract from filename
                        try:
                            # Format: StudentID_number.jpg or StudentID.number.jpg
                            if '_' in filename:
                                student_id = int(filename.split('_')[0])
                            elif '.' in filename:
                                parts = filename.split('.')
                                if len(parts) > 1 and parts[0].isdigit():
                                    student_id = int(parts[0])
                        except ValueError:
                            pass
                    
                    # If still no ID, try one more method (e.g., 123_1.jpg or 123.1.jpg)
                    if student_id is None:
                        try:
                            # Directory name might be "Name_ID"
                            if '_' in parent_dir:
                                student_id = int(parent_dir.split('_')[-1])
                        except ValueError:
                            logger.warning(f"Could not extract student ID from {img_path}")
                            continue
                    
                    # If we have a valid ID, process the image
                    if student_id is not None:
                        # Read and preprocess image
                        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
                        if img is None:
                            logger.warning(f"Could not read image: {img_path}")
                            continue
                        
                        # Detect face in the image
                        detected_faces = self.face_cascade.detectMultiScale(
                            img, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
                        
                        # If face found, add to training data
                        if len(detected_faces) > 0:
                            x, y, w, h = detected_faces[0]  # Use first detected face
                            face_roi = img[y:y+h, x:x+w]
                            # Resize face to a standard size for more consistent training
                            face_roi = cv2.resize(face_roi, (100, 100))
                            faces.append(face_roi)
                            labels.append(student_id)
                            logger.debug(f"Added face from {img_path} with ID {student_id}")
                    else:
                            logger.warning(f"No face detected in training image: {img_path}")
                
                except Exception as e:
                    logger.error(f"Error processing training image {img_path}: {e}")
            
            # If we have faces to train with
            if len(faces) > 0:
                logger.info(f"Training recognizer with {len(faces)} face images for {len(set(labels))} students")
                self.recognizer.train(faces, np.array(labels))
                
                # Save the trained model
                os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
                self.recognizer.write(self.model_path)
                logger.info(f"Saved trained recognizer model to {self.model_path}")
                self._is_recognizer_trained = True
                
                # Add any missing students to the student data
                self._ensure_students_in_data(set(labels))
                
                return True
            else:
                logger.warning("No valid faces found in training images, skipping training")
                self._is_recognizer_trained = False
                return False
        
        except Exception as e:
            logger.error(f"Error training face recognizer: {e}")
            self._is_recognizer_trained = False
            return False
            
    def _ensure_students_in_data(self, student_ids):
        """Ensure all trained student IDs are in the student data"""
        if self.student_data is None or self.students_csv_path is None:
            return
            
        # Convert existing IDs to strings for comparison
        existing_ids = set(self.student_data['ID'].astype(str))
        
        # Find missing IDs
        missing_ids = []
        for student_id in student_ids:
            if str(student_id) not in existing_ids:
                missing_ids.append(str(student_id))
        
        # If we have missing IDs, add them to the student data
        if missing_ids:
            new_students = []
            for student_id in missing_ids:
                new_students.append({
                    'ID': student_id,
                    'Name': f"Student {student_id}",
                    'Course': 'Unknown',
                    'Year': str(datetime.datetime.now().year)
                })
                
            # Add to DataFrame
            new_data = pd.DataFrame(new_students)
            self.student_data = pd.concat([self.student_data, new_data], ignore_index=True)
            
            # Save to CSV
            self.student_data.to_csv(self.students_csv_path, index=False)
            
            # Update mapping
            for _, row in new_data.iterrows():
                id_value = row['ID']
                try:
                    id_int = int(id_value) if str(id_value).isdigit() else id_value
                    self.student_names[id_int] = row['Name']
                except Exception as e:
                    logger.error(f"Error converting ID {id_value} to int: {e}")
            
            logger.info(f"Added {len(missing_ids)} missing students to the student data")
    
    def detect_faces(self, frame):
        """
        Detect faces in an input frame
        
        Args:
            frame: Input frame (RGB format)
            
        Returns:
            List of face regions as (x, y, w, h)
        """
        try:
            # Convert to grayscale if the image is not already grayscale
            if len(frame.shape) == 3:
                gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
            else:
                gray = frame
                
            # Apply Haar cascade to detect faces
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )
            
            return faces
            
        except Exception as e:
            logger.error(f"Error detecting faces: {e}")
            return []

    def recognize_face(self, face_img):
        """
        Recognize a face against the trained model
        
        Args:
            face_img: Face image (RGB format)
            
        Returns:
            Tuple of (student_id, confidence)
        """
        try:
            # Convert to grayscale if needed
            if len(face_img.shape) == 3:
                gray = cv2.cvtColor(face_img, cv2.COLOR_RGB2GRAY)
            else:
                gray = face_img
                
            # Resize to a consistent size
            gray = cv2.resize(gray, (100, 100))
            
            # Perform recognition using LBPH
            student_id, confidence = self.recognizer.predict(gray)
            
            # Return the results
            return student_id, confidence
            
        except Exception as e:
            logger.error(f"Error recognizing face: {e}")
            return None, 100  # High confidence value (100% distance) indicates no match
    
    def get_student_name(self, student_id):
        """
        Get student name from student ID
        
        Args:
            student_id: Student ID
            
        Returns:
            Student name or 'Unknown'
        """
        try:
            return self.student_names.get(student_id, "Unknown")
        except Exception as e:
            logger.error(f"Error getting student name: {e}")
            return "Unknown"

    def save_student(self, student_id, student_name, encoding=None):
        """Save or update student data"""
        if not student_id or student_id.strip() == '':
            logger.error("Cannot save student: Empty student ID")
            return False
            
        if not student_name or student_name.strip() == '':
            logger.error(f"Cannot save student {student_id}: Empty student name")
            return False
        
        try:
            # Convert ID to string for consistency
            student_id = str(student_id).strip()
            student_name = str(student_name).strip()
            
            # Update in-memory data
            self.student_data[student_id] = {
                'name': student_name,
                'encoding': encoding,
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Prepare data for CSV
            rows = []
            for id, data in self.student_data.items():
                encoding_str = ''
                if data['encoding'] is not None:
                    encoding_str = np.array2string(data['encoding'], separator=',').replace('\n', '')
                
                rows.append({
                    'ID': id,
                    'Name': data['name'],
                    'Encoding': encoding_str,
                    'Last Updated': data.get('last_updated', '')
                })
            
            # Create directory if not exists
            os.makedirs(os.path.dirname(self.student_data_path), exist_ok=True)
            
            # Write to CSV
            with open(self.student_data_path, 'w', newline='') as file:
                fieldnames = ['ID', 'Name', 'Encoding', 'Last Updated']
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            
            logger.info(f"Saved student data for {student_name} (ID: {student_id})")
            return True
            
        except Exception as e:
            logger.error(f"Error saving student details: {e}")
            return False