"""
Attendance View for the Face Detection Attendance System
"""
import os
import time
import threading
import datetime
import logging
import cv2
import numpy as np
import tkinter as tk
from tkinter import StringVar, BooleanVar
import customtkinter as ctk
from PIL import Image, ImageTk

from .base_view import BaseView
from ..controllers.attendance_controller import AttendanceController
from ..utils.exceptions import RecognitionError, ValidationError

class AttendanceView(BaseView):
    """
    View for marking attendance with face recognition
    
    Attributes:
        controller: AttendanceController instance
        camera_active: Whether the camera is active
        is_recognizing: Whether face recognition is in progress
        subject_var: StringVar for subject input
        camera: OpenCV camera capture object
        face_detected: Whether a face is detected in the current frame
        face_recognized: Whether a face is recognized in the current frame
    """
    
    def __init__(self, master, auth_system, **kwargs):
        """
        Initialize the attendance view
        
        Args:
            master: Parent widget
            auth_system: Authentication system
            **kwargs: Additional arguments for BaseView
        """
        # Initialize base view
        super().__init__(master, **kwargs)
        
        # Initialize controller
        self.controller = AttendanceController()
        
        # Initialize camera variables
        self.camera_active = False
        self.camera_thread = None
        self.camera = None
        self.camera_id = 0
        self.frame_rate = 30
        self.resolution = (640, 480)
        self.flip_image = False
        
        # Initialize recognition state
        self.is_recognizing = False
        self.recognition_cooldown = 2.0  # seconds
        self.last_recognition_time = 0
        self.face_detected = False
        self.face_recognized = False
        self.recognition_result = None
        
        # Initialize UI variables
        self.subject_var = StringVar(value="")
        self.status_var = StringVar(value="Ready")
        self.auto_recognize_var = BooleanVar(value=True)
        
        # Set up the UI
        self.setup_ui()
        
        # Start camera
        self.start_camera()
    
    def setup_ui(self):
        """Set up the UI components"""
        # Main layout - 2x1 grid
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=3)  # Camera feed (larger)
        self.rowconfigure(1, weight=1)  # Controls (smaller)
        
        # Create camera frame
        self.camera_frame = ctk.CTkFrame(self, corner_radius=15)
        self.camera_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        # Create camera feed label
        self.camera_label = ctk.CTkLabel(self.camera_frame, text="")
        self.camera_label.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create controls frame
        self.controls_frame = ctk.CTkFrame(self, corner_radius=15)
        self.controls_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        
        # Configure controls layout - 1x2 grid
        self.controls_frame.columnconfigure(0, weight=1)  # Form inputs
        self.controls_frame.columnconfigure(1, weight=1)  # Results/status
        self.controls_frame.rowconfigure(0, weight=1)
        
        # Create form frame
        self.form_frame = ctk.CTkFrame(self.controls_frame, corner_radius=10)
        self.form_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        # Subject selection
        self.subject_label = ctk.CTkLabel(
            self.form_frame, 
            text="Subject:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.subject_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        # Get available subjects (hardcoded for now, could come from database)
        subjects = ["Python", "Maths", "Physics", "Chemistry", "Biology"]
        
        self.subject_combobox = ctk.CTkComboBox(
            self.form_frame,
            values=subjects,
            variable=self.subject_var,
            width=200,
            height=40
        )
        self.subject_combobox.pack(anchor="w", padx=10, pady=(0, 10))
        
        # Auto-recognize checkbox
        self.auto_recognize_checkbox = ctk.CTkCheckBox(
            self.form_frame,
            text="Auto-recognize faces",
            variable=self.auto_recognize_var,
            checkbox_width=20,
            checkbox_height=20
        )
        self.auto_recognize_checkbox.pack(anchor="w", padx=10, pady=10)
        
        # Manual capture button
        self.capture_button = ctk.CTkButton(
            self.form_frame,
            text="Capture and Recognize",
            command=self.on_capture_button,
            height=40,
            width=200,
            corner_radius=8,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.capture_button.pack(anchor="w", padx=10, pady=10)
        
        # Camera controls
        self.camera_controls_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        self.camera_controls_frame.pack(fill="x", padx=10, pady=10)
        
        # Restart camera button
        self.restart_camera_button = ctk.CTkButton(
            self.camera_controls_frame,
            text="Restart Camera",
            command=self.restart_camera,
            height=30,
            width=200,
            corner_radius=8
        )
        self.restart_camera_button.pack(anchor="w", pady=5)
        
        # Create results frame
        self.results_frame = ctk.CTkFrame(self.controls_frame, corner_radius=10)
        self.results_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        
        # Status label
        self.status_label = ctk.CTkLabel(
            self.results_frame,
            text="Status:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.status_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        self.status_value_label = ctk.CTkLabel(
            self.results_frame,
            textvariable=self.status_var,
            font=ctk.CTkFont(size=14)
        )
        self.status_value_label.pack(anchor="w", padx=10, pady=(0, 10))
        
        # Recent attendances (placeholder)
        self.recent_label = ctk.CTkLabel(
            self.results_frame,
            text="Recent Attendance:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.recent_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        # Recent attendance scrollable frame
        self.recent_frame = ctk.CTkScrollableFrame(
            self.results_frame,
            width=300,
            height=100,
            corner_radius=8
        )
        self.recent_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Progress bar for face detection confidence
        self.progress_label = ctk.CTkLabel(
            self.results_frame,
            text="Recognition Confidence:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.progress_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        self.progress_bar = ctk.CTkProgressBar(
            self.results_frame,
            width=300,
            height=15,
            corner_radius=5
        )
        self.progress_bar.pack(anchor="w", padx=10, pady=(0, 10))
        self.progress_bar.set(0)
    
    def start_camera(self):
        """Start the camera in a separate thread"""
        if self.camera_active:
            return  # Camera already active
        
        try:
            # Initialize camera
            self.camera = cv2.VideoCapture(self.camera_id)
            
            # Configure camera
            if self.resolution:
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
            
            if self.frame_rate:
                self.camera.set(cv2.CAP_PROP_FPS, self.frame_rate)
            
            # Check if camera opened successfully
            if not self.camera.isOpened():
                self.show_error("Failed to open camera")
                return
            
            # Set camera active flag
            self.camera_active = True
            
            # Start camera thread
            self.camera_thread = threading.Thread(target=self.update_camera_feed, daemon=True)
            self.camera_thread.start()
            
            self.logger.info("Camera started successfully")
            self.status_var.set("Camera active")
            
        except Exception as e:
            self.logger.error(f"Error starting camera: {e}")
            self.show_error(f"Failed to start camera: {str(e)}")
    
    def stop_camera(self):
        """Stop the camera"""
        # Set camera inactive flag
        self.camera_active = False
        
        # Wait for thread to finish
        if self.camera_thread:
            self.camera_thread.join(1.0)  # Wait up to 1 second
            self.camera_thread = None
        
        # Release camera
        if self.camera:
            self.camera.release()
            self.camera = None
            
        self.logger.info("Camera stopped")
        self.status_var.set("Camera inactive")
    
    def restart_camera(self):
        """Restart the camera"""
        self.stop_camera()
        time.sleep(1)  # Small delay to ensure camera is released
        self.start_camera()
    
    def update_camera_feed(self):
        """Update camera feed in a loop"""
        frame_count = 0
        last_time = time.time()
        
        while self.camera_active:
            try:
                # Read a frame from the camera
                ret, frame = self.camera.read()
                
                if not ret or frame is None:
                    self.logger.warning("Failed to read frame from camera")
                    time.sleep(0.1)
                    continue
                
                # Flip the image if needed
                if self.flip_image:
                    frame = cv2.flip(frame, 1)  # Flip horizontally
                
                # Process frame for display
                processed_frame = self.process_frame(frame)
                
                # If auto-recognize is enabled, check if we should recognize faces
                if self.auto_recognize_var.get() and not self.is_recognizing:
                    # Check cooldown
                    current_time = time.time()
                    if current_time - self.last_recognition_time > self.recognition_cooldown:
                        # Start recognition in a separate thread
                        if self.face_detected:
                            self.is_recognizing = True
                            threading.Thread(
                                target=self.recognize_face,
                                args=(frame.copy(),),
                                daemon=True
                            ).start()
                
                # Update FPS counter
                frame_count += 1
                current_time = time.time()
                elapsed_time = current_time - last_time
                
                if elapsed_time >= 1.0:  # Update FPS every second
                    fps = frame_count / elapsed_time
                    frame_count = 0
                    last_time = current_time
                    
                    # Update status with FPS
                    status = self.status_var.get()
                    if "FPS" in status:
                        # Remove FPS from status
                        status = status.split(" | ")[0]
                    
                    self.status_var.set(f"{status} | {fps:.1f} FPS")
                
            except Exception as e:
                self.logger.error(f"Error in camera feed: {e}")
                time.sleep(0.1)
    
    def process_frame(self, frame):
        """
        Process a frame from the camera
        
        Args:
            frame: OpenCV frame
            
        Returns:
            Processed frame
        """
        try:
            # Convert BGR to RGB (required for PIL/Tkinter)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Detect faces (simplified version - in real app this would use a proper face detector)
            # This is just a placeholder for demonstration
            face_detected = self.check_for_face(rgb_frame)
            self.face_detected = face_detected
            
            # Add a face indicator rectangle if face is detected
            if face_detected:
                # Add a simple green rectangle (this would be replaced with actual face detection)
                cv2.rectangle(
                    rgb_frame, 
                    (int(rgb_frame.shape[1]/2 - 50), int(rgb_frame.shape[0]/2 - 50)),
                    (int(rgb_frame.shape[1]/2 + 50), int(rgb_frame.shape[0]/2 + 50)),
                    (0, 255, 0), 
                    2
                )
            
            # Add visual feedback for recognized faces
            if self.face_recognized and self.recognition_result:
                # Add name and confidence
                cv2.putText(
                    rgb_frame,
                    f"{self.recognition_result['name']} ({self.recognition_result['confidence']:.2f})",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 255, 0),
                    2
                )
            
            # Convert to PIL format
            pil_image = Image.fromarray(rgb_frame)
            
            # Resize to fit display area
            pil_image = self.resize_image_to_fit(pil_image, 600, 400)
            
            # Convert to Tkinter format
            tk_image = ImageTk.PhotoImage(pil_image)
            
            # Update image in the main thread
            self.after(0, lambda: self.update_image(tk_image))
            
            return rgb_frame
            
        except Exception as e:
            self.logger.error(f"Error processing frame: {e}")
            return frame
    
    def update_image(self, tk_image):
        """
        Update the camera image
        
        Args:
            tk_image: Tkinter PhotoImage
        """
        self.camera_label.configure(image=tk_image)
        self.camera_label.image = tk_image  # Keep a reference to prevent garbage collection
    
    def resize_image_to_fit(self, pil_image, max_width, max_height):
        """
        Resize image to fit within max dimensions while preserving aspect ratio
        
        Args:
            pil_image: PIL Image
            max_width: Maximum width
            max_height: Maximum height
            
        Returns:
            Resized PIL Image
        """
        width, height = pil_image.size
        
        # Calculate the aspect ratio
        aspect_ratio = width / height
        
        # Determine new dimensions
        if width > max_width or height > max_height:
            if width / max_width > height / max_height:
                # Width is the limiting factor
                new_width = max_width
                new_height = int(max_width / aspect_ratio)
            else:
                # Height is the limiting factor
                new_height = max_height
                new_width = int(max_height * aspect_ratio)
                
            # Resize image
            pil_image = pil_image.resize((new_width, new_height), Image.LANCZOS)
            
        return pil_image
    
    def check_for_face(self, frame):
        """
        Check if a face is in the frame (placeholder)
        
        Args:
            frame: OpenCV frame
            
        Returns:
            bool: True if a face is detected, False otherwise
        """
        # This is a placeholder that always returns True for demonstration
        # In a real application, this would use a proper face detection algorithm
        return True
    
    def on_capture_button(self):
        """Handle capture button click"""
        if not self.camera_active:
            self.show_warning("Camera is not active")
            return
            
        if self.is_recognizing:
            self.show_warning("Recognition already in progress")
            return
            
        subject = self.subject_var.get()
        if not subject:
            self.show_warning("Please select a subject")
            return
            
        try:
            # Read a frame from the camera
            ret, frame = self.camera.read()
            
            if not ret or frame is None:
                self.show_error("Failed to capture frame from camera")
                return
                
            # Flip the image if needed
            if self.flip_image:
                frame = cv2.flip(frame, 1)
                
            # Start recognition in a separate thread
            self.is_recognizing = True
            threading.Thread(
                target=self.recognize_face,
                args=(frame.copy(),),
                daemon=True
            ).start()
            
        except Exception as e:
            self.logger.error(f"Error capturing frame: {e}")
            self.show_error(f"Failed to capture frame: {str(e)}")
            self.is_recognizing = False
    
    def recognize_face(self, frame):
        """
        Recognize face in frame and mark attendance
        
        Args:
            frame: OpenCV frame
        """
        try:
            # Update status
            self.after(0, lambda: self.status_var.set("Recognizing face..."))
            
            # Get subject
            subject = self.subject_var.get()
            
            # Call controller to recognize and mark attendance
            result = self.controller.recognize_and_mark_attendance(frame, subject)
            
            # Store last recognition time
            self.last_recognition_time = time.time()
            
            # Process result in the main thread
            self.after(0, lambda: self.process_recognition_result(result))
            
        except Exception as e:
            self.logger.error(f"Error in face recognition: {e}")
            
            # Update status in the main thread
            self.after(0, lambda: self.status_var.set(f"Recognition error: {str(e)}"))
            self.after(0, lambda: self.progress_bar.set(0))
            
        finally:
            # Reset recognition flag
            self.is_recognizing = False
    
    def process_recognition_result(self, result):
        """
        Process recognition result in the main thread
        
        Args:
            result: Recognition result from controller
        """
        if result.get("success", False):
            # Recognition successful
            data = result.get("data", {})
            name = data.get("name", "Unknown")
            enrollment = data.get("enrollment", "")
            confidence = data.get("confidence", 0.0)
            
            # Update UI
            self.status_var.set(f"Recognized {name} ({enrollment})")
            self.progress_bar.set(confidence)
            
            # Store recognition result for display
            self.face_recognized = True
            self.recognition_result = {
                "name": name,
                "enrollment": enrollment,
                "confidence": confidence
            }
            
            # Add to recent attendances
            self.add_recent_attendance(name, enrollment, confidence)
            
        else:
            # Recognition failed
            error = result.get("error", {})
            message = error.get("message", "Unknown error")
            
            # Update UI
            self.status_var.set(f"Recognition failed: {message}")
            self.progress_bar.set(0)
            self.face_recognized = False
            self.recognition_result = None
    
    def add_recent_attendance(self, name, enrollment, confidence):
        """
        Add a recent attendance to the UI
        
        Args:
            name: Student name
            enrollment: Student enrollment ID
            confidence: Recognition confidence
        """
        # Create a frame for the attendance entry
        entry_frame = ctk.CTkFrame(self.recent_frame)
        entry_frame.pack(fill="x", padx=5, pady=5)
        
        # Current time
        now = datetime.datetime.now().strftime("%H:%M:%S")
        
        # Add name and time
        name_label = ctk.CTkLabel(
            entry_frame,
            text=f"{name} ({enrollment})",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        name_label.pack(anchor="w", padx=5, pady=2)
        
        # Add time and confidence
        time_label = ctk.CTkLabel(
            entry_frame,
            text=f"Time: {now} | Confidence: {confidence:.2f}",
            font=ctk.CTkFont(size=10)
        )
        time_label.pack(anchor="w", padx=5, pady=2)
    
    def update_camera_settings(self, camera_id=0, resolution=None, fps=30, flip=False):
        """
        Update camera settings
        
        Args:
            camera_id: Camera ID
            resolution: Tuple of (width, height)
            fps: Frame rate
            flip: Whether to flip the image horizontally
        """
        # Store settings
        self.camera_id = camera_id
        self.resolution = resolution
        self.frame_rate = fps
        self.flip_image = flip
        
        # Restart camera to apply settings
        self.restart_camera()
    
    def on_app_close(self):
        """Clean up resources when application is closed"""
        self.on_close()
    
    def on_close(self):
        """Clean up resources when view is closed"""
        super().on_close()
        
        # Stop camera
        self.stop_camera()
        
        # Clean up controller
        if self.controller:
            self.controller.cleanup()