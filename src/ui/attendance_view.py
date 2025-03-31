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
import traceback

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
        
        # Initialize logger
        self.logger = logger  # Use the module-level logger
        
        self.master = master
        self.config = config
        
        # Initialize configuration
        config = ConfigManager().get_config()
        self.attendance_dir = os.path.join(os.getcwd(), config.get("paths", {}).get("attendance_dir", "data/attendance"))
        self.models_dir = os.path.join(os.getcwd(), config.get("paths", {}).get("models_dir", "models"))
        self.students_file = os.path.join(os.getcwd(), config.get("paths", {}).get("students_file", "data/students.csv"))
        
        # Create attendance directory if it doesn't exist
        os.makedirs(self.attendance_dir, exist_ok=True)
        
        # Detection settings
        self.face_detection_threshold = config.get("face_recognition", {}).get("detection_threshold", 0.6)
        self.logger.info(f"Face detection threshold set to {self.face_detection_threshold}")
        
        # Initialize face recognizer
        self.face_recognizer = cv2.face.LBPHFaceRecognizer_create()
        
        # Load the face recognizer model if it exists
        self.recognizer_model_path = os.path.join(self.models_dir, "face_recognizer.yml")
        self.has_recognition_model = os.path.exists(self.recognizer_model_path)
        
        if self.has_recognition_model:
            try:
                self.face_recognizer.read(self.recognizer_model_path)
                self.logger.info(f"Loaded face recognition model from {self.recognizer_model_path}")
            except Exception as e:
                self.logger.error(f"Error loading face recognition model: {e}")
                self.has_recognition_model = False
        else:
            self.logger.warning(f"No face recognition model found at {self.recognizer_model_path}")
        
        # Load student data
        self.students = {}
        self.load_students()
        
        # Initialize camera variables
        self.camera = None
        self.camera_loop_running = False
        self.camera_thread = None
        self.current_frame = None
        self.last_processed_time = 0
        self.fps = 0
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # UI Elements
        self.camera_running = False
        self.attendance_mode = "auto"  # "auto" or "manual"
        self.current_frame_image = None
        self.camera_label = None
        self.status_message = None
        self.marked_students = set()
        
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
        
        # Bind resize event
        self.bind("<Configure>", self._on_resize)
        
        logger.info("Attendance View initialized")
    
    def _setup_ui(self):
        """Set up the attendance view UI components"""
        # Configure grid - all rows and columns should expand proportionally
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Header - fixed height
        self.grid_rowconfigure(1, weight=0)  # Settings - fixed height
        self.grid_rowconfigure(2, weight=1)  # Content - expandable
        self.grid_rowconfigure(3, weight=0)  # Status bar - fixed height
        
        # Create header section
        self._create_header()
        
        # Create settings section
        self._create_settings_panel()
        
        # Create main content area
        self._create_main_content()
        
        # Create status bar
        self._create_status_bar()
    
    def _create_header(self):
        """Create header with title and description"""
        header_frame = ctk.CTkFrame(self, corner_radius=8)
        header_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        
        # Try to get icon
        icon = None
        try:
            if hasattr(self.master, "icons"):
                icon = self.master.icons.get_icon("attendance", size=(32, 32))
        except Exception as e:
            logger.error(f"Error loading icon: {e}")
        
        # Title with icon
        title_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_frame.pack(fill="x", padx=20, pady=(15, 10))
        
        if icon:
            icon_label = ctk.CTkLabel(title_frame, image=icon, text="")
            icon_label.pack(side="left", padx=(0, 10))
            
        title_label = ctk.CTkLabel(
            title_frame, 
            text="Attendance Management", 
            font=ctk.CTkFont(size=22, weight="bold")
        )
        title_label.pack(side="left", fill="x")
        
        # Description
        description = ctk.CTkLabel(
            header_frame,
            text="Record and manage student attendance using face recognition",
            font=ctk.CTkFont(size=14),
            text_color=("gray50", "gray70")
        )
        description.pack(fill="x", padx=20, pady=(0, 15))
    
    def _create_settings_panel(self):
        """Create settings panel with controls"""
        settings_frame = ctk.CTkFrame(self, corner_radius=8)
        settings_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        settings_frame.grid_columnconfigure(4, weight=1)
        
        # Subject selection
        subject_label = ctk.CTkLabel(settings_frame, text="Subject:")
        subject_label.grid(row=0, column=0, padx=(20, 5), pady=(15, 5), sticky="w")
        
        # Create a combobox for subjects
        subjects = self._get_subjects()
        self.subject_var = ctk.StringVar(value=subjects[0] if subjects else "General")
        
        self.subject_menu = ctk.CTkOptionMenu(
            settings_frame,
            values=subjects,
            variable=self.subject_var,
            width=180
        )
        self.subject_menu.grid(row=0, column=1, padx=5, pady=(15, 5), sticky="w")
        
        # Add subject button
        add_subject_button = ctk.CTkButton(
            settings_frame,
            text="+",
            width=30,
            command=self._add_new_subject
        )
        add_subject_button.grid(row=0, column=2, padx=5, pady=(15, 5), sticky="w")
        
        # Mode toggle
        mode_label = ctk.CTkLabel(settings_frame, text="Mode:")
        mode_label.grid(row=0, column=3, padx=(20, 5), pady=(15, 5), sticky="w")
        
        self.mode_var = ctk.StringVar(value="Auto")
        self.mode_button = ctk.CTkButton(
            settings_frame,
            text="Auto Recognition",
            width=150,
            command=self._toggle_mode
        )
        self.mode_button.grid(row=0, column=4, padx=5, pady=(15, 5), sticky="w")
        
        # Divider
        divider = ctk.CTkFrame(settings_frame, height=1, fg_color=("gray80", "gray30"))
        divider.grid(row=1, column=0, columnspan=6, padx=20, pady=(10, 5), sticky="ew")
        
        # Camera controls
        camera_label = ctk.CTkLabel(settings_frame, text="Camera Control:")
        camera_label.grid(row=2, column=0, padx=(20, 5), pady=10, sticky="w")
        
        # Try to get icons
        camera_icon = None
        manual_icon = None
        try:
            if hasattr(self.master, "icons"):
                camera_icon = self.master.icons.get_icon("capture", size=(20, 20))
                manual_icon = self.master.icons.get_icon("edit", size=(20, 20))
        except Exception as e:
            logger.error(f"Error loading icons: {e}")
        
        # Camera button
        self.camera_button = ctk.CTkButton(
            settings_frame,
            text="Start Camera",
            image=camera_icon,
            compound="left",
            width=150,
            command=self._start_camera
        )
        self.camera_button.grid(row=2, column=1, padx=5, pady=10, sticky="w")
        
        # Manual attendance button
        self.manual_button = ctk.CTkButton(
            settings_frame,
            text="Add Manual",
            image=manual_icon,
            compound="left",
            width=150,
            command=self._add_manual_attendance
        )
        self.manual_button.grid(row=2, column=2, columnspan=2, padx=5, pady=10, sticky="w")
        
        # Right-aligned buttons
        button_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        button_frame.grid(row=2, column=4, padx=(20, 20), pady=10, sticky="e")
        
        # Create manual frame (hidden by default)
        self.manual_frame = ctk.CTkFrame(settings_frame)
        self.manual_frame.grid(row=3, column=0, columnspan=5, padx=20, pady=10, sticky="ew")
        self.manual_frame.grid_columnconfigure(0, weight=1)
        
        # Manual student entry
        student_entry_frame = ctk.CTkFrame(self.manual_frame, fg_color="transparent")
        student_entry_frame.pack(fill="x", padx=10, pady=10)
        
        # Student ID Entry
        id_label = ctk.CTkLabel(student_entry_frame, text="Student ID:")
        id_label.pack(side="left", padx=(0, 5))
        
        self.student_id_entry = ctk.CTkEntry(student_entry_frame, width=100)
        self.student_id_entry.pack(side="left", padx=(0, 15))
        
        # Student Name Entry
        name_label = ctk.CTkLabel(student_entry_frame, text="Name:")
        name_label.pack(side="left", padx=(0, 5))
        
        self.student_name_entry = ctk.CTkEntry(student_entry_frame, width=150)
        self.student_name_entry.pack(side="left", padx=(0, 15))
        
        # Manual add button
        add_button = ctk.CTkButton(
            student_entry_frame,
            text="Add",
            width=80,
            command=self._manual_mark_attendance
        )
        add_button.pack(side="left")
        
        # Hide the manual frame initially
        self.manual_frame.grid_remove()
        
        # Save button (initially disabled)
        self.save_button = ctk.CTkButton(
            button_frame,
            text="Save Attendance",
            state="disabled",
            command=self._save_attendance
        )
        self.save_button.pack(side="left", padx=(0, 10))
        
        # Clear button
        self.clear_button = ctk.CTkButton(
            button_frame,
            text="Clear",
            fg_color=("gray70", "gray30"),
            command=self._clear_attendance
        )
        self.clear_button.pack(side="left")
    
    def _create_main_content(self):
        """Create the main content section with camera view and attendance list"""
        # Main content container with camera view and attendance list
        content_frame = ctk.CTkFrame(self)
        content_frame.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="nsew")
        
        # Configure the grid layout for proper spacing and resizing
        content_frame.grid_columnconfigure(0, weight=2)  # Camera view gets 2/5 of space
        content_frame.grid_columnconfigure(1, weight=3)  # Attendance list gets 3/5 of space
        content_frame.grid_rowconfigure(0, weight=1)  # Both rows expand equally

        # Camera View - left side
        camera_frame = ctk.CTkFrame(content_frame, corner_radius=10)
        camera_frame.grid(row=0, column=0, padx=(0, 10), pady=0, sticky="nsew")
        camera_frame.grid_columnconfigure(0, weight=1)
        camera_frame.grid_rowconfigure(0, weight=0)  # Title
        camera_frame.grid_rowconfigure(1, weight=1)  # Camera container

        # Camera title and icon
        camera_header = ctk.CTkFrame(camera_frame, fg_color="transparent")
        camera_header.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        
        camera_title = ctk.CTkLabel(
            camera_header, 
            text="Camera Feed",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        camera_title.pack(side="left", padx=10)
        
        # FPS counter
        self.fps_label = ctk.CTkLabel(
            camera_header,
            text="FPS: 0",
            font=ctk.CTkFont(size=12),
            text_color=("gray50", "gray70")
        )
        self.fps_label.pack(side="right", padx=10)
        
        # Camera container - fixed size wrapper to maintain aspect ratio
        camera_container = ctk.CTkFrame(camera_frame, fg_color="transparent", width=640, height=480)
        camera_container.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        camera_container.grid_propagate(False)  # Prevent resizing with contents
        camera_container.grid_columnconfigure(0, weight=1)
        camera_container.grid_rowconfigure(0, weight=1)
        
        # Create black background for camera view
        bg_color = "black" if self.get_appearance_mode() == "Dark" else "#333333"
        
        # Create camera label for displaying the feed
        self.camera_label = ctk.CTkLabel(
            camera_container, 
            text="Camera feed will appear here",
            fg_color=bg_color,
            text_color="white",
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=5
        )
        self.camera_label.grid(row=0, column=0, sticky="nsew")

        # Attendance List - right side
        attendance_frame = ctk.CTkFrame(content_frame, corner_radius=10)
        attendance_frame.grid(row=0, column=1, padx=(10, 0), pady=0, sticky="nsew")
        attendance_frame.grid_columnconfigure(0, weight=1)
        attendance_frame.grid_rowconfigure(0, weight=0)  # Title
        attendance_frame.grid_rowconfigure(1, weight=1)  # Treeview

        # Attendance title
        attendance_title = ctk.CTkLabel(
            attendance_frame, 
            text="Attendance Records",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        attendance_title.grid(row=0, column=0, padx=20, pady=(10, 5), sticky="w")

        # Create frame for the treeview
        tree_frame = ctk.CTkFrame(attendance_frame, fg_color="transparent")
        tree_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)

        # Treeview styling
        style = ttk.Style()
        if self.get_appearance_mode() == "Dark":
            style.configure("Treeview", 
                background="#2b2b2b", 
                foreground="white", 
                fieldbackground="#2b2b2b",
                borderwidth=0)
            style.map('Treeview', background=[('selected', '#1f538d')])
        else:
            style.configure("Treeview", 
                background="#f9f9f9", 
                foreground="black", 
                fieldbackground="#f9f9f9",
                borderwidth=0)
            style.map('Treeview', background=[('selected', '#3a7ebf')])

        # Create scrollable treeview for attendance list
        self.tree = ttk.Treeview(
            tree_frame,
            columns=("id", "name", "time", "confidence"),
            show="headings",
            style="Treeview"
        )
        self.tree.grid(row=0, column=0, sticky="nsew")

        # Add scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Configure columns
        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="Name")
        self.tree.heading("time", text="Time")
        self.tree.heading("confidence", text="Confidence")
        
        self.tree.column("id", width=80, anchor="center")
        self.tree.column("name", width=150, anchor="w")
        self.tree.column("time", width=100, anchor="center")
        self.tree.column("confidence", width=100, anchor="center")

        # Create the manual attendance frame but hide it initially
        self.manual_frame = self._create_manual_frame(attendance_frame)
        self.manual_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.manual_frame.grid_remove()  # Initially hidden
    
    def _create_status_bar(self):
        """Create status bar at the bottom"""
        # Status bar
        self.status_frame = ctk.CTkFrame(self, height=30, corner_radius=0)
        self.status_frame.grid(row=3, column=0, sticky="ew")
        
        # Status label
        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="Ready",
            font=ctk.CTkFont(size=13),
            anchor="w"
        )
        self.status_label.pack(side="left", padx=20, pady=5, fill="x")
    
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
            if self.attendance_mode == "auto":
                self.attendance_mode = "manual"
                
                # Update button appearance
                self.mode_button.configure(
                    text="Manual Mode", 
                    fg_color=("#e67e22", "#d35400")  # Orange
                )
                
                # Show status
                self.show_status("Manual mode enabled - enter student details manually", "blue")
                
                # Show manual entry frame
                if hasattr(self, 'manual_frame'):
                    self.manual_frame.grid()
                    
                    # Set focus to the ID field
                    if hasattr(self, 'student_id_entry'):
                        self.student_id_entry.focus_set()
            else:
                self.attendance_mode = "auto"
                
                # Update button appearance
                self.mode_button.configure(
                    text="Auto Recognition", 
                    fg_color=("#3498db", "#2980b9")  # Blue
                )
                
                # Show status
                self.show_status("Auto recognition mode enabled", "blue")
                
                # Hide manual entry frame
                if hasattr(self, 'manual_frame'):
                    self.manual_frame.grid_remove()
            
            self.logger.info(f"Attendance mode toggled to {self.attendance_mode}")
            
        except Exception as e:
            self.logger.error(f"Error toggling mode: {e}")
            self.show_status(f"Error: {e}", "red")
    
    def _start_camera(self):
        """Start the camera for attendance tracking"""
        try:
            if self.camera_running:
                logger.info("Camera is already running")
                return
            
            # Update UI
            self.camera_button.configure(state="disabled")
            
            # Show loading animation
            if hasattr(self, 'loading_indicator'):
                self.loading_indicator.place(relx=0.5, rely=0.5, anchor="center")
                
            # Start camera in a separate thread
            self.camera_thread = threading.Thread(target=self._initialize_camera)
            self.camera_thread.daemon = True
            self.camera_thread.start()
            
            # Show status
            self.show_status("Starting camera...", "blue")
            
        except Exception as e:
            logger.error(f"Error starting camera: {e}")
            self.show_status(f"Error starting camera: {e}", "red")
            self._camera_start_failed(str(e))
    
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
        """Called when camera has been successfully initialized"""
        # Log the success
        logger.info("Camera started successfully with resolution: %sx%s", 
                  int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH)),
                  int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT)))
        
        # Update UI
        if hasattr(self, 'settings_panel') and hasattr(self.settings_panel, 'camera_button'):
            self.settings_panel.camera_button.configure(
                text="Stop Camera",
                fg_color=("#e74c3c", "#c0392b"),  # Red color for stop button
                command=self._stop_camera
            )
            
            # Enable camera-dependent buttons
            if hasattr(self.settings_panel, 'toggle_button'):
                self.settings_panel.toggle_button.configure(state="normal")
        else:
            # Fallback to the direct button if there's no settings panel
            if hasattr(self, 'camera_button'):
                self.camera_button.configure(
                    text="Stop Camera",
                    command=self._stop_camera,
                    state="normal"
                )
            
        # Show status
        self.show_status("Camera started successfully", "green")
        
        # Start camera processing loop in a background thread
        self.camera_thread = threading.Thread(target=self._camera_loop)
        self.camera_thread.daemon = True
        self.camera_thread.start()
        
        # Reset FPS counter
        self.last_fps_update = time.time()
        self.frame_count = 0
    
    def _camera_start_failed(self, error_message):
        """Camera initialization failed"""
        try:
            # Update button states
            self.camera_button.configure(text="Start Camera", command=self._start_camera)
            self.camera_button.configure(state="normal")
            
            # Hide loading indicator
            if hasattr(self, 'loading_indicator'):
                self.loading_indicator.place_forget()
            
            # Show error message
            self.show_status(f"Camera failed to start: {error_message}", "red")
            
            # Update flag
            self.camera_running = False
            
        except Exception as e:
            logger.error(f"Error updating UI after camera failure: {e}")
    
    def _stop_camera(self):
        """Stop the camera feed"""
        try:
            logger.info("Stopping camera...")
            
            # Set flag to stop camera loop
            self.camera_running = False
            
            # Without using a thread join (which could block UI)
            # we schedule camera resource cleanup after a short delay
            self.after(100, self._stop_camera_thread)
            
            # Disable camera button while stopping
            if hasattr(self, 'camera_button'):
                self.camera_button.configure(
                    text="Stopping...",
                    state="disabled"
                )
                
            return True
            
        except Exception as e:
            logger.error(f"Error stopping camera: {e}")
            return False
    
    def _stop_camera_thread(self):
        """Background thread to stop the camera"""
        try:
            # Wait for camera thread to finish
            if hasattr(self, 'camera_thread') and self.camera_thread.is_alive():
                self.camera_thread.join(timeout=3.0)
                
            # Release camera resources
            if self.camera and self.camera.isOpened():
                self.camera.release()
                self.camera = None
            
            # Update UI from main thread
            self.after(0, self._camera_stop_complete)
            
        except Exception as e:
            logger.error(f"Error in camera stop thread: {e}")
            self.after(0, lambda: self.show_status(f"Error stopping camera: {e}", "red"))
    
    def _camera_stop_complete(self):
        """Update UI after camera is stopped"""
        try:
            # Update buttons
            self.camera_button.configure(text="Start Camera", command=self._start_camera)
            self.camera_button.configure(state="normal")
            
            # Reset camera view
            if hasattr(self, 'camera_label'):
                self.camera_label.configure(text="Camera feed will appear here")
            
            # Update status
            self.show_status("Camera stopped", "blue")
            
            # Reset FPS counter
            if hasattr(self, 'fps_label'):
                self.fps_label.configure(text="0 FPS")
            
        except Exception as e:
            logger.error(f"Error updating UI after camera stop: {e}")
            self.show_status(f"Error: {e}", "red")
    
    def _camera_loop(self):
        """Process camera frames in the background thread"""
        try:
            # Counter for FPS calculation
            frame_count = 0
            last_time = time.time()
            
            # Main camera processing loop
            while self.camera_running and self.camera and self.camera.isOpened():
                # Read a frame
                ret, frame = self.camera.read()
                
                if not ret or frame is None:
                    self.logger.error("Failed to capture frame from camera")
                    time.sleep(0.1)
                    continue
                
                # Store current frame for processing
                current_frame = frame.copy()
                
                # Increment frame counter
                frame_count += 1
                
                # Calculate FPS every second
                elapsed_time = time.time() - last_time
                if elapsed_time >= 1.0:
                    fps = frame_count / elapsed_time
                    # Update FPS in main thread
                    self.after(0, lambda fps=fps: self._update_fps(fps))
                    # Reset counter
                    frame_count = 0
                    last_time = time.time()
                
                # Process the frame (face detection, etc.)
                processed_frame = self._process_frame(current_frame)
                
                # Update the UI in the main thread with the processed frame
                self.after(0, lambda frame=processed_frame: self._update_camera_view(frame))
                
                # Sleep to prevent excessive CPU usage (adjust as needed)
                time.sleep(0.03)  # ~30 FPS max
                
        except Exception as e:
            self.logger.error(f"Error in camera loop: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Ensure we update UI with camera stopped status
            self.logger.info("Camera loop exited")
            
            # Stop the camera if it's still running
            if self.camera:
                try:
                    self.camera.release()
                except:
                    pass
                self.camera = None
    
    def _update_fps(self, fps):
        """Safely update FPS label with existence check"""
        try:
            if hasattr(self, 'fps_label') and self.fps_label.winfo_exists():
                self.fps_label.configure(text=f"FPS: {fps:.1f}")
        except Exception as e:
            logger.error(f"Error updating FPS: {e}")
    
    def _update_camera_view(self, frame):
        """Update the camera view with a new frame"""
        try:
            # Check if view and camera label still exist
            if not self.winfo_exists() or not hasattr(self, 'camera_label') or not self.camera_label.winfo_exists():
                return
                
            if frame is None:
                logger.warning("Received None frame in _update_camera_view")
                return
                
            # Get current dimensions of the camera view
            width = self.camera_label.winfo_width() or 640
            height = self.camera_label.winfo_height() or 480
                
            # Convert the frame to PIL Image
            pil_image = Image.fromarray(frame)
                
            # Create CTkImage with the correct dimensions
            ctk_image = ctk.CTkImage(
                light_image=pil_image,
                dark_image=pil_image,
                size=(width, height)
            )
                
            # Update the camera label
            self.camera_label.configure(image=ctk_image, text="")
                
            # Store the current image to prevent garbage collection
            self.current_image = ctk_image

        except Exception as e:
            logger.error(f"Error updating camera view: {e}")
            traceback.print_exc()
    
    def _add_manual_attendance(self):
        """Add a student to attendance list manually from input fields"""
        try:
            # Check if manual frame exists and is visible
            if not hasattr(self, 'manual_frame') or not self.manual_frame.winfo_ismapped():
                # Show manual frame 
                self.attendance_mode = "manual"
                self._toggle_mode()  # This will toggle to manual mode and show the frame
                return
                
            # Get student details from entries
            student_id = self.manual_id_entry.get().strip() if hasattr(self, 'manual_id_entry') else ""
            student_name = self.manual_name_entry.get().strip() if hasattr(self, 'manual_name_entry') else ""
            
            # Validate input
            if not student_id:
                self.show_status("Please enter a Student ID", "red")
                # Focus the field
                if hasattr(self, 'manual_id_entry'):
                    self.manual_id_entry.focus_set()
                return
                
            if not student_name:
                self.show_status("Please enter a Student Name", "red")
                # Focus the field
                if hasattr(self, 'manual_name_entry'):
                    self.manual_name_entry.focus_set()
                return
            
            # Mark attendance
            self.mark_attendance(student_id, student_name)
            
            # Clear the input fields
            if hasattr(self, 'manual_id_entry'):
                self.manual_id_entry.delete(0, 'end')
            if hasattr(self, 'manual_name_entry'):
                self.manual_name_entry.delete(0, 'end')
            
            # Set focus back to ID field for next entry
            if hasattr(self, 'manual_id_entry'):
                self.manual_id_entry.focus_set()
            
            # Show success message
            self.show_status(f"Attendance marked for {student_name}", "green")
            
        except Exception as e:
            self.logger.error(f"Error adding manual attendance: {e}")
            import traceback
            traceback.print_exc()
            self.show_status(f"Error: {e}", "red")
    
    def _clear_attendance(self):
        """Clear the attendance records from the display and memory"""
        try:
            # Confirm before clearing
            result = messagebox.askyesno("Clear Attendance", "Are you sure you want to clear all attendance records?")
            if not result:
                return
                
            # Clear the attendance list
            self.attendance_list = []
            self.detected_faces = set()
            
            # Clear the tree if it exists
            if hasattr(self, 'tree') and self.tree is not None and self.tree.winfo_exists():
                # Get all items
                items = self.tree.get_children()
                
                # Delete all items
                for item in items:
                    self.tree.delete(item)
            
            # Disable save button
            if hasattr(self, 'save_button'):
                self.save_button.configure(state="disabled")
            
            # Show status
            self.show_status("Attendance records cleared", "blue")
            logger.info("Attendance records cleared")
            
        except Exception as e:
            logger.error(f"Error clearing attendance: {e}")
            self.show_status(f"Error clearing records: {e}", "red")
    
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
        """Clean up resources when view is closed"""
        try:
            # Stop camera if running
            if hasattr(self, 'camera_running') and self.camera_running:
                self._stop_camera()
                
            # Cancel any pending after calls
            if hasattr(self, 'after_ids'):
                for after_id in self.after_ids:
                    try:
                        self.after_cancel(after_id)
                    except Exception as e:
                        logger.error(f"Error canceling after ID {after_id}: {e}")
                        
                # Clear the list
                self.after_ids = []
                
            logger.info("Attendance view resources cleaned up")
            return True
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return False

    def _create_loading_indicator(self, parent):
        """Create an animated loading indicator"""
        try:
            # Create a frame for the loading animation
            loading_frame = ctk.CTkFrame(parent, fg_color="transparent")
            
            # Create animated loading label
            loading_label = ctk.CTkLabel(
                loading_frame,
                text="Loading...",
                font=ctk.CTkFont(size=16)
            )
            loading_label.pack(pady=10)
            
            # Create animated dots
            def animate_loading():
                if not hasattr(loading_label, 'dots'):
                    loading_label.dots = 0
                
                # Update dots
                loading_label.dots = (loading_label.dots + 1) % 4
                dots = "." * loading_label.dots
                loading_label.configure(text=f"Loading{dots:3}")
                
                # Continue animation if frame exists
                if loading_frame.winfo_exists():
                    self.after(300, animate_loading)
            
            # Start animation
            animate_loading()
            
            return loading_frame
            
        except Exception as e:
            logger.error(f"Error creating loading indicator: {e}")
            # Create a simple fallback indicator
            fallback = ctk.CTkLabel(parent, text="Loading...")
            return fallback

    def _setup_event_handlers(self):
        """Set up event handlers for buttons and other interactive elements"""
        # Add event handlers to buttons here
        if hasattr(self, 'camera_button'):
            self.camera_button.configure(command=self._start_camera)
        if hasattr(self, 'mode_button'):
            self.mode_button.configure(command=self._toggle_mode)
        if hasattr(self, 'save_button'):
            self.save_button.configure(command=self._save_attendance)
        if hasattr(self, 'clear_button'):
            self.clear_button.configure(command=self._clear_attendance)
        if hasattr(self, 'manual_button'):
            self.manual_button.configure(command=self._add_manual_attendance)
        
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
        """Mark attendance for a recognized student"""
        try:
            # Create today's attendance file
            today = datetime.now().strftime("%Y-%m-%d")
            attendance_file = os.path.join(self.attendance_dir, f"attendance_{today}.csv")
            
            # Get current time
            current_time = datetime.now().strftime("%H:%M:%S")
            
            # Create or append to the attendance file
            file_exists = os.path.exists(attendance_file)
            
            with open(attendance_file, 'a', newline='') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(['ID', 'Name', 'Time', 'Date'])
                writer.writerow([student_id, student_name, current_time, today])
            
            message = f"Attendance marked for {student_name} ({student_id})"
            self.logger.info(message)
            self._update_log(message)
            
            # Show a success message in the UI
            self.after(0, lambda: self._show_attendance_confirmation(student_name))
            
        except Exception as e:
            self.logger.error(f"Error marking attendance: {e}")
            self._update_log(f"Error marking attendance: {e}", level="error")

    def _show_notification(self, message, type="info"):
        """Show a temporary notification with animation"""
        # Show status in the status bar
        if type == "success":
            self.show_status(message, "green")
        elif type == "error":
            self.show_status(message, "red")
        elif type == "info":
            self.show_status(message, "blue")
        else:
            self.show_status(message)
        
        # Create floating notification
        try:
            # Colors based on notification type
            bg_colors = {
                "success": ("#4CAF50", "#2E7D32"),  # Green
                "error": ("#F44336", "#C62828"),    # Red
                "info": ("#2196F3", "#1565C0")      # Blue
            }
            bg_color = bg_colors.get(type, ("#757575", "#424242"))  # Gray default
            
            # Create notification frame
            notif_frame = ctk.CTkFrame(
                self, 
                corner_radius=8,
                fg_color=bg_color,
                width=300
            )
            
            # Calculate position (centered at the top)
            if hasattr(self, 'winfo_width') and self.winfo_width() > 0:
                x_pos = (self.winfo_width() - 300) // 2
                notif_frame.place(x=x_pos, y=10)
            else:
                notif_frame.place(relx=0.5, y=10, anchor="n")
            
            # Add icon based on type
            icons = {
                "success": "✓",
                "error": "✗",
                "info": "ℹ"
            }
            icon = icons.get(type, "•")
            
            # Create content with icon and text
            icon_label = ctk.CTkLabel(
                notif_frame,
                text=icon,
                font=ctk.CTkFont(size=18, weight="bold"),
                text_color="white"
            )
            icon_label.pack(side="left", padx=(15, 5), pady=10)
            
            text_label = ctk.CTkLabel(
                notif_frame,
                text=message,
                font=ctk.CTkFont(size=13),
                text_color="white"
            )
            text_label.pack(side="left", fill="x", expand=True, padx=(0, 15), pady=10)
            
            # Animation to fade in and out
            def fade_out(opacity=1.0):
                if opacity <= 0:
                    notif_frame.destroy()
                    return
                
                notif_frame.configure(fg_color=(
                    self._adjust_color_opacity(bg_color[0], opacity),
                    self._adjust_color_opacity(bg_color[1], opacity)
                ))
                self.after(50, lambda: fade_out(opacity - 0.1))
            
            # Auto-dismiss after delay
            self.after(2000, lambda: fade_out())
            
        except Exception as e:
            logger.error(f"Error showing notification: {e}")
    
    def _adjust_color_opacity(self, hex_color, opacity):
        """Adjust color opacity for animation effects"""
        try:
            # Parse hex color
            if hex_color.startswith('#'):
                hex_color = hex_color[1:]
            
            # Get RGB components
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            
            # Adjust for background color blending
            bg_color = self._get_bg_color()
            if bg_color.startswith('#'):
                bg_color = bg_color[1:]
                
            bg_r = int(bg_color[0:2], 16) if len(bg_color) >= 2 else 240
            bg_g = int(bg_color[2:4], 16) if len(bg_color) >= 4 else 240
            bg_b = int(bg_color[4:6], 16) if len(bg_color) >= 6 else 240
            
            # Blend with background based on opacity
            r = int(r * opacity + bg_r * (1 - opacity))
            g = int(g * opacity + bg_g * (1 - opacity))
            b = int(b * opacity + bg_b * (1 - opacity))
            
            # Convert back to hex
            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception as e:
            logger.error(f"Error adjusting color opacity: {e}")
            return hex_color

    def after(self, ms, func=None, *args):
        """Override after to track IDs for cleanup"""
        if func is not None:
            after_id = super().after(ms, func, *args)
            self.after_ids.append(after_id)
            return after_id
        return super().after(ms)

    def _manual_mark_attendance(self):
        """Mark attendance manually using the input fields"""
        try:
            # Get student details from entries
            student_id = self.student_id_entry.get().strip()
            student_name = self.student_name_entry.get().strip()
            
            # Validate input
            if not student_id:
                self.show_status("Please enter a Student ID", "red")
                # Focus the field
                if hasattr(self, 'student_id_entry'):
                    self.student_id_entry.focus_set()
                return
                
            if not student_name:
                self.show_status("Please enter a Student Name", "red")
                # Focus the field
                if hasattr(self, 'student_name_entry'):
                    self.student_name_entry.focus_set()
                return
            
            # Mark attendance
            self.mark_attendance(student_id, student_name)
            
            # Clear the input fields
            if hasattr(self, 'student_id_entry'):
                self.student_id_entry.delete(0, 'end')
            if hasattr(self, 'student_name_entry'):
                self.student_name_entry.delete(0, 'end')
            
            # Set focus back to ID field for next entry
            if hasattr(self, 'student_id_entry'):
                self.student_id_entry.focus_set()
            
            # Show success message
            self.show_status(f"Attendance marked for {student_name}", "green")
            
        except Exception as e:
            self.logger.error(f"Error marking manual attendance: {e}")
            import traceback
            traceback.print_exc()
            self.show_status(f"Error: {e}", "red")

    def _on_resize(self, event=None):
        """Handle resize events to update UI elements"""
        # Only process if it's our widget being resized, not a child widget
        if event and event.widget == self:
            # Allow some time for the resize to complete
            self.after_cancel_by_tag("resize") if hasattr(self, "after_cancel_by_tag") else None
            after_id = self.after(100, self._update_ui_after_resize)
            self.after_ids.append(after_id)
    
    def _update_ui_after_resize(self):
        """Update UI elements after resize"""
        try:
            # Update camera view size
            if hasattr(self, 'camera_label') and self.camera_label.winfo_exists():
                # Force camera view to take up available space
                self.camera_label.configure(width=self.camera_label.winfo_width())
                self.camera_label.configure(height=self.camera_label.winfo_height())
                
                # If camera is running, ensure the image is updated to match new size
                if self.camera_running and hasattr(self, '_current_image_ref'):
                    # The next camera frame will be resized appropriately
                    pass
                    
            # Adjust column widths in treeview
            if hasattr(self, 'tree') and self.tree.winfo_exists():
                tree_width = self.tree_frame.winfo_width() - 20  # Subtract scrollbar width
                if tree_width > 0:
                    # Calculate proportional widths
                    self.tree.column("id", width=int(tree_width * 0.15))
                    self.tree.column("name", width=int(tree_width * 0.35))
                    self.tree.column("time", width=int(tree_width * 0.2))
                    
        except Exception as e:
            logger.error(f"Error updating UI after resize: {e}")

    def _process_frame(self, frame):
        """Process a camera frame to detect and recognize faces"""
        try:
            if frame is None:
                return None
                
            # Make a copy of the frame for processing
            frame_copy = frame.copy()
            
            # Convert to grayscale for face detection
            gray = cv2.cvtColor(frame_copy, cv2.COLOR_BGR2RGB)
            gray_frame = cv2.cvtColor(gray, cv2.COLOR_RGB2GRAY)
            
            # Detect faces in the frame
            faces = self.face_cascade.detectMultiScale(
                gray_frame,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )
            
            # Process each detected face
            face_detected = False
            recognition_message = "No face detected"
            
            for (x, y, w, h) in faces:
                face_detected = True
                
                # Draw rectangle around face
                cv2.rectangle(frame_copy, (x, y), (x+w, y+h), (0, 255, 0), 2)
                
                # Check if we're in auto mode and have a recognition model
                if self.attendance_mode == "auto" and self.has_recognition_model:
                    try:
                        # Extract face for recognition
                        face_roi = gray_frame[y:y+h, x:x+w]
                        face_roi = cv2.resize(face_roi, (100, 100))
                        
                        # Perform face recognition
                        label_id, confidence = self.face_recognizer.predict(face_roi)
                        
                        # Lower confidence is better in LBPH (convert to a percentage)
                        recognition_confidence = 100 - confidence
                        threshold = self.face_detection_threshold * 100
                        
                        self.logger.info(f"Recognition confidence: {recognition_confidence:.1f}%, threshold: {threshold:.1f}%")
                        
                        if recognition_confidence >= threshold:
                            # Try to get student info based on the recognized label
                            student_info = self.get_student_by_id(str(label_id))
                            
                            if student_info:
                                student_id, student_name = student_info
                                recognition_message = f"Recognized: {student_name} ({student_id})"
                                
                                # Add text to the frame
                                cv2.putText(frame_copy, student_name, (x, y-10), 
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                                
                                # Mark attendance for this student if not already marked
                                if student_id not in self.marked_students:
                                    self.logger.info(f"Marking attendance for student: {student_name} ({student_id})")
                                    self.mark_attendance(student_id, student_name)
                                    self.marked_students.add(student_id)
                                    # Flash effect to indicate attendance marking
                                    self.after(0, lambda: self._flash_attendance_marked())
                            else:
                                recognition_message = f"Unknown Student (ID: {label_id})"
                                cv2.putText(frame_copy, "Unknown", (x, y-10), 
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                        else:
                            recognition_message = f"Low confidence: {recognition_confidence:.1f}%"
                            cv2.putText(frame_copy, "Low confidence", (x, y-10), 
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                    except Exception as e:
                        self.logger.error(f"Error in face recognition: {e}")
                        recognition_message = "Recognition error"
                else:
                    # In manual mode, just show face detected
                    recognition_message = "Face detected (Manual mode)"
                    cv2.putText(frame_copy, "Face Detected", (x, y-10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)
            
            # Update status message
            self.after(0, lambda msg=recognition_message: self._update_status(msg))
            
            return frame_copy
            
        except Exception as e:
            self.logger.error(f"Error processing frame: {e}")
            import traceback
            traceback.print_exc()
            return frame
    
    def get_student_by_id(self, student_id):
        """Get student information by ID"""
        return self.students.get(student_id)
    
    def load_students(self):
        """Load student data from CSV file"""
        try:
            if os.path.exists(self.students_file):
                import pandas as pd
                df = pd.read_csv(self.students_file)
                for _, row in df.iterrows():
                    # Store as student_id -> (id, name) for easy lookup
                    self.students[str(row['ID'])] = (str(row['ID']), row['Name'])
                self.logger.info(f"Loaded {len(self.students)} student records")
            else:
                self.logger.warning(f"Students file not found: {self.students_file}")
        except Exception as e:
            self.logger.error(f"Error loading students: {e}")
    
    def mark_attendance(self, student_id, student_name):
        """Mark attendance for a recognized student"""
        try:
            # Create today's attendance file
            today = datetime.now().strftime("%Y-%m-%d")
            attendance_file = os.path.join(self.attendance_dir, f"attendance_{today}.csv")
            
            # Get current time
            current_time = datetime.now().strftime("%H:%M:%S")
            
            # Create or append to the attendance file
            file_exists = os.path.exists(attendance_file)
            
            with open(attendance_file, 'a', newline='') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(['ID', 'Name', 'Time', 'Date'])
                writer.writerow([student_id, student_name, current_time, today])
            
            message = f"Attendance marked for {student_name} ({student_id})"
            self.logger.info(message)
            self._update_log(message)
            
            # Show a success message in the UI
            self.after(0, lambda: self._show_attendance_confirmation(student_name))
            
        except Exception as e:
            self.logger.error(f"Error marking attendance: {e}")
            self._update_log(f"Error marking attendance: {e}", level="error")

    def get_appearance_mode(self):
        """Get the current appearance mode (Dark/Light)"""
        try:
            return ctk.get_appearance_mode()
        except:
            return "Dark"  # Default to dark mode

    def _create_manual_frame(self, parent):
        """Create the manual attendance entry frame"""
        manual_frame = ctk.CTkFrame(parent)
        
        # Configure grid
        manual_frame.grid_columnconfigure(0, weight=1)
        manual_frame.grid_rowconfigure(6, weight=1)  # Push everything to the top
        
        # Title
        manual_title = ctk.CTkLabel(
            manual_frame,
            text="Manual Attendance Entry",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        manual_title.grid(row=0, column=0, padx=20, pady=(15, 10), sticky="w")
        
        # Student ID
        id_label = ctk.CTkLabel(manual_frame, text="Student ID:", anchor="w")
        id_label.grid(row=1, column=0, padx=20, pady=(10, 5), sticky="w")
        
        self.manual_id_entry = ctk.CTkEntry(manual_frame)
        self.manual_id_entry.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")
        
        # Student Name
        name_label = ctk.CTkLabel(manual_frame, text="Student Name:", anchor="w")
        name_label.grid(row=3, column=0, padx=20, pady=(10, 5), sticky="w")
        
        self.manual_name_entry = ctk.CTkEntry(manual_frame)
        self.manual_name_entry.grid(row=4, column=0, padx=20, pady=(0, 10), sticky="ew")
        
        # Submit button
        self.manual_submit_button = ctk.CTkButton(
            manual_frame,
            text="Mark Attendance",
            command=self._manual_mark_attendance
        )
        self.manual_submit_button.grid(row=5, column=0, padx=20, pady=(10, 5), sticky="ew")
        
        # Note
        note_label = ctk.CTkLabel(
            manual_frame,
            text="Note: Use this form when automatic\nface recognition is not working",
            font=ctk.CTkFont(size=12),
            text_color=("gray50", "gray70")
        )
        note_label.grid(row=6, column=0, padx=20, pady=(5, 15), sticky="nw")
        
        return manual_frame

    def _update_status(self, message):
        """Update the status message in the UI"""
        try:
            if hasattr(self, 'status_label') and self.status_label.winfo_exists():
                self.status_label.configure(text=message)
        except Exception as e:
            logger.error(f"Error updating status: {e}")
    
    def _update_log(self, message, level="info"):
        """Update log with a message"""
        try:
            # Log to console based on level
            if level == "error":
                logger.error(message)
            elif level == "warning":
                logger.warning(message)
            else:
                logger.info(message)
                
            # If we have a log widget, update it
            if hasattr(self, 'log_text') and self.log_text.winfo_exists():
                # Add timestamp
                timestamp = datetime.now().strftime("%H:%M:%S")
                log_entry = f"[{timestamp}] {message}\n"
                
                # Get text color based on level
                text_color = {
                    "error": "red",
                    "warning": "orange",
                    "info": ("black", "white")
                }.get(level, ("black", "white"))
                
                # Add to log
                self.log_text.configure(state="normal")
                self.log_text.insert("end", log_entry, text_color)
                self.log_text.configure(state="disabled")
                self.log_text.see("end")  # Scroll to bottom
                
        except Exception as e:
            logger.error(f"Error updating log: {e}")
    
    def _show_attendance_confirmation(self, student_name):
        """Show confirmation that attendance was marked for a student"""
        try:
            # Show notification
            self._show_notification(f"Attendance marked for {student_name}", "success")
            
            # Update attendance list display if we have a treeview
            if hasattr(self, 'tree') and self.tree.winfo_exists():
                # Add to the list with animation effect - just an example
                # In a real app, you'd get the actual student details
                today = datetime.now().strftime("%Y-%m-%d")
                time_now = datetime.now().strftime("%H:%M:%S")
                
                # Add to tree with highlight effect
                item_id = self.tree.insert("", "end", values=(
                    "Auto", student_name, time_now, today
                ))
                
                # Scroll to make the new item visible
                self.tree.see(item_id)
                
                # Configure tag for highlighting
                self.tree.tag_configure('highlight', background='#4CAF50', foreground='white')
                self.tree.tag_configure('normal', background='')
                
                # Apply highlight effect (flash a few times)
                def highlight(count=0):
                    try:
                        if not self.tree.winfo_exists():
                            return
                            
                        if count % 2 == 0:
                            self.tree.item(item_id, tags=('highlight',))
                        else:
                            self.tree.item(item_id, tags=('normal',))
                        
                        if count < 6:  # 3 flashes
                            self.after(300, lambda: highlight(count + 1))
                        else:
                            self.tree.item(item_id, tags=('normal',))
                    except Exception as e:
                        logger.error(f"Error in highlight animation: {e}")
                
                # Start highlight animation
                highlight()
                
            # Update our flag that we have attendance records
            if hasattr(self, 'save_button') and self.save_button.winfo_exists():
                self.save_button.configure(state="normal")
                
        except Exception as e:
            logger.error(f"Error showing attendance confirmation: {e}")
            # Fall back to simple status update
            self.show_status(f"Attendance marked for {student_name}", "green")

    def _flash_attendance_marked(self):
        """Visual feedback that attendance was marked"""
        try:
            # Create a flash overlay frame
            flash = ctk.CTkFrame(
                self,
                fg_color=("#4CAF50", "#2E7D32"),  # Green color
                corner_radius=10
            )
            flash.place(relx=0.5, rely=0.4, anchor="center", relwidth=0.4, relheight=0.1)
            
            # Add message
            message = ctk.CTkLabel(
                flash,
                text="✓ Attendance Marked!",
                font=ctk.CTkFont(size=20, weight="bold"),
                text_color="white"
            )
            message.pack(expand=True, fill="both", padx=20, pady=10)
            
            # Fade out effect
            def fade_out(opacity=1.0, step=0):
                if step >= 10 or not flash.winfo_exists():  # 10 steps or widget destroyed
                    flash.destroy()
                    return
                    
                # Reduce opacity
                flash.configure(fg_color=(
                    self._adjust_color_opacity(("#4CAF50", "#2E7D32")[0], opacity),
                    self._adjust_color_opacity(("#4CAF50", "#2E7D32")[1], opacity)
                ))
                # Schedule next fade step
                self.after(100, lambda: fade_out(opacity - 0.1, step + 1))
            
            # Start fade effect after 1 second
            self.after(1000, lambda: fade_out())
        except Exception as e:
            self.logger.error(f"Error showing attendance marked flash: {e}")