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

# Set up logging
logger = logging.getLogger(__name__)

class FaceDetector:
    """Face detection and recognition class"""
    
    def __init__(self, method="hybrid", threshold=0.6):
        """
        Initialize the face detector
        
        Args:
            method: Detection method to use (hybrid, haar_cascade, dlib, mtcnn)
            threshold: Confidence threshold for face recognition (0-1)
        """
        self.method = method
        self.threshold = threshold
        self.recognizer = None
        self.face_cascade = None
        self.student_data = {}
        
        # Initialize models
        self._init_models()
        
        # Load student data
        self._load_student_data()
        
        # Train recognizer if needed
        self._train_recognizer_if_needed()
        
        logger.info(f"Face detector initialized with method: {method}, threshold: {threshold}")
    
    def _init_models(self):
        """Initialize face detection models based on selected method"""
        # For all methods, we need the Haar cascade for basic detection
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        
        # Initialize recognizer
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        
        # Try to load a pre-trained model if it exists
        model_path = os.path.join("TrainingImageLabel", "Trainner.yml")
        if os.path.exists(model_path):
            try:
                self.recognizer.read(model_path)
                logger.info(f"Loaded face recognizer model from {model_path}")
            except Exception as e:
                logger.warning(f"Error loading recognizer: {e}")
                # Try alternative file format
                alt_model_path = os.path.join("TrainingImageLabel", "trainner.yml.npz")
                if os.path.exists(alt_model_path):
                    try:
                        self.recognizer.read(alt_model_path)
                        logger.info(f"Loaded face recognizer model from {alt_model_path}")
                    except Exception as e:
                        logger.error(f"Error loading alternative recognizer model: {e}")
        
        # Try to load additional models based on selected method
        if self.method in ["hybrid", "dlib"]:
            try:
                import dlib
                self.dlib_detector = dlib.get_frontal_face_detector()
                
                # Try to load the shape predictor and face recognition model if available
                predictor_path = os.path.join("models", "shape_predictor_68_face_landmarks.dat")
                recognition_path = os.path.join("models", "dlib_face_recognition_resnet_model_v1.dat")
                
                if os.path.exists(predictor_path) and os.path.exists(recognition_path):
                    self.shape_predictor = dlib.shape_predictor(predictor_path)
                    self.face_recognizer = dlib.face_recognition_model_v1(recognition_path)
                    logger.info("Loaded dlib face recognition models")
                else:
                    logger.info("Dlib models not found, will use only basic detection")
            except ImportError:
                logger.warning("Dlib module not available")
        
        if self.method in ["hybrid", "mtcnn"]:
            try:
                from mtcnn import MTCNN
                self.mtcnn_detector = MTCNN()
                logger.info("Loaded MTCNN detector")
            except ImportError:
                logger.warning("MTCNN module not available")
    
    def _load_student_data(self):
        """Load student data from CSV and images"""
        try:
            # Load from StudentDetails.csv if it exists
            students_file = os.path.join("StudentDetails", "StudentDetails.csv")
            if os.path.exists(students_file):
                import pandas as pd
                df = pd.read_csv(students_file)
                
                # Create a dictionary mapping ID to name
                for _, row in df.iterrows():
                    self.student_data[str(row["ID"])] = {
                        "name": row["Name"],
                        "course": row.get("Course", ""),
                        "year": row.get("Year", "")
                    }
                
                logger.info(f"Loaded {len(self.student_data)} students from {students_file}")
            else:
                logger.warning(f"Students file {students_file} not found")
            
            # Check training images
            training_dir = "TrainingImage"
            if os.path.exists(training_dir):
                count = 0
                for file in os.listdir(training_dir):
                    if file.endswith((".jpg", ".jpeg", ".png")):
                        # Extract ID and name from filename (format: ID.Name.1.jpg)
                        parts = file.split('.')
                        if len(parts) >= 3:
                            student_id = parts[0]
                            student_name = parts[1]
                            
                            # Add to student data if not already there
                            if student_id not in self.student_data:
                                self.student_data[student_id] = {
                                    "name": student_name,
                                    "course": "",
                                    "year": ""
                                }
                                count += 1
                
                logger.info(f"Added {count} additional students from training images")
        
        except Exception as e:
            logger.error(f"Error loading student data: {e}")
    
    def _train_recognizer_if_needed(self):
        """Train the recognizer if there are training images but no model"""
        model_path = os.path.join("TrainingImageLabel", "Trainner.yml")
        training_dir = "TrainingImage"
        
        # Check if we need to train (no model exists or training dir has newer files)
        should_train = False
        
        if not os.path.exists(model_path):
            should_train = True
            logger.info("No existing model found, will train recognizer")
        elif os.path.exists(training_dir):
            model_time = os.path.getmtime(model_path)
            
            # Check if any image in the directory is newer than the model
            for file in os.listdir(training_dir):
                if file.endswith((".jpg", ".jpeg", ".png")):
                    file_path = os.path.join(training_dir, file)
                    if os.path.getmtime(file_path) > model_time:
                        should_train = True
                        logger.info("Found newer training images, will retrain recognizer")
                        break
        
        if should_train and os.path.exists(training_dir):
            try:
                # Train the model
                logger.info("Training face recognizer...")
                faces = []
                ids = []
                
                # Load training images
                for file in os.listdir(training_dir):
                    if file.endswith((".jpg", ".jpeg", ".png")):
                        # Extract ID from filename
                        parts = file.split('.')
                        if len(parts) >= 3:
                            student_id = parts[0]
                            
                            # Load and process image
                            image_path = os.path.join(training_dir, file)
                            img = cv2.imread(image_path)
                            
                            if img is not None:
                                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                                face_rects = self.face_cascade.detectMultiScale(gray, 1.3, 5)
                                
                                for (x, y, w, h) in face_rects:
                                    # Extract face ROI
                                    roi = gray[y:y+h, x:x+w]
                                    faces.append(roi)
                                    ids.append(int(student_id))
                
                if faces and ids:
                    # Train the recognizer
                    self.recognizer.train(faces, np.array(ids))
                    
                    # Create directory if it doesn't exist
                    os.makedirs(os.path.dirname(model_path), exist_ok=True)
                    
                    # Save the model
                    self.recognizer.write(model_path)
                    logger.info(f"Trained and saved recognizer with {len(faces)} faces")
                else:
                    logger.warning("No faces detected in training images")
            
            except Exception as e:
                logger.error(f"Error training recognizer: {e}")
    
    def detect_and_recognize(self, frame):
        """
        Detect and recognize faces in a frame
        
        Args:
            frame: The input frame from camera or image
            
        Returns:
            tuple: (processed_frame, list of detected faces)
                  detected_faces is a list of tuples (id, name, confidence)
        """
        detected_faces = []
        
        try:
            # Create a copy of the frame for processing
            processed_frame = frame.copy()
            
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Detect faces using Haar cascade
            faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
            
            # Process each detected face
            for (x, y, w, h) in faces:
                # Draw rectangle around face
                cv2.rectangle(processed_frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
                
                # Extract face ROI
                face_roi = gray[y:y+h, x:x+w]
                
                # Try to recognize the face
                try:
                    id_num, confidence = self.recognizer.predict(face_roi)
                    
                    # Convert confidence to a more intuitive scale (0-100%, higher is better)
                    recognition_confidence = 100 - confidence
                    
                    # Check if confidence is above threshold
                    if recognition_confidence >= self.threshold * 100:
                        # Get student name from ID
                        student_id = str(id_num)
                        if student_id in self.student_data:
                            student_name = self.student_data[student_id]["name"]
                        else:
                            student_name = f"Unknown-{id_num}"
                        
                        # Add to detected faces list
                        detected_faces.append((student_id, student_name, recognition_confidence / 100))
                        
                        # Draw text on frame
                        text = f"{student_name} ({recognition_confidence:.1f}%)"
                        cv2.putText(processed_frame, text, (x, y-10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                    else:
                        # Low confidence
                        cv2.putText(processed_frame, "Unknown", (x, y-10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                
                except Exception as e:
                    logger.error(f"Error during face recognition: {e}")
                    cv2.putText(processed_frame, "Error", (x, y-10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            
            return processed_frame, detected_faces
        
        except Exception as e:
            logger.error(f"Error in detect_and_recognize: {e}")
            return frame, []
    
    def add_face(self, student_id, name, images):
        """
        Add new face images for a student
        
        Args:
            student_id: Student ID
            name: Student name
            images: List of face images
            
        Returns:
            bool: Success status
        """
        try:
            # Create directory if it doesn't exist
            training_dir = "TrainingImage"
            os.makedirs(training_dir, exist_ok=True)
            
            # Save images
            for i, image in enumerate(images):
                # Format: ID.Name.1.jpg, ID.Name.2.jpg, etc.
                image_path = os.path.join(training_dir, f"{student_id}.{name}.{i+1}.jpg")
                cv2.imwrite(image_path, image)
            
            # Add to student data
            self.student_data[student_id] = {
                "name": name,
                "course": "",
                "year": ""
            }
            
            # Retrain recognizer
            self._train_recognizer_if_needed()
            
            return True
        
        except Exception as e:
            logger.error(f"Error adding face: {e}")
            return False