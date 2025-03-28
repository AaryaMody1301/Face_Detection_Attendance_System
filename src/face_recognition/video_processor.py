"""
Optimized video processing for face detection and recognition
"""
import os
import cv2
import time
import numpy as np
import logging
import threading
from collections import deque
from typing import Dict, List, Tuple, Optional, Union, Any

# Import local modules
from src.utils.performance_monitor import get_performance_monitor
from src.utils.app_config import AppConfig

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VideoProcessor:
    """
    Optimized video processing for face detection and recognition
    """
    
    def __init__(self, config=None):
        """
        Initialize the video processor
        
        Args:
            config (AppConfig, optional): Application configuration
        """
        self.config = config or AppConfig()
        self.perf_monitor = get_performance_monitor()
        
        # Initialize face detection parameters
        self.confidence_threshold = self.config.get("face_detection", "confidence_threshold", default=0.6)
        self.min_face_size = self.config.get("face_detection", "min_face_size", default=30)
        self.max_faces = self.config.get("face_detection", "max_faces", default=10)
        self.processing_scale = self.config.get("face_detection", "processing_scale", default=0.5)
        self.stabilization = self.config.get("face_detection", "stabilization", default=True)
        self.stabilization_frames = self.config.get("face_detection", "stabilization_frames", default=3)
        
        # Initialize camera parameters
        self.camera_device_id = self.config.get("camera", "device_id", default=0)
        self.camera_resolution = self.config.get("camera", "resolution", default=[640, 480])
        self.camera_fps = self.config.get("camera", "fps", default=30)
        
        # Initialize video capture
        self.cap = None
        self.frame_width = self.camera_resolution[0]
        self.frame_height = self.camera_resolution[1]
        
        # Initialize face detection
        self.face_cascade = None
        self.face_detector_model = None
        self.initialize_face_detector()
        
        # Initialize face recognition
        self.recognizer = None
        self.initialize_face_recognizer()
        
        # Tracking and stabilization
        self.face_locations_history = deque(maxlen=self.stabilization_frames)
        self.face_encodings_history = deque(maxlen=self.stabilization_frames)
        self.face_names_history = deque(maxlen=self.stabilization_frames)
        
        # Performance metrics
        self.frame_count = 0
        self.fps = 0
        self.last_fps_update = time.time()
        self.last_frame_time = 0
        
        # Thread safety
        self.lock = threading.RLock()
        
        # Debug mode
        self.debug_mode = self.config.get("advanced", "debug_mode", default=False)
    
    def initialize_face_detector(self):
        """Initialize face detection models"""
        try:
            # Try to load Haar cascade classifier
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            if not os.path.exists(cascade_path):
                cascade_path = 'haarcascade_frontalface_default.xml'
            
            self.face_cascade = cv2.CascadeClassifier(cascade_path)
            
            # Check if cascade classifier loaded successfully
            if self.face_cascade.empty():
                logger.warning("Failed to load Haar cascade classifier, falling back to default")
                self.face_cascade = None
            else:
                logger.info(f"Loaded Haar cascade classifier from {cascade_path}")
            
            # Try to load DNN-based model if available
            try:
                # Try to load DNN face detector model
                prototxt_path = 'models/deploy.prototxt'
                model_path = 'models/res10_300x300_ssd_iter_140000.caffemodel'
                
                if os.path.exists(prototxt_path) and os.path.exists(model_path):
                    self.face_detector_model = cv2.dnn.readNetFromCaffe(prototxt_path, model_path)
                    logger.info("Loaded DNN face detector model")
                else:
                    logger.warning("DNN face detector model files not found")
            except Exception as e:
                logger.error(f"Error loading DNN face detector: {e}")
                self.face_detector_model = None
            
        except Exception as e:
            logger.error(f"Error initializing face detector: {e}")
            self.face_cascade = None
            self.face_detector_model = None
    
    def initialize_face_recognizer(self):
        """Initialize face recognition model"""
        try:
            # Try to load LBPH face recognizer
            self.recognizer = cv2.face.LBPHFaceRecognizer_create()
            
            # Try to load trained recognizer
            try:
                recognizer_path = 'TrainingImageLabel/Trainner.yml'
                self.recognizer.read(recognizer_path)
                logger.info(f"Loaded face recognizer from {recognizer_path}")
            except Exception as e:
                logger.warning(f"Could not load face recognizer: {e}")
        except Exception as e:
            logger.error(f"Error initializing face recognizer: {e}")
            self.recognizer = None
    
    def start_camera(self):
        """
        Start camera capture
        
        Returns:
            bool: True if camera started successfully
        """
        try:
            # Release existing capture if any
            if self.cap is not None:
                self.cap.release()
            
            # Initialize video capture
            self.cap = cv2.VideoCapture(self.camera_device_id)
            
            # Set camera properties
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.camera_resolution[0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.camera_resolution[1])
            self.cap.set(cv2.CAP_PROP_FPS, self.camera_fps)
            
            # Get actual frame dimensions
            self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            logger.info(f"Camera started with resolution {self.frame_width}x{self.frame_height}")
            return True
            
        except Exception as e:
            logger.error(f"Error starting camera: {e}")
            return False
    
    def stop_camera(self):
        """Stop camera capture"""
        if self.cap is not None:
            self.cap.release()
            self.cap = None
            logger.info("Camera stopped")
    
    def read_frame(self):
        """
        Read a frame from the camera
        
        Returns:
            tuple: (success, frame)
        """
        if self.cap is None:
            return False, None
        
        try:
            # Read frame
            ret, frame = self.cap.read()
            
            # Update performance metrics
            current_time = time.time()
            if current_time - self.last_fps_update >= 1.0:
                self.fps = self.frame_count / (current_time - self.last_fps_update)
                self.perf_monitor.update_frame_rate(self.fps)
                self.last_fps_update = current_time
                self.frame_count = 0
            else:
                self.frame_count += 1
            
            self.last_frame_time = current_time
            
            return ret, frame
            
        except Exception as e:
            logger.error(f"Error reading frame: {e}")
            return False, None
    
    def detect_faces(self, frame):
        """
        Detect faces in a frame
        
        Args:
            frame (numpy.ndarray): Input frame
            
        Returns:
            list: List of face locations (x, y, w, h)
        """
        # Input validation
        if frame is None or frame.size == 0:
            logger.warning("Empty frame provided to face detector")
            return []
        
        # Start timing
        start_time = time.time()
        
        # Process frame at reduced resolution for better performance
        scale = self.processing_scale
        if scale != 1.0:
            try:
                small_frame = cv2.resize(frame, (0, 0), fx=scale, fy=scale)
            except Exception as e:
                logger.error(f"Error resizing frame: {e}")
                small_frame = frame.copy()
                scale = 1.0  # Reset scale since resize failed
        else:
            small_frame = frame.copy()
        
        # Convert to grayscale for Haar cascade
        try:
            gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
        except Exception as e:
            logger.error(f"Error converting to grayscale: {e}")
            return []
        
        # Face detection using DNN if available (more accurate but slower)
        face_locations = []
        dnn_detection_success = False
        
        if self.face_detector_model is not None:
            try:
                # Prepare blob from image
                blob = cv2.dnn.blobFromImage(small_frame, 1.0, (300, 300), [104, 117, 123], False, False)
                self.face_detector_model.setInput(blob)
                detections = self.face_detector_model.forward()
                
                h, w = small_frame.shape[:2]
                
                # Process detections
                for i in range(detections.shape[2]):
                    confidence = detections[0, 0, i, 2]
                    
                    # Filter by confidence threshold
                    if confidence > self.confidence_threshold:
                        # Get bounding box coordinates
                        box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                        x1, y1, x2, y2 = box.astype("int")
                        
                        # Ensure coordinates are within frame bounds
                        x1 = max(0, x1)
                        y1 = max(0, y1)
                        x2 = min(w, x2)
                        y2 = min(h, y2)
                        
                        # Calculate width and height
                        w_face = x2 - x1
                        h_face = y2 - y1
                        
                        # Filter by minimum face size
                        if w_face >= self.min_face_size*scale and h_face >= self.min_face_size*scale:
                            face_locations.append((x1, y1, w_face, h_face))
                
                # Limit number of faces
                if self.max_faces > 0 and len(face_locations) > self.max_faces:
                    # Sort by area (largest first)
                    face_locations.sort(key=lambda loc: loc[2] * loc[3], reverse=True)
                    face_locations = face_locations[:self.max_faces]
                
                dnn_detection_success = len(face_locations) > 0
            
            except Exception as e:
                logger.error(f"Error in DNN face detection: {e}")
                dnn_detection_success = False
        
        # If DNN detection failed or not available, fallback to Haar cascade
        if not dnn_detection_success and self.face_cascade is not None:
            try:
                # Try different scaleFactor values if detection fails initially
                scale_factors = [1.1, 1.2, 1.3]
                min_neighbors_options = [5, 4, 3]
                
                for sf in scale_factors:
                    for mn in min_neighbors_options:
                        # Skip trying less accurate parameters if we already got results
                        if face_locations:
                            break
                            
                        faces = self.face_cascade.detectMultiScale(
                            gray,
                            scaleFactor=sf,
                            minNeighbors=mn,
                            minSize=(int(self.min_face_size * scale), int(self.min_face_size * scale)),
                            flags=cv2.CASCADE_SCALE_IMAGE
                        )
                        
                        if len(faces) > 0:
                            face_locations = [(x, y, w, h) for (x, y, w, h) in faces]
                            logger.debug(f"Haar cascade detected {len(faces)} faces with scaleFactor={sf}, minNeighbors={mn}")
                            break
                
                # Limit number of faces
                if self.max_faces > 0 and len(face_locations) > self.max_faces:
                    # Sort by area (largest first)
                    face_locations.sort(key=lambda loc: loc[2] * loc[3], reverse=True)
                    face_locations = face_locations[:self.max_faces]
                    
            except Exception as e:
                logger.error(f"Error in Haar cascade face detection: {e}")
        
        # Scale back to original image coordinates if needed
        if scale != 1.0 and face_locations:
            try:
                face_locations = [(int(x / scale), int(y / scale), 
                                  int(w / scale), int(h / scale)) 
                                for (x, y, w, h) in face_locations]
            except Exception as e:
                logger.error(f"Error scaling face locations: {e}")
        
        # Apply stabilization if enabled
        if face_locations and self.stabilization and len(self.face_locations_history) > 0:
            try:
                face_locations = self._stabilize_face_locations(face_locations)
            except Exception as e:
                logger.error(f"Error during face location stabilization: {e}")
        
        # Add to history
        self.face_locations_history.append(face_locations)
        
        # Update performance metrics
        detection_time = time.time() - start_time
        self.perf_monitor.update_face_detection_time(detection_time)
        
        # Debug output
        if self.debug_mode:
            logger.debug(f"Detected {len(face_locations)} faces in {detection_time:.3f}s")
        
        return face_locations
    
    def recognize_faces(self, frame, face_locations):
        """
        Recognize faces in a frame
        
        Args:
            frame (numpy.ndarray): Input frame
            face_locations (list): List of face locations (x, y, w, h)
            
        Returns:
            list: List of (face_location, name, confidence) tuples
        """
        if frame is None or not face_locations or self.recognizer is None:
            return []
        
        # Start timing
        start_time = time.time()
        
        # Convert to grayscale for recognition
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Recognize each face
        results = []
        for (x, y, w, h) in face_locations:
            try:
                # Extract face ROI
                face_roi = gray[y:y+h, x:x+w]
                
                # Resize to a standard size for recognition
                face_roi = cv2.resize(face_roi, (100, 100))
                
                # Predict
                id_, confidence = self.recognizer.predict(face_roi)
                
                # Convert confidence (lower is better in LBPH) to a percentage (higher is better)
                confidence = 100 - min(100, confidence)
                
                # Get name from ID
                name = self._get_name_from_id(id_)
                
                results.append(((x, y, w, h), name, confidence))
                
            except Exception as e:
                logger.error(f"Error recognizing face: {e}")
                results.append(((x, y, w, h), "Unknown", 0.0))
        
        # Add to history
        self.face_names_history.append([name for _, name, _ in results])
        
        # Debug output
        if self.debug_mode:
            recognition_time = time.time() - start_time
            logger.debug(f"Recognized {len(results)} faces in {recognition_time:.3f}s")
        
        return results
    
    def process_frame(self, frame, detect=True, recognize=True):
        """
        Process a frame with face detection and recognition
        
        Args:
            frame (numpy.ndarray): Input frame
            detect (bool): Whether to perform face detection
            recognize (bool): Whether to perform face recognition
            
        Returns:
            tuple: (processed_frame, face_results)
        """
        with self.lock:
            if frame is None:
                return None, []
            
            # Create a copy of the frame
            processed_frame = frame.copy()
            
            face_results = []
            
            # Detect faces
            if detect:
                face_locations = self.detect_faces(frame)
                
                # Recognize faces
                if recognize and self.recognizer is not None:
                    face_results = self.recognize_faces(frame, face_locations)
                else:
                    face_results = [((x, y, w, h), "Unknown", 0.0) for (x, y, w, h) in face_locations]
                
                # Draw face boxes and labels
                for (x, y, w, h), name, confidence in face_results:
                    # Draw rectangle around the face
                    cv2.rectangle(processed_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    
                    # Draw name label
                    label = f"{name} ({confidence:.1f}%)"
                    cv2.putText(processed_frame, label, (x, y-10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            return processed_frame, face_results
    
    def _stabilize_face_locations(self, current_locations):
        """
        Stabilize face locations across frames
        
        Args:
            current_locations (list): Current face locations
            
        Returns:
            list: Stabilized face locations
        """
        if not self.face_locations_history:
            return current_locations
        
        # Get previous locations
        prev_locations = self.face_locations_history[-1]
        
        # If no faces in current frame, return previous locations
        if not current_locations:
            return prev_locations
        
        # If no faces in previous frame, return current locations
        if not prev_locations:
            return current_locations
        
        # Match faces between frames
        stabilized_locations = []
        for curr_x, curr_y, curr_w, curr_h in current_locations:
            curr_center = (curr_x + curr_w // 2, curr_y + curr_h // 2)
            
            # Find closest face in previous frame
            best_match = None
            best_distance = float('inf')
            
            for prev_x, prev_y, prev_w, prev_h in prev_locations:
                prev_center = (prev_x + prev_w // 2, prev_y + prev_h // 2)
                
                # Calculate distance between centers
                distance = ((curr_center[0] - prev_center[0]) ** 2 + 
                           (curr_center[1] - prev_center[1]) ** 2) ** 0.5
                
                if distance < best_distance:
                    best_distance = distance
                    best_match = (prev_x, prev_y, prev_w, prev_h)
            
            # If a close match was found, blend the locations
            if best_match and best_distance < max(curr_w, curr_h) // 2:
                # Weighted average (70% current, 30% previous)
                stabilized_x = int(0.7 * curr_x + 0.3 * best_match[0])
                stabilized_y = int(0.7 * curr_y + 0.3 * best_match[1])
                stabilized_w = int(0.7 * curr_w + 0.3 * best_match[2])
                stabilized_h = int(0.7 * curr_h + 0.3 * best_match[3])
                
                stabilized_locations.append((stabilized_x, stabilized_y, stabilized_w, stabilized_h))
            else:
                # No close match, use current location
                stabilized_locations.append((curr_x, curr_y, curr_w, curr_h))
        
        return stabilized_locations
    
    def _get_name_from_id(self, id_):
        """
        Get name from person ID
        
        Args:
            id_ (int): Person ID
            
        Returns:
            str: Person name or "Unknown"
        """
        # TODO: Implement name lookup from database or CSV file
        # This is a placeholder implementation
        try:
            # Try to load names from StudentDetails.csv
            import csv
            import pandas as pd
            
            try:
                # Try pandas first
                df = pd.read_csv("StudentDetails/StudentDetails.csv")
                row = df[df['Id'] == id_]
                if not row.empty:
                    return row.iloc[0]['Name']
            except Exception:
                # Fall back to csv module
                with open("StudentDetails/StudentDetails.csv", 'r') as csvFile:
                    reader = csv.reader(csvFile)
                    for row in reader:
                        if len(row) >= 2 and row[0] == str(id_):
                            return row[1]
        except Exception as e:
            logger.error(f"Error getting name from ID: {e}")
        
        return f"Person_{id_}"
    
    def get_performance_stats(self):
        """
        Get performance statistics
        
        Returns:
            dict: Performance statistics
        """
        return {
            "fps": self.fps,
            "frame_time": 1000.0 / max(1.0, self.fps),  # ms per frame
            "resolution": (self.frame_width, self.frame_height),
            "face_detection_time": self.perf_monitor.get_current_metrics()["face_detection_time"] * 1000.0  # ms
        }
    
    def set_camera_parameters(self, device_id=None, resolution=None, fps=None):
        """
        Set camera parameters
        
        Args:
            device_id (int, optional): Camera device ID
            resolution (tuple, optional): Camera resolution (width, height)
            fps (int, optional): Camera FPS
            
        Returns:
            bool: True if parameters were updated
        """
        with self.lock:
            changed = False
            
            if device_id is not None and device_id != self.camera_device_id:
                self.camera_device_id = device_id
                changed = True
            
            if resolution is not None and resolution != self.camera_resolution:
                self.camera_resolution = resolution
                changed = True
            
            if fps is not None and fps != self.camera_fps:
                self.camera_fps = fps
                changed = True
            
            if changed and self.cap is not None:
                # Restart camera with new parameters
                self.stop_camera()
                self.start_camera()
            
            return changed
    
    def set_detection_parameters(self, confidence_threshold=None, min_face_size=None, 
                                max_faces=None, processing_scale=None, 
                                stabilization=None, stabilization_frames=None):
        """
        Set face detection parameters
        
        Args:
            confidence_threshold (float, optional): Confidence threshold
            min_face_size (int, optional): Minimum face size
            max_faces (int, optional): Maximum number of faces to detect
            processing_scale (float, optional): Processing scale for improved performance
            stabilization (bool, optional): Whether to enable face stabilization
            stabilization_frames (int, optional): Number of frames for face stabilization
            
        Returns:
            bool: True if parameters were updated
        """
        with self.lock:
            changed = False
            
            if confidence_threshold is not None and confidence_threshold != self.confidence_threshold:
                self.confidence_threshold = confidence_threshold
                changed = True
            
            if min_face_size is not None and min_face_size != self.min_face_size:
                self.min_face_size = min_face_size
                changed = True
            
            if max_faces is not None and max_faces != self.max_faces:
                self.max_faces = max_faces
                changed = True
            
            if processing_scale is not None and processing_scale != self.processing_scale:
                self.processing_scale = processing_scale
                changed = True
            
            if stabilization is not None and stabilization != self.stabilization:
                self.stabilization = stabilization
                changed = True
            
            if stabilization_frames is not None and stabilization_frames != self.stabilization_frames:
                self.stabilization_frames = stabilization_frames
                self.face_locations_history = deque(maxlen=self.stabilization_frames)
                self.face_names_history = deque(maxlen=self.stabilization_frames)
                changed = True
            
            return changed
    
    def save_frame(self, frame, path, name=None, timestamp=True):
        """
        Save a frame to disk
        
        Args:
            frame (numpy.ndarray): Frame to save
            path (str): Directory path
            name (str, optional): File name (without extension)
            timestamp (bool): Whether to add timestamp to filename
            
        Returns:
            str: File path if saved successfully, None otherwise
        """
        try:
            # Create directory if it doesn't exist
            if not os.path.exists(path):
                os.makedirs(path)
            
            # Generate filename
            if name is None:
                name = "frame"
            
            if timestamp:
                timestamp_str = time.strftime("%Y%m%d_%H%M%S")
                filename = f"{name}_{timestamp_str}.jpg"
            else:
                filename = f"{name}.jpg"
            
            file_path = os.path.join(path, filename)
            
            # Save image
            cv2.imwrite(file_path, frame)
            logger.info(f"Saved frame to {file_path}")
            
            return file_path
            
        except Exception as e:
            logger.error(f"Error saving frame: {e}")
            return None
    
    def release(self):
        """Release resources"""
        self.stop_camera()
        logger.info("Video processor released")