"""
Video processor for face detection and recognition

This module provides a video processing class that works with both UI variants.
"""

import cv2
import numpy as np
import threading
import logging
import time
import queue
from datetime import datetime
import os
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

class VideoProcessor:
    """
    Video processor class for face detection and attendance.
    
    Handles video capture, face detection, recognition, and display in a separate thread.
    """
    
    def __init__(self, face_detector, db_handler, video_device=0, buffer_size=10):
        """
        Initialize the video processor.
        
        Args:
            face_detector: Face detector instance
            db_handler: Database handler instance 
            video_device (int or str): Video device index or path to video file
            buffer_size (int): Size of the frame buffer
        """
        self.face_detector = face_detector
        self.db_handler = db_handler
        self.video_device = video_device
        
        # Video capture
        self.cap = None
        self.is_running = False
        self.processing_thread = None
        
        # Frame processing
        self.frame_queue = queue.Queue(maxsize=buffer_size)
        self.result_frame = None
        self.result_frame_lock = threading.Lock()
        
        # Status
        self.status = "Idle"
        self.fps = 0
        self.last_fps_update = time.time()
        self.frame_count = 0
        
        # Recognition settings
        self.min_face_size = 30
        self.confidence_threshold = 0.6
        self.recognition_interval = 1.0  # seconds
        self.last_recognition_time = 0
        
        # Attendance tracking
        self.current_subject = None
        self.marked_students = set()  # Track students already marked present
        self.attendance_mode = False
        
        # Training settings
        self.training_mode = False
        self.training_name = None
        self.training_id = None
        self.image_count = 0
        self.max_training_images = 50
        self.training_interval = 0.5  # seconds
        self.last_training_capture = 0
    
    def start(self):
        """Start video processing"""
        if self.is_running:
            logger.warning("Video processor is already running")
            return False
            
        try:
            # Open video capture
            self.cap = cv2.VideoCapture(self.video_device)
            
            # Check if opened successfully
            if not self.cap.isOpened():
                logger.error(f"Failed to open video device {self.video_device}")
                return False
                
            # Clear queue
            while not self.frame_queue.empty():
                self.frame_queue.get()
                
            # Reset status
            self.is_running = True
            self.status = "Running"
            self.frame_count = 0
            self.fps = 0
            self.last_fps_update = time.time()
            self.marked_students = set()
            
            # Start processing thread
            self.processing_thread = threading.Thread(target=self._process_frames, daemon=True)
            self.processing_thread.start()
            
            logger.info(f"Started video processing on device {self.video_device}")
            return True
            
        except Exception as e:
            logger.error(f"Error starting video processor: {e}")
            self.is_running = False
            
            # Clean up if needed
            if self.cap:
                self.cap.release()
                self.cap = None
                
            return False
    
    def stop(self):
        """Stop video processing"""
        if not self.is_running:
            return
            
        # Signal thread to stop
        self.is_running = False
        
        # Wait for thread to finish
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=1.0)
            
        # Release video capture
        if self.cap:
            self.cap.release()
            self.cap = None
            
        # Update status
        self.status = "Stopped"
        
        logger.info("Stopped video processing")
    
    def _process_frames(self):
        """Process video frames (runs in a separate thread)"""
        while self.is_running:
            try:
                # Capture frame
                ret, frame = self.cap.read()
                
                if not ret or frame is None:
                    logger.warning("Failed to capture frame")
                    self.status = "No Frame"
                    time.sleep(0.1)
                    continue
                
                # Update FPS calculation
                current_time = time.time()
                self.frame_count += 1
                elapsed = current_time - self.last_fps_update
                
                if elapsed >= 1.0:
                    self.fps = self.frame_count / elapsed
                    self.frame_count = 0
                    self.last_fps_update = current_time
                
                # Process frame based on mode
                if self.training_mode:
                    self._process_training_frame(frame)
                elif self.attendance_mode:
                    self._process_attendance_frame(frame)
                else:
                    self._process_display_frame(frame)
                    
            except Exception as e:
                logger.error(f"Error in frame processing: {e}")
                self.status = f"Error: {str(e)[:30]}..."
                time.sleep(0.1)
    
    def _process_display_frame(self, frame):
        """Process frame for display only (detection without recognition)"""
        # Create a copy for drawing
        display_frame = frame.copy()
        
        try:
            # Detect faces
            face_locations = self.face_detector.detect_faces(frame)
            
            # Draw rectangles around faces
            for face_location in face_locations:
                top, right, bottom, left = face_location
                
                # Draw rectangle
                cv2.rectangle(display_frame, (left, top), (right, bottom), (0, 255, 0), 2)
                
            # Add status text
            self._add_status_overlay(display_frame)
            
            # Update result frame
            with self.result_frame_lock:
                self.result_frame = display_frame
                
        except Exception as e:
            logger.error(f"Error in display processing: {e}")
            self.status = f"Error: {str(e)[:30]}..."
            
            # Still update the frame even on error
            with self.result_frame_lock:
                self.result_frame = display_frame
    
    def _process_attendance_frame(self, frame):
        """Process frame for attendance tracking"""
        # Create a copy for drawing
        display_frame = frame.copy()
        
        try:
            # Only do recognition processing at certain intervals to avoid excessive CPU usage
            current_time = time.time()
            
            # Detect faces in every frame
            face_locations = self.face_detector.detect_faces(frame)
            
            # Draw rectangles around faces
            for face_location in face_locations:
                top, right, bottom, left = face_location
                
                # Draw rectangle (yellow by default before recognition)
                cv2.rectangle(display_frame, (left, top), (right, bottom), (0, 255, 255), 2)
            
            # Recognize faces at intervals
            if current_time - self.last_recognition_time >= self.recognition_interval and face_locations:
                self.last_recognition_time = current_time
                
                # Recognize faces
                recognized_faces = self.face_detector.recognize_faces(
                    frame, confidence_threshold=self.confidence_threshold
                )
                
                # Process each recognized face
                for face_location, name, student_id, confidence in recognized_faces:
                    top, right, bottom, left = face_location
                    
                    # If recognized with sufficient confidence
                    color = (0, 255, 0)  # Green for recognized
                    label = f"{name} ({confidence:.2f})"
                    
                    if name == "Unknown":
                        color = (0, 0, 255)  # Red for unknown
                        label = "Unknown"
                    
                    # Draw rectangle with recognition result
                    cv2.rectangle(display_frame, (left, top), (right, bottom), color, 2)
                    
                    # Draw label background
                    cv2.rectangle(display_frame, (left, top-30), (right, top), color, -1)
                    
                    # Draw label text
                    cv2.putText(
                        display_frame, label, (left + 6, top - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA
                    )
                    
                    # Mark attendance if this is a known face and not already marked
                    if (
                        name != "Unknown" and 
                        student_id and 
                        self.current_subject and 
                        f"{student_id}_{self.current_subject}" not in self.marked_students
                    ):
                        try:
                            # Mark attendance in database
                            self.db_handler.mark_attendance(
                                student_id,
                                name,
                                self.current_subject
                            )
                            
                            # Add to marked students set
                            self.marked_students.add(f"{student_id}_{self.current_subject}")
                            
                            logger.info(f"Marked attendance for {name} ({student_id}) in {self.current_subject}")
                            
                            # Update status
                            self.status = f"Marked: {name}"
                        except Exception as e:
                            logger.error(f"Error marking attendance: {e}")
            
            # Add status text
            self._add_status_overlay(display_frame)
            
            # Update result frame
            with self.result_frame_lock:
                self.result_frame = display_frame
                
        except Exception as e:
            logger.error(f"Error in attendance processing: {e}")
            self.status = f"Error: {str(e)[:30]}..."
            
            # Still update the frame even on error
            with self.result_frame_lock:
                self.result_frame = display_frame
    
    def _process_training_frame(self, frame):
        """Process frame for training image capture"""
        # Create a copy for drawing
        display_frame = frame.copy()
        
        try:
            # Detect faces
            face_locations = self.face_detector.detect_faces(frame)
            
            # Check if we should capture a training image
            current_time = time.time()
            should_capture = (
                current_time - self.last_training_capture >= self.training_interval and
                self.image_count < self.max_training_images and
                face_locations and
                self.training_name and
                self.training_id
            )
            
            # Process each detected face
            for face_location in face_locations:
                top, right, bottom, left = face_location
                
                # Draw rectangle
                color = (255, 255, 0)  # Yellow for training mode
                
                if should_capture:
                    color = (0, 255, 0)  # Green when capturing
                    
                cv2.rectangle(display_frame, (left, top), (right, bottom), color, 2)
                
                # Save training image if needed
                if should_capture:
                    try:
                        self._save_training_image(frame, face_location)
                        self.last_training_capture = current_time
                        break  # Only save one face per frame
                    except Exception as e:
                        logger.error(f"Error saving training image: {e}")
            
            # Add status text
            progress = f"Progress: {self.image_count}/{self.max_training_images}"
            cv2.putText(
                display_frame, progress, (10, 70),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2, cv2.LINE_AA
            )
            
            self._add_status_overlay(display_frame)
            
            # Update result frame
            with self.result_frame_lock:
                self.result_frame = display_frame
                
        except Exception as e:
            logger.error(f"Error in training processing: {e}")
            self.status = f"Error: {str(e)[:30]}..."
            
            # Still update the frame even on error
            with self.result_frame_lock:
                self.result_frame = display_frame
    
    def _save_training_image(self, frame, face_location):
        """Save a training image with the face"""
        try:
            # Extract face with some margin
            top, right, bottom, left = face_location
            
            # Add margins (20% on each side)
            height = bottom - top
            width = right - left
            
            top = max(0, top - int(height * 0.2))
            bottom = min(frame.shape[0], bottom + int(height * 0.2))
            left = max(0, left - int(width * 0.2))
            right = min(frame.shape[1], right + int(width * 0.2))
            
            # Extract face region
            face_image = frame[top:bottom, left:right]
            
            # Create directory if it doesn't exist
            os.makedirs("TrainingImage", exist_ok=True)
            
            # Generate filename: Name.ID.Number.jpg
            timestamp = int(time.time() * 1000)
            filename = f"{self.training_name}.{self.training_id}.{self.image_count+1}_{timestamp}.jpg"
            file_path = os.path.join("TrainingImage", filename)
            
            # Save image
            cv2.imwrite(file_path, face_image)
            
            # Update count
            self.image_count += 1
            
            # Update status
            self.status = f"Saved: {self.image_count}/{self.max_training_images}"
            
            logger.info(f"Saved training image {self.image_count}: {file_path}")
            
            # Check if we've reached the maximum
            if self.image_count >= self.max_training_images:
                self.status = "Completed Training"
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error saving training image: {e}")
            return False
    
    def _add_status_overlay(self, frame):
        """Add status overlay to frame"""
        # Add FPS
        cv2.putText(
            frame, f"FPS: {self.fps:.1f}", (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2, cv2.LINE_AA
        )
        
        # Add mode status
        mode = "Training" if self.training_mode else "Attendance" if self.attendance_mode else "Display"
        cv2.putText(
            frame, f"Mode: {mode}", (frame.shape[1] - 200, 30),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2, cv2.LINE_AA
        )
        
        # Add status text
        cv2.putText(
            frame, f"Status: {self.status}", (10, frame.shape[0] - 10),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2, cv2.LINE_AA
        )
    
    def get_frame(self):
        """Get the latest processed frame"""
        with self.result_frame_lock:
            if self.result_frame is None:
                # Return a blank frame if no frame is available
                blank = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(
                    blank, "No frame available", (180, 240),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2, cv2.LINE_AA
                )
                return blank
            return self.result_frame.copy()
    
    def set_attendance_mode(self, enabled, subject=None):
        """
        Set attendance mode
        
        Args:
            enabled (bool): Whether to enable attendance mode
            subject (str, optional): Subject name for attendance tracking
        """
        self.attendance_mode = enabled
        self.training_mode = False  # Disable training mode
        
        if enabled:
            self.current_subject = subject
            self.marked_students = set()  # Reset marked students
            self.status = f"Attendance: {subject}"
        else:
            self.current_subject = None
            self.status = "Display mode"
            
        logger.info(f"Attendance mode {'enabled for ' + subject if enabled else 'disabled'}")
    
    def set_training_mode(self, enabled, name=None, student_id=None, max_images=None):
        """
        Set training mode
        
        Args:
            enabled (bool): Whether to enable training mode
            name (str, optional): Name of the person to train
            student_id (str, optional): Student ID
            max_images (int, optional): Maximum number of training images
        """
        self.training_mode = enabled
        self.attendance_mode = False  # Disable attendance mode
        
        if enabled and name and student_id:
            self.training_name = name
            self.training_id = student_id
            if max_images:
                self.max_training_images = max_images
            self.image_count = 0
            self.last_training_capture = 0
            self.status = f"Training: {name} ({student_id})"
        else:
            self.training_name = None
            self.training_id = None
            self.status = "Display mode"
            
        logger.info(f"Training mode {'enabled for ' + name if enabled else 'disabled'}")
    
    def set_video_device(self, device_id):
        """
        Change the video capture device
        
        Args:
            device_id (int or str): Camera index or path to video file
            
        Returns:
            bool: Success or failure
        """
        # Stop current processing
        was_running = self.is_running
        if was_running:
            self.stop()
            
        # Update device
        self.video_device = device_id
        
        # Restart if it was running
        if was_running:
            return self.start()
        return True
    
    def set_recognition_params(self, confidence_threshold=None, min_face_size=None, recognition_interval=None):
        """
        Set recognition parameters
        
        Args:
            confidence_threshold (float, optional): Confidence threshold (0.0-1.0)
            min_face_size (int, optional): Minimum face size in pixels
            recognition_interval (float, optional): Recognition interval in seconds
        """
        if confidence_threshold is not None:
            self.confidence_threshold = max(0.1, min(confidence_threshold, 1.0))
            
        if min_face_size is not None:
            self.min_face_size = max(10, min_face_size)
            
        if recognition_interval is not None:
            self.recognition_interval = max(0.1, recognition_interval)
            
        logger.info(f"Updated recognition parameters: threshold={self.confidence_threshold}, "
                   f"min_face_size={self.min_face_size}, interval={self.recognition_interval}")
    
    def is_active(self):
        """Check if the video processor is active"""
        return self.is_running and self.processing_thread and self.processing_thread.is_alive()
    
    def get_status(self):
        """Get current status"""
        return {
            "mode": "training" if self.training_mode else "attendance" if self.attendance_mode else "display",
            "status": self.status,
            "fps": self.fps,
            "active": self.is_active(),
            "subject": self.current_subject,
            "training_progress": f"{self.image_count}/{self.max_training_images}" if self.training_mode else None,
            "marked_students": len(self.marked_students) if self.attendance_mode else 0
        } 