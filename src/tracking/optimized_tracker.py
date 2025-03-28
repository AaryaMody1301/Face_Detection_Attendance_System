"""
Optimized attendance tracking module with improved video processing
"""
import os
import cv2
import tkinter as tk
import numpy as np
import logging
import threading
import time
import datetime
from queue import Queue
from PIL import Image, ImageTk
import customtkinter as ctk

from ..utils.video_utils import VideoStream, FaceDetectionProcessor
from ..face_recognition.detector import FaceDetector
from ..utils.app_config import AppConfig

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OptimizedAttendanceTracker:
    """Optimized attendance tracking with advanced video processing"""
    
    def __init__(self, db_handler, parent_widget, video_frame, status_callback=None):
        """
        Initialize the attendance tracker
        
        Args:
            db_handler: Database handler for storing attendance records
            parent_widget: Parent tkinter widget
            video_frame: Tkinter widget to display video feed
            status_callback: Callback function for status updates
        """
        self.db = db_handler
        self.parent = parent_widget
        self.video_frame = video_frame
        self.status_callback = status_callback
        self._displayed_imgs = []  # Store strong references to displayed images
        
        # Load configuration
        self.config = AppConfig()
        
        # Initialize face detector with configuration settings
        face_config = self.config.get("face_recognition")
        self.face_detector = FaceDetector(
            detection_model=face_config.get("detection_model", "hog"),
            scale_factor=face_config.get("scale_factor", 0.5)
        )
        
        # Load trained model if available
        model_path = os.path.join("TrainingImageLabel", "trainner.yml")
        if os.path.exists(model_path):
            self.face_detector.load_model(model_path)
            logger.info(f"Face recognition model loaded: {model_path}")
        
        # Initialize video stream
        video_config = self.config.get("video")
        self.video_stream = None
        self.processor = None
        
        # Tracking state
        self.is_tracking = False
        self.tracking_thread = None
        self.stop_event = threading.Event()
        self.frame_queue = Queue(maxsize=5)
        
        # Tracking session data
        self.current_subject = None
        self.session_id = None
        self.session_start_time = None
        self.recognized_students = {}
    
    def start_tracking(self, subject):
        """
        Start attendance tracking
        
        Args:
            subject (str): Subject name for the attendance session
            
        Returns:
            bool: True if tracking started successfully
        """
        if self.is_tracking:
            logger.warning("Tracking is already active")
            return False
        
        # Store subject
        self.current_subject = subject
        
        # Create attendance session in database
        now = datetime.datetime.now()
        date = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")
        
        self.session_id = self.db.create_attendance_record(subject, date, time_str)
        if not self.session_id:
            logger.error("Failed to create attendance record")
            self._update_status("Failed to create attendance record")
            return False
        
        # Initialize video stream
        video_config = self.config.get("video")
        self.video_stream = VideoStream(
            src=0,
            width=video_config.get("width", 640),
            height=video_config.get("height", 480),
        )
        
        # Start video stream
        if not self.video_stream.start():
            logger.error("Failed to start video stream")
            self._update_status("Failed to start camera")
            return False
        
        # Initialize face detection processor
        face_config = self.config.get("face_recognition")
        self.processor = FaceDetectionProcessor(
            detector=self.face_detector,
            recognition_threshold=face_config.get("recognition_threshold", 0.6),
            processing_scale=face_config.get("scale_factor", 0.5),
            min_face_size=face_config.get("min_face_size", 30),
            max_faces=face_config.get("max_faces", 10),
            stabilization_frames=face_config.get("stabilization_frames", 3)
        )
        
        # Reset tracking state
        self.stop_event.clear()
        self.recognized_students = {}
        self.session_start_time = time.time()
        self.is_tracking = True
        
        # Start tracking in a separate thread
        self.tracking_thread = threading.Thread(target=self._tracking_loop, daemon=True)
        self.tracking_thread.start()
        
        self._update_status(f"Tracking started for subject: {subject}")
        return True
    
    def stop_tracking(self):
        """
        Stop attendance tracking
        
        Returns:
            tuple: (attendance_count, student_list)
        """
        if not self.is_tracking:
            logger.warning("No tracking session is active")
            return 0, []
        
        # Signal thread to stop
        self.stop_event.set()
        
        # Wait for thread to finish
        if self.tracking_thread and self.tracking_thread.is_alive():
            self.tracking_thread.join(timeout=2.0)
        
        # Stop video stream
        if self.video_stream:
            self.video_stream.stop()
            self.video_stream = None
        
        # Update state
        self.is_tracking = False
        
        # Get attendance data
        attendance_count = len(self.recognized_students)
        student_list = list(self.recognized_students.values())
        
        # Clear video frame
        self._clear_video_frame()
        
        self._update_status(f"Tracking stopped. {attendance_count} students marked present.")
        
        return attendance_count, student_list
    
    def _tracking_loop(self):
        """Main tracking loop running in a separate thread"""
        fps_target = self.config.get("video", "fps", 30)
        # Ensure fps_target is always a number, defaulting to 30 if None
        if fps_target is None:
            fps_target = 30
        frame_interval = 1.0 / fps_target  # Time between frames
        
        while not self.stop_event.is_set():
            loop_start = time.time()
            
            try:
                # Read frame from video stream
                frame = self.video_stream.read()
                
                if frame is None:
                    logger.warning("Failed to read frame from video stream")
                    time.sleep(0.1)
                    continue
                
                # Process frame
                processed_frame, face_data = self.processor.process_frame(frame)
                
                # Mark attendance for recognized faces
                self._process_attendance(face_data)
                
                # Add additional information to the frame
                processed_frame = self._add_tracking_info(processed_frame)
                
                # Convert to PIL format for tkinter
                self._update_video_frame(processed_frame)
                
                # Calculate time to wait for next frame
                processing_time = time.time() - loop_start
                wait_time = max(0, frame_interval - processing_time)
                
                if wait_time > 0:
                    time.sleep(wait_time)
                
            except Exception as e:
                logger.error(f"Error in tracking loop: {e}")
                time.sleep(0.1)
    
    def _process_attendance(self, face_data):
        """Process attendance for recognized faces"""
        for face in face_data:
            name = face["name"]
            confidence = face["confidence"]
            
            # Skip unknown faces
            if name == "Unknown":
                continue
            
            # Split name and ID if needed
            if "." in name:
                parts = name.split(".")
                if len(parts) >= 2:
                    name, student_id = parts[0], parts[1]
                else:
                    student_id = name  # Use name as ID if can't parse
            else:
                student_id = name  # Use name as ID if no dot separator
            
            # Create a unique key for this student
            student_key = f"{student_id}_{name}"
            
            # If student not already recognized with higher confidence
            if (student_key not in self.recognized_students or 
                self.recognized_students[student_key]["confidence"] < confidence):
                
                # Mark attendance in database
                now = datetime.datetime.now()
                date = now.strftime("%Y-%m-%d")
                time_str = now.strftime("%H:%M:%S")
                
                success = self.db.mark_attendance(
                    enrollment=student_id,
                    name=name,
                    subject=self.current_subject,
                    date=date,
                    time=time_str,
                    confidence=confidence
                )
                
                if success:
                    # Store in recognized students
                    self.recognized_students[student_key] = {
                        "id": student_id,
                        "name": name,
                        "time": time_str,
                        "confidence": confidence
                    }
                    
                    self._update_status(f"✓ Marked attendance for {name}")
    
    def _add_tracking_info(self, frame):
        """Add tracking information to the frame"""
        if frame is None:
            return None
        
        # Add attendance count
        attendance_count = len(self.recognized_students)
        attendance_text = f"Attendance Count: {attendance_count}"
        cv2.putText(frame, attendance_text, (10, 30), 
                  cv2.FONT_HERSHEY_SIMPLEX, 0.8, (50, 50, 255), 2)
        
        # Add subject
        subject_text = f"Subject: {self.current_subject}"
        cv2.putText(frame, subject_text, (10, 60), 
                  cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50, 50, 255), 2)
        
        # Add elapsed time
        elapsed_time = time.time() - self.session_start_time
        time_text = f"Time: {int(elapsed_time)}s"
        cv2.putText(frame, time_text, (10, 90), 
                  cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50, 50, 255), 2)
        
        return frame
    
    def _update_video_frame(self, frame):
        """Update the video frame in the UI"""
        if frame is None or self.video_frame is None:
            return
        
        try:
            # Convert from BGR (OpenCV format) to RGB (PIL format)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Convert to PIL format
            pil_image = Image.fromarray(frame_rgb)
            
            # Check if we're using the custom VideoDisplayWidget
            if hasattr(self.video_frame, 'display_image'):
                # Direct display using our custom widget
                self.parent.after(0, lambda: self.video_frame.display_image(pil_image))
            else:
                # Fallback to old method for compatibility
                # Get current dimensions
                try:
                    width = self.video_frame.winfo_width()
                    height = self.video_frame.winfo_height()
                except:
                    width = 640
                    height = 480
                
                # Make sure dimensions are reasonable
                if width < 10:
                    width = 640
                if height < 10:
                    height = 480
                    
                # Resize if the widget has valid dimensions
                img_width, img_height = pil_image.size
                ratio = min(width/img_width, height/img_height)
                new_width = int(img_width * ratio)
                new_height = int(img_height * ratio)
                
                # Resize the image
                pil_image = pil_image.resize((new_width, new_height), Image.LANCZOS)
                
                # Convert to Tkinter format
                tk_image = ImageTk.PhotoImage(pil_image)
                
                # Schedule update in the main thread
                if not self.stop_event.is_set():
                    self.parent.after(0, lambda: self._set_image(tk_image))
            
        except Exception as e:
            logger.error(f"Error updating video frame: {e}")
    
    def _set_image(self, image):
        """Set the image on the video frame (called from main thread)"""
        try:
            # Check if widget exists and is valid
            if self.video_frame and hasattr(self.video_frame, 'configure'):
                # Store reference in both the instance and the widget
                self.video_frame.configure(image=image)
                # Keep a STRONG reference to the image to prevent garbage collection
                self.video_frame.image = image
                
                # Also keep image in a list of references to ensure it's not garbage collected
                self._displayed_imgs.append(image)
                # Limit the list size to prevent memory leak (keep last 5 images)
                if len(self._displayed_imgs) > 5:
                    self._displayed_imgs.pop(0)
        except Exception as e:
            logger.error(f"Error setting image: {e}")
            
    def _clear_video_frame(self):
        """Clear the video frame"""
        try:
            # Check if we're using the custom VideoDisplayWidget
            if hasattr(self.video_frame, 'clear'):
                self.video_frame.clear()
            elif hasattr(self.video_frame, 'configure'):
                self.video_frame.configure(image='')
                self.video_frame.image = None
                self._displayed_imgs.clear()
        except Exception as e:
            logger.error(f"Error clearing video frame: {e}")
    
    def _update_status(self, message):
        """Update status using the callback if available"""
        if self.status_callback and callable(self.status_callback):
            self.status_callback(message)
        else:
            logger.info(message)
    
    def get_performance_stats(self):
        """Get performance statistics"""
        if not self.processor:
            return {}
        
        stats = self.processor.get_stats()
        
        if self.video_stream:
            # Add video stream stats
            stats["frame_count"] = self.video_stream.frame_count
            stats["resolution"] = self.video_stream.get_resolution()
        
        return stats
    
    def update_camera_settings(self, camera_id=None, resolution=None, fps=None, flip=None):
        """
        Update camera settings during runtime
        
        Args:
            camera_id (int, optional): Camera device ID
            resolution (list, optional): [width, height] resolution
            fps (int, optional): Frames per second
            flip (bool, optional): Whether to flip the image horizontally
            
        Returns:
            bool: Whether the update was successful
        """
        try:
            # Update configuration
            if camera_id is not None:
                self.config.set("camera.id", camera_id)
            
            if resolution is not None:
                self.config.set("camera.resolution", resolution)
                
                # Also update video configuration
                if isinstance(resolution, (list, tuple)) and len(resolution) >= 2:
                    self.config.set("video.width", resolution[0])
                    self.config.set("video.height", resolution[1])
            
            if fps is not None:
                self.config.set("camera.fps", fps)
                self.config.set("video.fps", fps)
                
            if flip is not None:
                self.config.set("camera.flip_image", flip)
                
            # Save configuration
            self.config.save_config()
            
            # If we have an active video stream, we need to restart it
            needs_restart = self.video_stream is not None
            
            # Stop the current video stream if active
            if needs_restart:
                self.video_stream.stop()
                
            # Create a new video stream with updated settings
            if needs_restart:
                # Initialize video stream with new settings
                self.video_stream = VideoStream(
                    src=camera_id if camera_id is not None else 0,
                    width=resolution[0] if resolution is not None else self.config.get("video.width", 640),
                    height=resolution[1] if resolution is not None else self.config.get("video.height", 480),
                    fps=fps if fps is not None else self.config.get("video.fps", 30),
                    flip_horizontal=flip if flip is not None else self.config.get("camera.flip_image", False)
                )
                
                # Start the new video stream
                if not self.video_stream.start():
                    self._update_status("Failed to restart video stream with new settings")
                    return False
                
                self._update_status("Camera settings updated successfully")
                
            return True
            
        except Exception as e:
            logger.exception(f"Error updating camera settings: {e}")
            self._update_status(f"Error updating camera settings: {str(e)}")
            return False