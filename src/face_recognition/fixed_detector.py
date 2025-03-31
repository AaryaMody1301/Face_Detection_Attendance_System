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

# Set up logging
logger = logging.getLogger(__name__)

class FaceDetector:
    """Face detection and recognition class"""
    
    def __init__(self, method='haar', threshold=0.6, students_csv_path=None):
        """
        Initialize face detector with specified method
        
        Parameters:
        -----------
        method : str
            Face detection method ('haar', 'hog', or 'cnn')
        threshold : float
            Confidence threshold for face recognition (0.0-1.0)
        students_csv_path : str or None
            Path to CSV file with student data (ID, Name, Course, Year)
        """
        self.method = method
        self.threshold = threshold
        self.students_csv_path = students_csv_path
        self.face_cascade = None
        self.recognizer = None
        self.student_data = None
        self.student_names = {}  # Map of ID to name
        self._is_recognizer_trained = False  # Flag to track if recognizer has been trained
        self.model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                    'models', 'face_recognizer.yml')
        self.training_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                      'data', 'training_images')
        # Define path to backup training images
        self.backup_training_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                                           'backups', 'training_image_backup', 'Organized')
        
        # Initialize face detection models
        self._init_models()
        
        # Load student data if path provided
        if students_csv_path:
            try:
                self._load_student_data(students_csv_path)
                # Check for backup training images and copy them if needed
                self._import_backup_training_images()
                # Train face recognizer if needed
                self._train_recognizer_if_needed()
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
            if self.method in ['hog', 'cnn']:
                try:
                    import face_recognition
                    logger.info(f"Using {self.method.upper()} method with face_recognition library")
                except ImportError:
                    logger.warning("face_recognition library not available, falling back to Haar cascade")
                    self.method = 'haar'
        
        except Exception as e:
            logger.error(f"Error initializing face detection models: {e}")
            raise
    
    def _load_student_data(self, csv_path):
        """Load student data from CSV file"""
        try:
            if not os.path.exists(csv_path):
                logger.error(f"Student data CSV not found: {csv_path}")
                # Create the CSV file with default content
                self._create_default_student_csv(csv_path)
            
            # Read CSV with proper encoding handling
            encodings_to_try = ['utf-8', 'latin1', 'cp1252']
            success = False
            
            for encoding in encodings_to_try:
                try:
                    self.student_data = pd.read_csv(csv_path, encoding=encoding)
                    success = True
                    logger.info(f"Successfully loaded CSV with encoding: {encoding}")
                    break
                except UnicodeDecodeError:
                    logger.warning(f"Failed to load CSV with encoding: {encoding}")
                except Exception as e:
                    logger.error(f"Error loading CSV with encoding {encoding}: {e}")
            
            if not success:
                logger.error("Failed to load CSV with all encodings, creating a new one")
                self._create_default_student_csv(csv_path)
                self.student_data = pd.read_csv(csv_path, encoding='utf-8')
            
            # Ensure required columns exist
            required_columns = ['ID', 'Name']
            missing_columns = [col for col in required_columns if col not in self.student_data.columns]
            
            if missing_columns:
                logger.error(f"Required columns missing in student data: {missing_columns}")
                # Try to fix column names if they exist with different case
                for column in missing_columns:
                    # First try to find columns with same name but different case
                    for existing_col in self.student_data.columns:
                        if existing_col.lower() == column.lower():
                            self.student_data = self.student_data.rename(columns={existing_col: column})
                            logger.info(f"Renamed column from {existing_col} to {column}")
                            missing_columns.remove(column)
                            break
            
            # Check again after fixes
            missing_columns = [col for col in required_columns if col not in self.student_data.columns]
            if missing_columns:
                logger.error(f"Required columns still missing in student data: {missing_columns}")
                # Create new file with correct columns
                self._create_default_student_csv(csv_path)
                self.student_data = pd.read_csv(csv_path, encoding='utf-8')
            
            # Create mapping of ID to name
            for _, row in self.student_data.iterrows():
                # Convert ID to string or int as needed
                id_value = row['ID']
                # Convert to int for face recognition (needs numeric IDs)
                id_int = int(id_value) if isinstance(id_value, (str, int)) else id_value
                self.student_names[id_int] = row['Name']
            
            logger.info(f"Loaded {len(self.student_data)} students from {csv_path}")
            logger.debug(f"Student names mapping: {self.student_names}")
        
        except Exception as e:
            logger.error(f"Error loading student data: {e}")
            raise
            
    def _create_default_student_csv(self, csv_path):
        """Create a default student CSV file with sample data"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(csv_path), exist_ok=True)
            
            # Write CSV with default content
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                f.write("ID,Name,Course,Year\n")
                f.write("1001,John Smith,Computer Science,2023\n")
                f.write("1002,Jane Doe,Mathematics,2024\n")
                f.write("1003,Robert Johnson,Physics,2023\n")
                f.write("1004,Emily Wilson,Biology,2025\n")
            
            logger.info(f"Created default student CSV at {csv_path}")
            return True
        except Exception as e:
            logger.error(f"Error creating default student CSV: {e}")
            return False
    
    def _import_backup_training_images(self):
        """Import training images from backup folder if available"""
        try:
            # Check if backup training directory exists
            if not os.path.exists(self.backup_training_dir):
                logger.warning(f"Backup training directory not found: {self.backup_training_dir}")
                return False
            
            # Check if main training directory exists, create if not
            if not os.path.exists(self.training_dir):
                os.makedirs(self.training_dir, exist_ok=True)
                logger.info(f"Created training images directory: {self.training_dir}")
            
            # Check if backup has images and if main training dir is empty
            backup_has_images = False
            for item in os.listdir(self.backup_training_dir):
                if os.path.isdir(os.path.join(self.backup_training_dir, item)):
                    backup_has_images = True
                    break
        
            main_dir_empty = True
            if os.path.exists(self.training_dir):
                main_dir_empty = len(os.listdir(self.training_dir)) == 0
            
            # If backup has images and main training dir is empty, import them
            if backup_has_images and main_dir_empty:
                logger.info(f"Importing training images from backup: {self.backup_training_dir}")
                
                # Check and update student data with backup folder info
                self._update_student_data_from_backup()
                
                # Copy images from backup to training directory
                imported_count = 0
                for student_dir in os.listdir(self.backup_training_dir):
                    student_path = os.path.join(self.backup_training_dir, student_dir)
                    if os.path.isdir(student_path):
                        # Extract student ID from the folder name (e.g., "John_123" -> "123")
                        try:
                            # Format could be either Name_ID or just ID
                            parts = student_dir.split('_')
                            if len(parts) > 1:
                                student_id = parts[-1]  # Last part should be the ID
                            else:
                                student_id = student_dir  # Assume folder name is the ID
                                
                            # Create target directory
                            target_dir = os.path.join(self.training_dir, student_id)
                            os.makedirs(target_dir, exist_ok=True)
                            
                            # Copy images to target directory
                            file_count = 0
                            for filename in os.listdir(student_path):
                                if filename.lower().endswith(('.jpg', '.jpeg', '.png')) and not os.path.isdir(os.path.join(student_path, filename)):
                                    # Copy the file with a standardized name
                                    src_file = os.path.join(student_path, filename)
                                    dst_file = os.path.join(target_dir, f"{student_id}_{file_count}.jpg")
                                    
                                    # Read and save to ensure format compatibility
                                    img = cv2.imread(src_file)
                                    if img is not None:
                                        cv2.imwrite(dst_file, img)
                                        file_count += 1
                                        imported_count += 1
                            
                            logger.info(f"Imported {file_count} images for student ID: {student_id}")
                        except Exception as e:
                            logger.error(f"Error importing images for {student_dir}: {e}")
                
                logger.info(f"Total training images imported: {imported_count}")
                return imported_count > 0
            else:
                if not backup_has_images:
                    logger.info("No backup training images found")
                else:
                    logger.info("Training directory already has images, skipping import")
                return False
                
        except Exception as e:
            logger.error(f"Error importing backup training images: {e}")
            return False
            
    def _update_student_data_from_backup(self):
        """Update student data from backup folder names"""
        try:
            # Check if backup training directory exists
            if not os.path.exists(self.backup_training_dir):
                return False
            
            # Get current student data
            students_to_add = []
            
            # Process each student directory in backup
            for student_dir in os.listdir(self.backup_training_dir):
                student_path = os.path.join(self.backup_training_dir, student_dir)
                if os.path.isdir(student_path):
                    try:
                        # Extract student name and ID from the folder name (e.g., "John_123")
                        parts = student_dir.split('_')
                        if len(parts) > 1:
                            student_name = parts[0].replace('.', ' ')  # Name part
                            student_id = parts[-1]  # ID part
                        else:
                            student_name = f"Student {student_dir}"  # Default name
                            student_id = student_dir  # Assume folder name is the ID
                        
                        # Check if this student ID already exists in our data
                        if self.student_data is not None:
                            existing = self.student_data[self.student_data['ID'].astype(str) == str(student_id)]
                            if len(existing) > 0:
                                continue  # Skip if already in data
                        
                        # Add to list for later addition
                        students_to_add.append({
                            'ID': student_id,
                            'Name': student_name,
                            'Course': 'Unknown',  # Default values
                            'Year': str(datetime.datetime.now().year)
                        })
                        
                    except Exception as e:
                        logger.error(f"Error processing student folder {student_dir}: {e}")
            
            # If we have new students to add and CSV path is defined
            if students_to_add and self.students_csv_path:
                # Load existing CSV or create new one
                if self.student_data is None:
                    # Create new DataFrame
                    self.student_data = pd.DataFrame(students_to_add)
                    logger.info(f"Created new student data with {len(students_to_add)} students from backup")
                else:
                    # Append to existing data
                    new_data = pd.DataFrame(students_to_add)
                    self.student_data = pd.concat([self.student_data, new_data], ignore_index=True)
                    logger.info(f"Added {len(students_to_add)} students from backup to existing data")
                
                # Save to CSV
                self.student_data.to_csv(self.students_csv_path, index=False)
                
                # Update name mapping
                for _, row in self.student_data.iterrows():
                    id_value = row['ID']
                    try:
                        id_int = int(id_value) if str(id_value).isdigit() else id_value
                        self.student_names[id_int] = row['Name']
                    except Exception as e:
                        logger.error(f"Error converting ID {id_value} to int: {e}")
                
                return True
            
            return False
                
        except Exception as e:
            logger.error(f"Error updating student data from backup: {e}")
            return False
    
    def _load_recognizer_if_exists(self):
        """Load the pre-trained face recognizer model if it exists"""
        try:
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
            # Check if training directory exists
            if not os.path.exists(self.training_dir):
                logger.warning(f"Training images directory not found: {self.training_dir}")
                os.makedirs(self.training_dir, exist_ok=True)
                logger.info(f"Created training images directory: {self.training_dir}")
                
                # Try to import from backup if available
                if self._import_backup_training_images():
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