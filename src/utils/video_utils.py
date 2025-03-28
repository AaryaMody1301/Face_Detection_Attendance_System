"""
Optimized video processing utilities for face recognition
"""
import cv2
import numpy as np
import threading
import time
import logging
import queue
from collections import deque

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VideoStream:
    """
    Optimized video stream class that efficiently captures frames
    from a camera or video file using threading and buffering
    """
    
    def __init__(self, src=0, width=640, height=480, fps=30, buffer_size=3):
        """
        Initialize the video stream
        
        Args:
            src: Camera index or video file path
            width: Desired frame width
            height: Desired frame height
            fps: Target frames per second
            buffer_size: Number of frames to buffer
        """
        self.src = src
        self.width = width
        self.height = height
        self.fps = fps
        self.buffer_size = max(1, buffer_size)
        
        # Create capture object (but don't start it yet)
        self.stream = None
        
        # Frame handling variables
        self.frame_buffer = deque(maxlen=self.buffer_size)
        self.current_frame = None
        self.frame_count = 0
        self.frame_time = 0
        
        # Thread control
        self.stopped = True
        self.thread = None
        self.lock = threading.Lock()
    
    def start(self):
        """
        Start the video stream thread
        
        Returns:
            bool: True if started successfully
        """
        if not self.stopped:
            logger.warning("Video stream is already running")
            return True
        
        # Try to initialize camera
        try:
            self.stream = cv2.VideoCapture(self.src)
            
            if not self.stream.isOpened():
                logger.error(f"Failed to open video source: {self.src}")
                return False
            
            # Set camera properties
            self.stream.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.stream.set(cv2.CAP_PROP_FPS, self.fps)
            
            # Read actual properties (may be different from requested)
            self.width = int(self.stream.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height = int(self.stream.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.fps = self.stream.get(cv2.CAP_PROP_FPS)
            
            logger.info(f"Started video stream: {self.width}x{self.height} @ {self.fps} FPS")
            
            # Reset variables
            self.frame_buffer.clear()
            self.current_frame = None
            self.frame_count = 0
            self.frame_time = time.time()
            self.stopped = False
            
            # Start capture thread
            self.thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.thread.start()
            
            # Wait for first frame
            timeout = time.time() + 5.0  # 5 second timeout
            while len(self.frame_buffer) == 0 and time.time() < timeout:
                time.sleep(0.1)
            
            return len(self.frame_buffer) > 0
            
        except Exception as e:
            logger.error(f"Error starting video stream: {e}")
            if self.stream and self.stream.isOpened():
                self.stream.release()
            return False
    
    def stop(self):
        """Stop the video stream thread"""
        self.stopped = True
        
        # Wait for thread to finish
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        
        # Release camera
        if self.stream and self.stream.isOpened():
            self.stream.release()
            self.stream = None
        
        logger.info("Video stream stopped")
    
    def read(self):
        """
        Read the most recent frame from the video stream
        
        Returns:
            numpy.ndarray or None: Frame if available, None otherwise
        """
        with self.lock:
            if not self.frame_buffer:
                return None
            
            # Get the most recent frame from the buffer
            self.current_frame = self.frame_buffer[-1].copy()
            return self.current_frame
    
    def _capture_loop(self):
        """Main capture loop running in a separate thread"""
        frame_interval = 1.0 / self.fps  # Time between frames
        
        while not self.stopped:
            loop_start = time.time()
            
            try:
                # Read frame from camera
                ret, frame = self.stream.read()
                
                if not ret or frame is None:
                    logger.warning("Failed to read frame from camera")
                    time.sleep(0.1)
                    continue
                
                # Update frame count and calculate FPS
                self.frame_count += 1
                elapsed = time.time() - self.frame_time
                if elapsed >= 1.0:
                    self.measured_fps = self.frame_count / elapsed
                    self.frame_count = 0
                    self.frame_time = time.time()
                
                # Add frame to buffer (with thread safety)
                with self.lock:
                    self.frame_buffer.append(frame)
                
                # Calculate time to wait for next frame
                processing_time = time.time() - loop_start
                wait_time = max(0, frame_interval - processing_time)
                
                if wait_time > 0:
                    time.sleep(wait_time)
                
            except Exception as e:
                logger.error(f"Error in video capture loop: {e}")
                time.sleep(0.1)
    
    def get_resolution(self):
        """Get the current resolution of the video stream"""
        return (self.width, self.height)


class FaceDetectionProcessor:
    """
    Optimized face detection and recognition processor with
    performance enhancements and memory optimizations
    """
    
    def __init__(self, detector, recognition_threshold=0.6, 
                 processing_scale=0.5, min_face_size=30, 
                 max_faces=10, stabilization_frames=3):
        """
        Initialize the face detection processor
        
        Args:
            detector: Face detector instance
            recognition_threshold: Confidence threshold for recognition
            processing_scale: Scale factor to apply to images before processing
            min_face_size: Minimum face size in pixels
            max_faces: Maximum number of faces to detect
            stabilization_frames: Number of frames for face tracking stabilization
        """
        self.detector = detector
        self.recognition_threshold = recognition_threshold
        self.processing_scale = max(0.1, min(1.0, processing_scale))
        self.min_face_size = min_face_size
        self.max_faces = max_faces
        self.stabilization_frames = stabilization_frames
        
        # Performance metrics
        self.process_times = deque(maxlen=30)  # Store last 30 processing times
        self.detection_times = deque(maxlen=30)
        self.recognition_times = deque(maxlen=30)
        
        # Face tracking to reduce jitter
        self.tracked_faces = []
        self.face_history = {}
        
        # Thread safety
        self.lock = threading.Lock()
    
    def process_frame(self, frame):
        """
        Process a frame for face detection and recognition
        
        Args:
            frame (numpy.ndarray): Frame to process
            
        Returns:
            tuple: (processed_frame, face_data)
        """
        if frame is None:
            return None, []
        
        start_time = time.time()
        face_data = []
        
        try:
            # Resize frame for faster processing if scale factor is less than 1.0
            if self.processing_scale < 1.0:
                h, w = frame.shape[:2]
                small_frame = cv2.resize(frame, (0, 0), fx=self.processing_scale, fy=self.processing_scale)
            else:
                small_frame = frame.copy()
            
            # Convert to RGB (face_recognition uses RGB)
            rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            
            # Detect faces
            detect_start = time.time()
            try:
                # Call without the extra parameters
                face_locations = self.detector.detect_faces(rgb_frame)
            except Exception as e:
                logger.error(f"Error processing frame: {e}")
                face_locations = []
            detect_time = time.time() - detect_start
            
            # Apply face tracking for stabilization
            with self.lock:
                face_locations = self._stabilize_face_locations(face_locations)
            
            # Recognize faces
            recog_start = time.time()
            face_encodings = self.detector.compute_face_encodings(rgb_frame, face_locations)
            
            recognized_faces = []
            for i, face_encoding in enumerate(face_encodings):
                name, confidence = self.detector.identify_face(face_encoding)
                
                # Skip faces with low confidence
                if confidence < self.recognition_threshold:
                    name = "Unknown"
                
                # Get face location and scale back to original size
                face_location = face_locations[i]
                if self.processing_scale < 1.0:
                    face_location = tuple(int(coord / self.processing_scale) for coord in face_location)
                
                face_data.append({
                    "name": name,
                    "confidence": confidence,
                    "location": face_location
                })
                
                # Draw face box and name
                self._draw_face_box(frame, face_location, name, confidence)
            
            recog_time = time.time() - recog_start
            
            # Update performance metrics
            process_time = time.time() - start_time
            self.process_times.append(process_time)
            self.detection_times.append(detect_time)
            self.recognition_times.append(recog_time)
            
            return frame, face_data
            
        except Exception as e:
            logger.error(f"Error processing frame: {e}")
            return frame, []
    
    def _stabilize_face_locations(self, face_locations):
        """
        Stabilize face locations to reduce jitter
        
        Uses a temporal filter to smooth face locations across frames
        """
        # Clean up old face entries
        current_time = time.time()
        for face_id in list(self.face_history.keys()):
            if current_time - self.face_history[face_id]["last_seen"] > 1.0:
                del self.face_history[face_id]
        
        # No faces detected
        if not face_locations:
            return []
        
        # Convert face locations to center points for tracking
        current_faces = []
        for i, loc in enumerate(face_locations):
            top, right, bottom, left = loc
            center_x = (left + right) // 2
            center_y = (top + bottom) // 2
            size = (right - left + bottom - top) // 2
            current_faces.append({
                "center": (center_x, center_y),
                "size": size,
                "location": loc,
                "matched": False
            })
        
        # If no tracked faces yet, initialize with current faces
        if not self.tracked_faces:
            for face in current_faces:
                face_id = id(face)
                self.face_history[face_id] = {
                    "locations": [face["location"]],
                    "last_seen": current_time
                }
            self.tracked_faces = current_faces
            return face_locations
        
        # Match current faces with tracked faces
        matched_locations = []
        
        for current in current_faces:
            cx, cy = current["center"]
            best_distance = float('inf')
            best_match = None
            
            # Find the closest tracked face
            for tracked in self.tracked_faces:
                if tracked["matched"]:
                    continue
                    
                tx, ty = tracked["center"]
                distance = ((cx - tx) ** 2 + (cy - ty) ** 2) ** 0.5
                
                # Use a distance threshold based on face size
                threshold = max(tracked["size"], current["size"]) * 0.5
                
                if distance < threshold and distance < best_distance:
                    best_distance = distance
                    best_match = tracked
            
            if best_match:
                best_match["matched"] = True
                face_id = id(best_match)
                
                # Update face history
                if face_id not in self.face_history:
                    self.face_history[face_id] = {
                        "locations": [current["location"]],
                        "last_seen": current_time
                    }
                else:
                    history = self.face_history[face_id]
                    history["last_seen"] = current_time
                    history["locations"].append(current["location"])
                    
                    # Limit history size
                    if len(history["locations"]) > self.stabilization_frames:
                        history["locations"].pop(0)
                    
                    # Calculate average location
                    avg_location = self._average_locations(history["locations"])
                    matched_locations.append(avg_location)
            else:
                # New face, no stabilization yet
                face_id = id(current)
                self.face_history[face_id] = {
                    "locations": [current["location"]],
                    "last_seen": current_time
                }
                matched_locations.append(current["location"])
        
        # Update tracked faces
        self.tracked_faces = [face for face in current_faces]
        
        return matched_locations if matched_locations else face_locations
    
    def _average_locations(self, locations):
        """Calculate average face location from a list of locations"""
        if not locations:
            return (0, 0, 0, 0)
        
        avg_top = sum(loc[0] for loc in locations) // len(locations)
        avg_right = sum(loc[1] for loc in locations) // len(locations)
        avg_bottom = sum(loc[2] for loc in locations) // len(locations)
        avg_left = sum(loc[3] for loc in locations) // len(locations)
        
        return (avg_top, avg_right, avg_bottom, avg_left)
    
    def _draw_face_box(self, frame, face_location, name, confidence):
        """
        Draw a face box and label on the frame
        
        Args:
            frame: The frame to draw on
            face_location: Face location as (top, right, bottom, left)
            name: Name of the recognized person
            confidence: Recognition confidence
        """
        # Extract coordinates
        top, right, bottom, left = face_location
        
        # Choose color based on name
        if name == "Unknown":
            # Red for unknown faces
            color = (0, 0, 255)
        else:
            # Green for recognized faces, with intensity based on confidence
            intensity = int(255 * min(confidence, 1.0))
            color = (0, intensity, 0)
        
        # Draw face box
        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
        
        # Draw label background
        label_size = cv2.getTextSize(name, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
        cv2.rectangle(frame, (left, bottom - label_size[1] - 10), (right, bottom), color, cv2.FILLED)
        
        # Draw name
        cv2.putText(frame, name, (left + 6, bottom - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Draw confidence if recognized
        if name != "Unknown":
            conf_text = f"{confidence:.2f}"
            cv2.putText(frame, conf_text, (right - 40, top + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    def get_stats(self):
        """Get performance statistics"""
        stats = {
            "avg_process_time": sum(self.process_times) / max(1, len(self.process_times)),
            "avg_detection_time": sum(self.detection_times) / max(1, len(self.detection_times)),
            "avg_recognition_time": sum(self.recognition_times) / max(1, len(self.recognition_times)),
            "processing_scale": self.processing_scale,
            "max_faces": self.max_faces
        }
        return stats