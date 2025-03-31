"""
Attendance View for Face Detection Attendance System
"""
import os
import sys
import cv2
import time
import logging
import numpy as np
import tkinter as tk
import pandas as pd
import threading
import customtkinter as ctk
from PIL import Image, ImageTk
from datetime import datetime
import csv
import face_recognition
import tkinter.messagebox as messagebox
import tkinter.ttk as ttk

from src.core.utils.config_manager import ConfigManager
from src.face_recognition.face_detector import FaceDetector

# Set up logging
logger = logging.getLogger(__name__)

class AttendanceView(ctk.CTkFrame):
    """Attendance View with face detection for marking attendance"""
    
    def __init__(self, master=None, config=None, **kwargs):
        """
        Initialize attendance view
        
        Args:
            master: Parent window
            config: Application configuration
        """
        super().__init__(master, **kwargs)
        
        self.master = master
        self.config = config
        
        # Initialize camera variables
        self.camera = None
        self.camera_running = False
        self.camera_thread = None
        self.auto_mode = True  # Default to auto mode
        self.failed_frames_count = 0
        
        # Track after() calls for cleanup
        self.after_ids = []
        
        # Initialize face detector if needed
        self.face_detector = None
        self.confidence_threshold = 0.6  # Confidence threshold (0-1)
        
        # Load subjects from config
        self.subjects = ["No Subject"]
        if config and hasattr(config, 'get'):
            # Get subjects from config
            self.subjects = config.get("courses", ["Computer Science", "Mathematics", "Physics"])
            
            # Get camera index from config
            self.camera_index = config.get("camera_index", 0)
            
            # Get confidence threshold from config
            self.confidence_threshold = config.get("confidence_threshold", 0.6)
        else:
            # Default values
            self.subjects = ["Computer Science", "Mathematics", "Physics"]
            self.camera_index = 0
        
        # Initialize attendance list
        self.attendance_list = []
        
        # Setup UI
        self._setup_ui()
        
        # Initialize face detector
        try:
            students_csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                                           "data", "students.csv")
            
            # Log the path to help with debugging
            logger.info(f"Looking for students CSV at: {students_csv_path}")
            
            # Check if file exists
            if not os.path.exists(students_csv_path):
                logger.warning(f"Students CSV file not found at {students_csv_path}")
                # Try to create a basic CSV file if it doesn't exist
                try:
                    os.makedirs(os.path.dirname(students_csv_path), exist_ok=True)
                    with open(students_csv_path, 'w', newline='') as f:
                        f.write("ID,Name,Course,Year\n")
                        f.write("1001,John Smith,Computer Science,2023\n")
                        f.write("1002,Jane Doe,Mathematics,2024\n")
                    logger.info(f"Created default students CSV file at {students_csv_path}")
                except Exception as e:
                    logger.error(f"Error creating default students CSV: {e}")
            
            # Initialize the face detector
            self.face_detector = FaceDetector(
                method='haar',
                threshold=self.confidence_threshold,
                students_csv_path=students_csv_path
            )
            logger.info(f"Initialized face detector with threshold {self.confidence_threshold}")
            
        except Exception as e:
            logger.error(f"Error initializing face detector: {e}")
            self.show_status(f"Error initializing face detection: {e}", "red")
        
        # Initialize other variables
        self.show_camera_in_manual_mode = self.config.get("attendance", {}).get("show_camera_in_manual_mode", True)
        self.detected_faces = set()
        self.student_tree_frame = None
        self.student_tree = None
        self.photo = None
        
        # Set up event handlers
        self._setup_event_handlers()
        
        logger.info("Attendance View initialized")
    
    def _setup_ui(self):
        """Set up the UI components"""
        # Configure grid layout
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Top Left: Camera View
        self.camera_frame = ctk.CTkFrame(self)
        self.camera_frame.grid(row=0, column=0, padx=(20, 10), pady=(20, 10), sticky="nsew")
        self.camera_frame.grid_rowconfigure(0, weight=1)
        self.camera_frame.grid_columnconfigure(0, weight=1)
        
        # Camera View
        self.camera_view = ctk.CTkLabel(
            self.camera_frame,
            text="Camera not started",
            font=ctk.CTkFont(size=20),
            fg_color="#1a1a1a",
            corner_radius=8
        )
        self.camera_view.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        
        # FPS Label on top of camera view
        self.fps_label = ctk.CTkLabel(
            self.camera_frame,
            text="FPS: 0.0",
            font=ctk.CTkFont(size=12),
            fg_color=("#3498db", "#2980b9"),  # Blue shade
            text_color="white",
            corner_radius=5,
            width=80,
            height=25
        )
        self.fps_label.place(relx=0.05, rely=0.05, anchor="nw")
        
        # Loading animation container
        self.loading_frame = ctk.CTkFrame(self.camera_frame, fg_color="transparent")
        self.loading_frame.grid(row=0, column=0, sticky="nsew")
        self.loading_frame.grid_rowconfigure(0, weight=1)
        self.loading_frame.grid_columnconfigure(0, weight=1)
        
        # Create loading animation
        self.loading_indicator = self._create_loading_indicator(self.loading_frame)
        self.loading_indicator.place(relx=0.5, rely=0.5, anchor="center")
        self.loading_indicator.grid_remove()  # Hide initially
        
        # Error message container
        self.error_frame = ctk.CTkFrame(self.camera_frame, fg_color="transparent")
        self.error_frame.grid(row=0, column=0, sticky="nsew")
        self.error_frame.grid_rowconfigure(0, weight=1)
        self.error_frame.grid_columnconfigure(0, weight=1)
        
        # Error message
        self.error_message = ctk.CTkLabel(
            self.error_frame,
            text="",
            font=ctk.CTkFont(size=14),
            text_color="red"
        )
        self.error_message.place(relx=0.5, rely=0.5, anchor="center")
        self.error_frame.grid_remove()  # Hide initially
        
        # Top right: Attendance Controls
        self.controls_panel = ctk.CTkFrame(self)
        self.controls_panel.grid(row=0, column=1, padx=(10, 20), pady=(20, 10), sticky="nsew")
        self.controls_panel.grid_columnconfigure(0, weight=1)
        
        # Controls panel title
        self.controls_title = ctk.CTkLabel(
            self.controls_panel,
            text="Attendance Controls",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.controls_title.grid(row=0, column=0, padx=20, pady=(15, 15), sticky="w")
        
        # Subject selection with add button
        self.subject_frame = ctk.CTkFrame(self.controls_panel)
        self.subject_frame.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.subject_frame.grid_columnconfigure(1, weight=1)
        
        self.subject_label = ctk.CTkLabel(
            self.subject_frame,
            text="Subject/Course:",
            anchor="w",
            width=100
        )
        self.subject_label.grid(row=0, column=0, padx=(20, 10), pady=10, sticky="w")
        
        self.subject_var = ctk.StringVar(value=self.subjects[0] if self.subjects else "")
        self.subject_dropdown = ctk.CTkComboBox(
            self.subject_frame,
            values=self.subjects,
            variable=self.subject_var,
            state="readonly" if self.subjects else "disabled"
        )
        self.subject_dropdown.grid(row=0, column=1, padx=(0, 5), pady=10, sticky="ew")
        
        # Add subject button
        self.add_subject_button = ctk.CTkButton(
            self.subject_frame,
            text="+",
            width=30,
            command=self._add_new_subject
        )
        self.add_subject_button.grid(row=0, column=2, padx=(0, 20), pady=10, sticky="e")
        
        # Attendance mode toggle
        self.mode_frame = ctk.CTkFrame(self.controls_panel)
        self.mode_frame.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")
        
        self.mode_button = ctk.CTkButton(
            self.mode_frame,
            text="Auto Mode: ON",
            fg_color="green",
            command=self._toggle_mode
        )
        self.mode_button.grid(row=0, column=0, padx=20, pady=10, sticky="ew")
        
        # Manual entry fields
        self.manual_frame = ctk.CTkFrame(self.controls_panel)
        self.manual_frame.grid(row=3, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.manual_frame.grid_columnconfigure(0, weight=1)
        
        # Create student selection tree for manual mode
        self.student_tree_frame = ctk.CTkFrame(self.manual_frame)
        self.student_tree_frame.grid(row=0, column=0, padx=20, pady=10, sticky="nsew")
        self.student_tree_frame.grid_rowconfigure(0, weight=1)
        self.student_tree_frame.grid_columnconfigure(0, weight=1)
        
        # Treeview for student selection
        columns = ("id", "name")
        self.student_tree = ttk.Treeview(self.student_tree_frame, columns=columns, show="headings", height=5)
        
        # Define headings
        self.student_tree.heading("id", text="Student ID")
        self.student_tree.heading("name", text="Name")
        
        # Define columns
        self.student_tree.column("id", width=100)
        self.student_tree.column("name", width=250)
        
        # Add scrollbar
        vsb = ttk.Scrollbar(self.student_tree_frame, orient="vertical", command=self.student_tree.yview)
        self.student_tree.configure(yscrollcommand=vsb.set)
        
        # Grid treeview and scrollbar
        self.student_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        
        # Mark button
        self.mark_button = ctk.CTkButton(
            self.manual_frame,
            text="Mark Selected Student",
            command=self._add_manual_attendance
        )
        self.mark_button.grid(row=1, column=0, padx=20, pady=(5, 10), sticky="ew")
        
        # Hide manual entry fields initially
        self.manual_frame.grid_remove()
        
        # Action buttons
        self.action_frame = ctk.CTkFrame(self.controls_panel)
        self.action_frame.grid(row=4, column=0, padx=20, pady=(10, 10), sticky="ew")
        self.action_frame.grid_columnconfigure((0, 1), weight=1)
        
        self.start_button = ctk.CTkButton(
            self.action_frame,
            text="Start Camera",
            command=self._start_camera,
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40
        )
        self.start_button.grid(row=0, column=0, padx=(5, 5), pady=10, sticky="ew")
        
        self.stop_button = ctk.CTkButton(
            self.action_frame,
            text="Stop Camera",
            command=self._stop_camera,
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            state="disabled",
            fg_color="#B22222"
        )
        self.stop_button.grid(row=1, column=0, padx=(5, 5), pady=10, sticky="ew")
        
        self.save_button = ctk.CTkButton(
            self.action_frame,
            text="Save Attendance",
            command=self._save_attendance,
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            state="disabled"
        )
        self.save_button.grid(row=0, column=1, padx=(5, 5), pady=10, sticky="ew")
        
        self.clear_button = ctk.CTkButton(
            self.action_frame,
            text="Clear Records",
            command=self._clear_attendance,
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40
        )
        self.clear_button.grid(row=1, column=1, padx=(5, 5), pady=10, sticky="ew")
        
        # Status message
        self.status_label = ctk.CTkLabel(
            self.controls_panel,
            text="Ready to start camera",
            text_color="green",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.grid(row=5, column=0, padx=20, pady=(0, 20), sticky="ew")
        
        # Bottom: Attendance List
        self.list_panel = ctk.CTkFrame(self)
        self.list_panel.grid(row=1, column=0, columnspan=2, padx=20, pady=(10, 20), sticky="nsew")
        self.list_panel.grid_rowconfigure(1, weight=1)
        self.list_panel.grid_columnconfigure(0, weight=1)
        
        # List panel title
        self.list_title = ctk.CTkLabel(
            self.list_panel,
            text="Attendance List",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.list_title.grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")
        
        # Create treeview for attendance list
        self.tree_frame = ctk.CTkFrame(self.list_panel)
        self.tree_frame.grid(row=1, column=0, padx=20, pady=(5, 20), sticky="nsew")
        self.tree_frame.grid_rowconfigure(0, weight=1)
        self.tree_frame.grid_columnconfigure(0, weight=1)
        
        # Use Treeview
        columns = ("id", "name", "time")
        self.tree = ttk.Treeview(self.tree_frame, columns=columns, show="headings")
        
        # Define headings
        self.tree.heading("id", text="Student ID")
        self.tree.heading("name", text="Name")
        self.tree.heading("time", text="Time")
        
        # Define columns
        self.tree.column("id", width=100)
        self.tree.column("name", width=250)
        self.tree.column("time", width=150)
        
        # Add scrollbars
        vsb = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self.tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Grid treeview and scrollbars
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        # Configure style for treeview
        style = ttk.Style()
        bg_color = "#2b2b2b" if ctk.get_appearance_mode() == "Dark" else "#f0f0f0"
        text_color = "#dcddde" if ctk.get_appearance_mode() == "Dark" else "#000000"
        
        style.configure(
            "Treeview",
            background=bg_color,
            foreground=text_color,
            fieldbackground=bg_color,
            borderwidth=0
        )
        style.map('Treeview', background=[('selected', '#347ab3')])
    
    def _get_bg_color(self):
        """Get appropriate background color based on appearance mode"""
        appearance_mode = ctk.get_appearance_mode()
        if appearance_mode == "Dark":
            return "#2b2b2b"
        else:
            return "#f0f0f0"
    
    def _get_text_color(self):
        """Get appropriate text color based on appearance mode"""
        appearance_mode = ctk.get_appearance_mode()
        if appearance_mode == "Dark":
            return "#dcddde"
        else:
            return "#000000"
    
    def _get_subjects(self):
        """Get course/subject list from database or config"""
        try:
            # Try to get subjects from config
            subjects = self.config.get("courses", [])
            
            if not subjects:
                # Default subjects if none found
                subjects = ["Computer Science", "Mathematics", "Physics", "Chemistry", "Biology"]
                logger.info("Using default subject list")
            else:
                logger.info(f"Loaded {len(subjects)} subjects from config")
                
            return subjects
        except Exception as e:
            logger.error(f"Error loading subjects: {e}")
            return ["Default Subject"]  # Provide a fallback
    
    def _toggle_mode(self):
        """Toggle between auto and manual attendance modes"""
        try:
            self.auto_mode = not self.auto_mode
            
            if self.auto_mode:
                self.mode_button.configure(text="Auto Mode: ON", fg_color="green")
                self.status_label.configure(text="Auto mode enabled - faces will be detected automatically")
                
                # Disable manual controls in auto mode
                self.manual_frame.grid_remove()
                
                # If camera is running, ensure the label is visible
                if self.camera_running:
                    self.camera_view.grid()
            else:
                self.mode_button.configure(text="Auto Mode: OFF", fg_color="gray")
                self.status_label.configure(text="Manual mode enabled - select students from list")
                
                # Enable manual controls
                self.manual_frame.grid()
                
                # Hide camera view in manual mode if configured to do so
                if not self.show_camera_in_manual_mode and self.camera_running:
                    self.camera_view.grid_remove()
                
            logger.info(f"Attendance mode toggled to {'Auto' if self.auto_mode else 'Manual'}")
        except Exception as e:
            logger.error(f"Error toggling mode: {e}")
            messagebox.showerror("Error", f"Failed to toggle mode: {e}")
    
    def _start_camera(self):
        """Start the camera feed"""
        if self.camera_running:
            return
        
        # Show loading indicator
        self.camera_view.grid_remove()
        self.error_frame.grid_remove()
        self.loading_indicator.grid()
        self.show_status("Starting camera...")
        
        # Disable controls while camera is starting
        self.start_button.configure(state="disabled")
        
        # Start in a separate thread to avoid blocking UI
        self.camera_thread = threading.Thread(target=self._initialize_camera)
        self.camera_thread.daemon = True
        self.camera_thread.start()
    
    def _initialize_camera(self):
        """Initialize the camera in a background thread"""
        try:
            logger.info("Initializing camera...")
            self.camera = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)  # Try using DirectShow
            
            if not self.camera.isOpened():
                logger.warning("Failed to open camera with DirectShow, trying default")
                self.camera = cv2.VideoCapture(self.camera_index)  # Try default
            
            if not self.camera.isOpened():
                logger.error("Failed to open camera")
                self.master.after(0, self._camera_start_failed, "Failed to open camera")
                return False
            
            # Try different resolutions until one works
            resolutions = [(640, 480), (1280, 720), (800, 600), (320, 240)]
            for width, height in resolutions:
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                
                # Check if setting was successful by reading a test frame
                ret, test_frame = self.camera.read()
                if ret and test_frame is not None and test_frame.size > 0:
                    logger.info(f"Successfully set camera resolution to {width}x{height}")
                    actual_width = self.camera.get(cv2.CAP_PROP_FRAME_WIDTH)
                    actual_height = self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
                    logger.info(f"Actual camera resolution: {actual_width}x{actual_height}")
                    break
            
            self.camera_running = True
            self.master.after(0, self._camera_start_success)
            return True
        
        except Exception as e:
            logger.error(f"Error initializing camera: {e}")
            self.master.after(0, self._camera_start_failed, str(e))
            return False
    
    def _camera_start_success(self):
        """Called when camera starts successfully"""
        # Update buttons
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        
        # Show status
        self.show_status("Camera started successfully", "green")
        logger.info("Camera started successfully")
        
        # Show camera view, hide loading and error
        self.loading_frame.grid_remove()
        self.error_frame.grid_remove()
        self.camera_view.grid()
        
        # Start the camera processing loop in a background thread
        self.camera_thread = threading.Thread(target=self._camera_loop)
        self.camera_thread.daemon = True
        self.camera_thread.start()
        
        # Enable save button
        self.save_button.configure(state="normal")
        
        # In auto mode, update status with instructions
        if self.auto_mode:
            self.show_status("Face detection active. Stand in front of camera to mark attendance.", "green")
        else:
            # In manual mode, give manual instructions
            self.show_status("Camera started. Use the manual controls to mark attendance.", "blue")
            
            # Hide camera in manual mode if configured to do so
            if not self.show_camera_in_manual_mode:
                self.camera_view.grid_remove()
    
    def _camera_start_failed(self, error_message):
        """Called when camera fails to start"""
        # Update buttons
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        
        # Update status
        error_msg = f"Failed to start camera: {error_message}"
        self.show_status(error_msg, "red")
        logger.error(error_msg)
        
        # Show error message
        self.loading_frame.grid_remove()
        self.camera_view.grid_remove()
        
        self.error_message.configure(text=error_msg)
        self.error_frame.grid()
        
        # Clean up any resources
        if self.camera and self.camera.isOpened():
            self.camera.release()
            self.camera = None
        
        self.camera_running = False
    
    def _stop_camera(self):
        """Stop the camera feed"""
        try:
            # Set flag to stop the camera loop
            self.camera_running = False
        
        # Update UI
            self.show_status("Stopping camera...", "blue")
            logger.info("Stopping camera...")
            
            # Start cleanup in background thread to avoid UI freeze
            threading.Thread(target=self._stop_camera_thread, daemon=True).start()
        except Exception as e:
            logger.error(f"Error stopping camera: {e}")
            self.show_status(f"Error stopping camera: {e}", "red")
            
    def _stop_camera_thread(self):
        """Stop camera in a background thread"""
        try:
            # Release camera
            if self.camera and self.camera.isOpened():
                self.camera.release()
                self.camera = None
                
            # Update UI on main thread when done
            self.master.after(0, self._camera_stop_complete)
        except Exception as e:
            logger.error(f"Error in camera stop thread: {e}")
            self.master.after(0, lambda: self.show_status(f"Error stopping camera: {e}", "red"))
            
    def _camera_stop_complete(self):
        """Called when camera is fully stopped"""
        # Update buttons
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        
        # Update display
        self.camera_view.configure(text="Camera stopped")
        self.show_status("Camera stopped", "blue")
        
        self.camera_running = False
    
    def _camera_loop(self):
        """Process camera frames and detect faces"""
        last_fps_time = time.time()
        frame_count = 0
        
        try:
            # Main camera loop
            while self.camera_running:
                # Read frame from camera
                ret, frame = self.camera.read()
                
                if not ret:
                    self.failed_frames_count += 1
                    
                    # If we've failed to read frames multiple times, camera may be disconnected
                    if self.failed_frames_count > 10:
                        logger.error("Failed to read from camera multiple times")
                        # Properly reset the camera in the main thread
                        if self.winfo_exists():
                            self.after(0, lambda: self.show_status("Camera disconnected. Try restarting.", "red"))
                            self.after(0, self._stop_camera)
                        break
                    
                    # Wait a bit before trying again
                    time.sleep(0.1)
                    continue
                
                # Reset failed frames counter on success
                self.failed_frames_count = 0
                
                # Calculate FPS
                frame_count += 1
                current_time = time.time()
                elapsed = current_time - last_fps_time
                
                if elapsed >= 1.0:
                    fps = frame_count / elapsed
                    frame_count = 0
                    last_fps_time = current_time
                    
                    # Update FPS in the main thread - with widget existence check
                    if self.winfo_exists() and hasattr(self, 'fps_label') and self.fps_label.winfo_exists():
                        self.after(0, lambda f=fps: self._safe_update_fps(f))
                
                # Process frame
                try:
                    frame = cv2.flip(frame, 1)  # Mirror for more intuitive display
                    
                    # Convert BGR to RGB for display
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    
                    # Detect faces in the frame
                    display_frame = rgb_frame.copy()
                    
                    # Use face detector to detect and recognize faces
                    if self.face_detector:
                        # Detect faces
                        faces = self.face_detector.detect_faces(rgb_frame)
                        
                        # Process each detected face
                        for (x, y, w, h) in faces:
                            # Draw rectangle around the face
                            cv2.rectangle(display_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                            
                            # Extract face image for recognition
                            face_img = rgb_frame[y:y+h, x:x+w]
                            
                            # Add text background for better readability
                            text_y = y - 10 if y - 10 > 10 else y + h + 10
                            
                            # Attempt to recognize face if recognizer is available and trained
                            if self.face_detector._is_recognizer_trained:
                                # Try to recognize the face
                                student_id, confidence = self.face_detector.recognize_face(face_img)
                                
                                # If recognized with high confidence
                                if confidence < 100 - (self.confidence_threshold * 100):  # Convert to distance
                                    # Get student name from ID
                                    student_name = self.face_detector.get_student_name(student_id)
                                    
                                    # Add text with confidence
                                    conf_text = f"{student_name} ({100-confidence:.1f}%)"
                                    
                                    # Draw text background
                                    text_size = cv2.getTextSize(conf_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
                                    cv2.rectangle(display_frame, 
                                                (x, text_y - 25), 
                                                (x + text_size[0], text_y + 5), 
                                                (0, 200, 0), 
                                                -1)
                                    
                                    # Draw text
                                    cv2.putText(display_frame, conf_text, (x, text_y),
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                                    
                                    # Mark attendance if not already detected
                                    self._mark_attendance(student_id, student_name)
                                else:
                                    # Unknown face
                                    # Draw text background
                                    text_size = cv2.getTextSize("Unknown", cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
                                    cv2.rectangle(display_frame, 
                                                (x, text_y - 25), 
                                                (x + text_size[0], text_y + 5), 
                                                (0, 0, 200), 
                                                -1)
                                    
                                    # Draw text
                                    cv2.putText(display_frame, "Unknown", (x, text_y),
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                            else:
                                # If recognizer is not trained, just show that a face was detected
                                text = "Face Detected (No Training Data)"
                                
                                # Draw text background
                                text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
                                cv2.rectangle(display_frame, 
                                            (x, text_y - 25), 
                                            (x + text_size[0], text_y + 5), 
                                            (200, 100, 0), 
                                            -1)
                                
                                # Draw text
                                cv2.putText(display_frame, text, (x, text_y),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    
                    # Check if widget still exists before accessing
                    if not self.winfo_exists() or not hasattr(self, 'camera_view') or not self.camera_view.winfo_exists():
                        logger.info("Camera view no longer exists, stopping camera loop")
                        break
                        
                    # Resize frame to fit in the camera view
                    target_width = self.camera_view.winfo_width() or 640
                    target_height = self.camera_view.winfo_height() or 480
                    img = Image.fromarray(display_frame)
                    
                    # Use safe resize method
                    img = self._safe_resize_image(img, target_width, target_height)
                    
                    # Create CTkImage with the actual image size to prevent errors
                    actual_width, actual_height = img.size
                    ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(actual_width, actual_height))
                    
                    # Update label in main thread safely
                    if self.winfo_exists():
                        self.after(0, lambda i=ctk_img: self._update_camera_view(i))
                    
                except Exception as e:
                    logger.error(f"Error processing camera frame: {e}")
                    if self.winfo_exists():
                        self.after(0, lambda e=str(e): self.show_status(f"Error processing frame: {e}", "red"))
                
                # Short delay to reduce CPU usage
                time.sleep(0.01)
        
        except Exception as e:
            logger.error(f"Error in camera loop: {e}")
            if self.winfo_exists():
                self.after(0, lambda e=str(e): self.show_status(f"Camera error: {e}", "red"))
        
        finally:
            logger.info("Camera loop exited")
    
    def _safe_update_fps(self, fps):
        """Safely update FPS label with existence check"""
        try:
            if hasattr(self, 'fps_label') and self.fps_label.winfo_exists():
                self.fps_label.configure(text=f"FPS: {fps:.1f}")
        except Exception as e:
            logger.error(f"Error updating FPS: {e}")
    
    def _update_camera_view(self, image_obj):
        """Update the camera view with the new image (run in main thread)"""
        try:
            # Keep a reference to the image to prevent garbage collection
            # Store in class instance variable rather than widget attribute
            self._current_image_ref = image_obj
            
            # Update the image in the label, with existence check
            if hasattr(self, 'camera_view') and self.camera_view and self.camera_view.winfo_exists() and image_obj:
                self.camera_view.configure(image=image_obj)
        except Exception as e:
            logger.error(f"Error updating camera view: {e}")
    
    def _add_manual_attendance(self):
        """Add a student to attendance list manually from selection"""
        try:
            # Get selected item
            selected_items = self.student_tree.selection()
            if not selected_items:
                messagebox.showinfo("Selection Required", "Please select a student from the list.")
                return
            
            # Get student info from selected item
            student_id, name = self.student_tree.item(selected_items[0], 'values')
            
            # Check if already in attendance list
            if student_id in self.detected_faces:
                messagebox.showinfo("Already Marked", f"Student {name} (ID: {student_id}) is already marked present.")
                return
            
            # Add to attendance
            self.detected_faces.add(student_id)
            current_time = datetime.now().strftime("%H:%M:%S")
                
            # Add to attendance list
            self.attendance_list.append({
                "id": student_id,
                "name": name,
                "time": current_time
            })
            
            # Add to treeview
            self.tree.insert("", "end", values=(student_id, name, current_time))
            
            # Update tag in student list
            self.student_tree.item(selected_items[0], tags=('present',))
            
            # Enable save button if this is the first entry
            if len(self.attendance_list) == 1:
                self.save_button.configure(state="normal")
        
            # Show success message
            self.show_status(f"Added {name} to attendance", "green")
            
        except Exception as e:
            logger.error(f"Error adding manual attendance: {e}")
            messagebox.showerror("Error", f"Failed to add attendance: {e}")
    
    def _clear_attendance(self):
        """Clear all attendance records"""
        try:
            # Check if there are records to clear
            if not self.attendance_list:
                messagebox.showinfo("No Records", "There are no attendance records to clear.")
                return
            
            # Ask for confirmation
            if not messagebox.askyesno("Confirm", "Are you sure you want to clear all attendance records?"):
                return
            
            # Clear attendance data
            self.attendance_list.clear()
            self.detected_faces.clear()
            
            # Clear treeview
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Reset tags in student tree
            for item in self.student_tree.get_children():
                self.student_tree.item(item, tags=())
            
            # Disable save button
            self.save_button.configure(state="disabled")
            
            # Show success message
            self.show_status("Attendance records cleared", "green")
            
        except Exception as e:
            logger.error(f"Error clearing attendance: {e}")
            messagebox.showerror("Error", f"Failed to clear attendance: {e}")
            
    def _save_attendance(self):
        """Save attendance records to a file"""
        try:
            # Check if there are records to save
            if not self.attendance_list:
                messagebox.showinfo("No Records", "There are no attendance records to save.")
                return
            
            # Get subject and current date
            subject = self.subject_var.get()
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            # Create filename
            filename = f"Attendance_{subject}_{current_date}.csv"
            
            # Ensure directory exists
            os.makedirs("Attendance", exist_ok=True)
            filepath = os.path.join("Attendance", filename)
            
            # Write to CSV
            with open(filepath, 'w', newline='') as csvfile:
                fieldnames = ['ID', 'Name', 'Time', 'Date']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for record in self.attendance_list:
                    writer.writerow({
                        'ID': record['id'],
                        'Name': record['name'],
                        'Time': record['time'],
                        'Date': current_date
                    })
            
            # Show success message
            self.show_status(f"Attendance saved to {filename}", "green")
            messagebox.showinfo("Success", f"Attendance records saved to {filename}")
            
        except Exception as e:
            logger.error(f"Error saving attendance: {e}")
            messagebox.showerror("Error", f"Failed to save attendance: {e}")
            raise
    
    def reset_attendance(self):
        """Reset attendance list and detected faces"""
        # Clear attendance list
        self.attendance_list = []
        self.detected_faces = set()
        
        # Clear treeview
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Disable save button
        self.save_button.configure(state="disabled")
        
        logger.info("Attendance list reset")
    
    def _safe_resize_image(self, image, target_width, target_height):
        """Safely resize an image to fit within the target dimensions while maintaining aspect ratio"""
        try:
            # Get current dimensions
            width, height = image.size
        
            # Calculate aspect ratios
            aspect = width / height
            target_aspect = target_width / target_height
            
            # Determine new dimensions keeping aspect ratio
            if aspect > target_aspect:
                # Image is wider than target
                new_width = target_width
                new_height = int(target_width / aspect)
            else:
                # Image is taller than target
                new_height = target_height
                new_width = int(target_height * aspect)
            
            # Ensure dimensions are at least 1 pixel
            new_width = max(1, new_width)
            new_height = max(1, new_height)
            
            # Perform resize with LANCZOS for better quality
            return image.resize((new_width, new_height), Image.LANCZOS)
        except Exception as e:
            logger.error(f"Error resizing image: {e}")
            # If resize fails, return original image
            return image
    
    def show_status(self, message, color="black"):
        """Show a status message with the given color"""
        try:
            if hasattr(self, 'status_label') and self.status_label.winfo_exists():
                self.status_label.configure(text=message, text_color=color)
            logger.info(message)
        except Exception as e:
            logger.error(f"Error showing status: {e}")
    
    def cleanup(self):
        """Clean up resources before closing"""
        try:
            # Set flag to stop the camera loop and prevent further callbacks
            self.camera_running = False
            
            # Stop any scheduled after calls - cancel all tracked after_ids
            if hasattr(self, 'after_ids'):
                for after_id in self.after_ids:
                    try:
                        self.after_cancel(after_id)
                    except Exception as e:
                        logger.error(f"Error canceling after ID {after_id}: {e}")
                # Clear the list
                self.after_ids = []
            
            # Stop camera directly without callbacks
            if self.camera and hasattr(self.camera, 'isOpened') and self.camera.isOpened():
                try:
                    self.camera.release()
                except Exception as e:
                    logger.error(f"Error releasing camera during cleanup: {e}")
                finally:
                    self.camera = None
            
            logger.info("Attendance view resources cleaned up")
            
            # Allow normal destroy
            return True
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return True  # Still allow destroy

    def _create_loading_indicator(self, parent):
        """Create a loading animation indicator"""
        loading_container = ctk.CTkFrame(parent, fg_color="transparent")
        
        # Create a progress spinner
        progress = ctk.CTkProgressBar(loading_container, width=100, height=10, mode="indeterminate")
        progress.pack(pady=(0, 10))
        progress.start()
        
        # Loading text
        loading_text = ctk.CTkLabel(
            loading_container,
            text="Starting camera...",
            font=ctk.CTkFont(size=14)
        )
        loading_text.pack()
        
        return loading_container

    def _setup_event_handlers(self):
        """Set up event handlers for buttons and other interactive elements"""
        # Add event handlers to buttons here
        self.start_button.configure(command=self._start_camera)
        self.stop_button.configure(command=self._stop_camera)
        self.mode_button.configure(command=self._toggle_mode)
        self.save_button.configure(command=self._save_attendance)
        self.clear_button.configure(command=self._clear_attendance)
        
        # Handle window close event
        if hasattr(self.master, "protocol"):
            self.master.protocol("WM_DELETE_WINDOW", self.cleanup)

    def _add_new_subject(self):
        """Show dialog to add a new subject"""
        # Create a dialog window
        dialog = ctk.CTkToplevel(self)
        dialog.title("Add New Subject")
        dialog.geometry("400x200")
        dialog.transient(self)
        dialog.grab_set()  # Make dialog modal
        
        # Center the dialog
        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - dialog.winfo_width()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        
        # Add form elements
        frame = ctk.CTkFrame(dialog)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Subject ID (optional)
        id_label = ctk.CTkLabel(frame, text="Subject ID (optional):")
        id_label.pack(anchor="w", pady=(0, 5))
        
        id_entry = ctk.CTkEntry(frame, placeholder_text="Enter subject ID")
        id_entry.pack(fill="x", pady=(0, 10))
        
        # Subject Name
        name_label = ctk.CTkLabel(frame, text="Subject Name:")
        name_label.pack(anchor="w", pady=(0, 5))
        
        name_entry = ctk.CTkEntry(frame, placeholder_text="Enter subject name")
        name_entry.pack(fill="x", pady=(0, 20))
        name_entry.focus_set()  # Focus on name entry
        
        # Buttons
        button_frame = ctk.CTkFrame(frame, fg_color="transparent")
        button_frame.pack(fill="x")
        
        # Cancel button
        cancel_button = ctk.CTkButton(
            button_frame, 
            text="Cancel",
            fg_color="gray",
            command=dialog.destroy
        )
        cancel_button.pack(side="left", padx=(0, 10))
        
        # Add button
        def add_subject():
            subject_name = name_entry.get().strip()
            if not subject_name:
                messagebox.showerror("Error", "Subject name cannot be empty")
                return
                
            # Add to subject list
            self.subjects.append(subject_name)
            self.subjects.sort()  # Sort alphabetically
            
            # Update dropdown
            self.subject_dropdown.configure(values=self.subjects)
            self.subject_dropdown.set(subject_name)
            
            # Save to config if available
            try:
                if hasattr(self, 'config') and self.config is not None:
                    self.config.set("courses", self.subjects)
                    self.config.save()
                    logger.info(f"Added subject '{subject_name}' to configuration")
            except Exception as e:
                logger.error(f"Error saving subject to config: {e}")
                
            # Close dialog
            dialog.destroy()
            
            # Update status
            self.show_status(f"Added new subject: {subject_name}", "green")
        
        add_button = ctk.CTkButton(
            button_frame, 
            text="Add Subject",
            command=add_subject
        )
        add_button.pack(side="right")
        
        # Handle Enter key
        dialog.bind("<Return>", lambda event: add_subject())
        dialog.bind("<Escape>", lambda event: dialog.destroy())

    def _mark_attendance(self, student_id, student_name):
        """Mark attendance for a student if not already detected"""
        if not isinstance(student_id, str):
            student_id = str(student_id)  # Convert to string for consistency
            
        if student_id not in self.detected_faces:
            self.detected_faces.add(student_id)
            
            # Create attendance record
            attendance_record = {
                "id": student_id,
                "name": student_name,
                "subject": self.subject_var.get(),
                "time": datetime.now().strftime('%H:%M:%S'),
                "date": datetime.now().strftime('%Y-%m-%d')
            }
            
            # Add to attendance list
            self.attendance_list.append(attendance_record)
            
            # Update treeview
            self.tree.insert("", "end", values=(
                student_id, 
                student_name, 
                self.subject_var.get(),
                datetime.now().strftime('%H:%M:%S')
            ))
            
            logger.info(f"Marked attendance for {student_name} (ID: {student_id})")
            
            # Enable save button if this is the first entry
            if len(self.attendance_list) == 1:
                self.save_button.configure(state="normal")
                
            # Show status message
            self.show_status(f"Attendance marked for {student_name} (ID: {student_id})", "green")
            
            return True
        return False

    def after(self, ms, func=None, *args):
        """Override after to track IDs for cleanup"""
        if func is not None:
            after_id = super().after(ms, func, *args)
            self.after_ids.append(after_id)
            return after_id
        return super().after(ms)