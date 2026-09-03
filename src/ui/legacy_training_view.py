"""
Face Training View for Face Detection Attendance System
"""
import os
import cv2
import numpy as np
import tkinter as tk
import threading
import customtkinter as ctk
from PIL import Image, ImageTk
import logging
import time
import glob
from datetime import datetime

from src.core.face_recognition.face_detector import FaceDetector

# Configure logging
logger = logging.getLogger(__name__)

class TrainingView(ctk.CTkFrame):
    """View for training face recognition models"""
    
    def __init__(self, master, controller=None, **kwargs):
        """
        Initialize the training view
        
        Args:
            master: Parent widget
            controller: Controller instance
        """
        super().__init__(master, **kwargs)
        self.master = master
        self.controller = controller
        
        # Initialize component variables
        self.camera = None
        self.camera_running = False
        self.training_running = False
        self.student_data = []
        self.after_ids = []  # Keep track of after() IDs for cleanup
        self.training_process = None
        self.current_image = None
        
        # Configuration variables
        self.camera_var = ctk.StringVar(value="0")  # Default camera index
        self.auto_capture_var = ctk.BooleanVar(value=True)
        self.image_count_var = ctk.StringVar(value="20")  # Default number of images
        
        # Student info variables (for manual mode)
        self.student_id_var = ctk.StringVar(value="")
        self.student_name_var = ctk.StringVar(value="")
        self.images_captured = 0
        self.target_images = 20
        
        # Setup UI
        self._setup_ui()
        
        # Initialize controller and load data
        self._initialize_data()
        
        # Update statistics initially
        self.update_statistics()
        
        # Log initialization
        logger.info("Training view initialized")
    
    def _setup_ui(self):
        """Set up the training view UI"""
        # Configure grid
        self.grid_columnconfigure(0, weight=0)  # Settings panel - fixed width
        self.grid_columnconfigure(1, weight=1)  # Main content - expandable
        self.grid_rowconfigure(0, weight=1)  # Both rows expand
        
        # Create main panels
        self._create_settings_panel()
        self._create_main_content()
    
    def _create_settings_panel(self):
        """Create the settings panel on the left side"""
        settings_frame = ctk.CTkFrame(self, corner_radius=10, width=300)
        settings_frame.grid(row=0, column=0, padx=(20, 10), pady=20, sticky="nsew")
        settings_frame.grid_propagate(False)  # Prevent frame from shrinking
        
        # Configure settings frame
        settings_frame.grid_columnconfigure(0, weight=1)
        settings_frame.grid_rowconfigure(9, weight=1)  # Push everything to the top
        
        # Title
        title_label = ctk.CTkLabel(
            settings_frame,
            text="Training Settings",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.grid(row=0, column=0, padx=20, pady=(20, 30), sticky="w")
        
        # Camera selection
        camera_label = ctk.CTkLabel(settings_frame, text="Camera Source:", anchor="w")
        camera_label.grid(row=1, column=0, padx=20, pady=(0, 5), sticky="w")
        
        camera_menu = ctk.CTkOptionMenu(
            settings_frame,
            variable=self.camera_var,
            values=["0", "1", "2", "3"],
            width=250
        )
        camera_menu.grid(row=2, column=0, padx=20, pady=(0, 15), sticky="w")
        
        # Images to capture
        images_label = ctk.CTkLabel(settings_frame, text="Images to Capture:", anchor="w")
        images_label.grid(row=3, column=0, padx=20, pady=(0, 5), sticky="w")
        
        images_entry = ctk.CTkEntry(
            settings_frame,
            textvariable=self.image_count_var,
            width=250
        )
        images_entry.grid(row=4, column=0, padx=20, pady=(0, 15), sticky="w")
        
        # Student ID
        id_label = ctk.CTkLabel(settings_frame, text="Student ID:", anchor="w")
        id_label.grid(row=5, column=0, padx=20, pady=(0, 5), sticky="w")
        
        id_entry = ctk.CTkEntry(
            settings_frame,
            textvariable=self.student_id_var,
            width=250,
            placeholder_text="Enter student ID"
        )
        id_entry.grid(row=6, column=0, padx=20, pady=(0, 15), sticky="w")
        
        # Student Name
        name_label = ctk.CTkLabel(settings_frame, text="Student Name:", anchor="w")
        name_label.grid(row=7, column=0, padx=20, pady=(0, 5), sticky="w")
        
        name_entry = ctk.CTkEntry(
            settings_frame,
            textvariable=self.student_name_var,
            width=250,
            placeholder_text="Enter student name"
        )
        name_entry.grid(row=8, column=0, padx=20, pady=(0, 15), sticky="w")
        
        # Auto capture mode
        auto_capture_switch = ctk.CTkSwitch(
            settings_frame,
            text="Auto-capture Mode",
            variable=self.auto_capture_var,
            onvalue=True,
            offvalue=False,
            width=250
        )
        auto_capture_switch.grid(row=9, column=0, padx=20, pady=(0, 15), sticky="w")
        
        # Control buttons frame
        controls_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        controls_frame.grid(row=10, column=0, padx=20, pady=(20, 20), sticky="ew")
        controls_frame.grid_columnconfigure(0, weight=1)
        controls_frame.grid_columnconfigure(1, weight=1)
        
        # Start camera button
        self.camera_button = ctk.CTkButton(
            controls_frame,
            text="Start Camera",
            command=self.start_camera,
            height=40,
            fg_color=("#3a7ebf", "#1f538d")
        )
        self.camera_button.grid(row=0, column=0, padx=(0, 5), pady=0, sticky="ew")
        
        # Start training button
        self.training_button = ctk.CTkButton(
            controls_frame,
            text="Start Training",
            command=self.start_training,
            height=40,
            fg_color=("#2ecc71", "#27ae60")
        )
        self.training_button.grid(row=0, column=1, padx=(5, 0), pady=0, sticky="ew")
        
        # Capture button (appears when camera is on)
        self.capture_button = ctk.CTkButton(
            settings_frame,
            text="Capture Image",
            command=self.capture_image,
            height=40,
            state="disabled",
            fg_color=("#e67e22", "#d35400")
        )
        self.capture_button.grid(row=11, column=0, padx=20, pady=(10, 20), sticky="ew")
    
    def _create_main_content(self):
        """Create the main content area with camera feed and logs"""
        main_frame = ctk.CTkFrame(self, corner_radius=10)
        main_frame.grid(row=0, column=1, padx=(10, 20), pady=20, sticky="nsew")
        
        # Configure main frame
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(0, weight=3)  # Camera gets more space
        main_frame.grid_rowconfigure(1, weight=1)  # Log gets less space
        main_frame.grid_rowconfigure(2, weight=0)  # Progress gets fixed space
        
        # Create camera view
        self._create_camera_view(main_frame)
        
        # Create log section
        self._create_log_section(main_frame)
        
        # Create progress section
        self._create_progress_section(main_frame)
    
    def _create_camera_view(self, parent):
        """Create the camera view section"""
        camera_frame = ctk.CTkFrame(parent, corner_radius=10)
        camera_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="nsew")
        
        # Configure camera frame
        camera_frame.grid_columnconfigure(0, weight=1)
        camera_frame.grid_rowconfigure(0, weight=0)  # Title
        camera_frame.grid_rowconfigure(1, weight=1)  # Camera view
        
        # Camera section title
        camera_title = ctk.CTkLabel(
            camera_frame, 
            text="Camera Feed",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        camera_title.grid(row=0, column=0, padx=20, pady=(15, 10), sticky="w")
        
        # Camera container with fixed dimensions to prevent resizing
        camera_container = ctk.CTkFrame(camera_frame, fg_color="transparent", width=640, height=480)
        camera_container.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        camera_container.grid_propagate(False)  # Prevent container from resizing with contents
        camera_container.grid_columnconfigure(0, weight=1)
        camera_container.grid_rowconfigure(0, weight=1)
        
        # Create a black background for the camera view
        bg_color = "black" if ctk.get_appearance_mode() == "Dark" else "#333333"
        
        # Camera display
        self.camera_view = ctk.CTkLabel(
            camera_container,
            text="Camera feed will appear here",
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color=bg_color,
            text_color="white",
            corner_radius=8
        )
        self.camera_view.grid(row=0, column=0, sticky="nsew")
        
        # Capture counter
        self.capture_counter = ctk.CTkLabel(
            camera_frame,
            text="Images: 0/20",
            font=ctk.CTkFont(size=14)
        )
        self.capture_counter.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="e")
        
        # FPS counter 
        self.fps_label = ctk.CTkLabel(
            camera_frame,
            text="FPS: 0",
            font=ctk.CTkFont(size=12),
            text_color=("gray50", "gray70")
        )
        self.fps_label.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="w")
    
    def _create_log_section(self, parent):
        """Create the log section"""
        log_frame = ctk.CTkFrame(parent, corner_radius=10)
        log_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        
        # Configure log frame
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(0, weight=0)  # Title
        log_frame.grid_rowconfigure(1, weight=1)  # Log content
        
        # Log title
        log_title = ctk.CTkLabel(
            log_frame,
            text="Training Log",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        log_title.grid(row=0, column=0, padx=20, pady=10, sticky="w")
        
        # Log text box
        self.log_text = ctk.CTkTextbox(log_frame, wrap="word")
        self.log_text.grid(row=1, column=0, padx=20, pady=(0, 15), sticky="nsew")
        self.log_text.configure(state="disabled")
    
    def _create_progress_section(self, parent):
        """Create the progress section"""
        progress_frame = ctk.CTkFrame(parent, corner_radius=10)
        progress_frame.grid(row=2, column=0, padx=20, pady=(10, 20), sticky="nsew")
        
        # Configure progress frame
        progress_frame.grid_columnconfigure(0, weight=1)
        progress_frame.grid_columnconfigure(1, weight=0)
        progress_frame.grid_rowconfigure(0, weight=1)
        
        # Progress bar
        progress_container = ctk.CTkFrame(progress_frame, fg_color="transparent")
        progress_container.grid(row=0, column=0, padx=20, pady=15, sticky="nsew")
        progress_container.grid_columnconfigure(0, weight=1)
        progress_container.grid_rowconfigure(0, weight=0)
        progress_container.grid_rowconfigure(1, weight=0)
        
        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(progress_container, height=15)
        self.progress_bar.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        self.progress_bar.set(0)
        
        # Progress label
        self.progress_label = ctk.CTkLabel(
            progress_container,
            text="Ready to start training",
            font=ctk.CTkFont(size=12)
        )
        self.progress_label.grid(row=1, column=0, sticky="w")
        
        # Status display
        self.status_display = ctk.CTkLabel(
            progress_frame,
            text="Status: Ready",
            font=ctk.CTkFont(size=14, weight="bold"),
            width=250
        )
        self.status_display.grid(row=0, column=1, padx=20, pady=15, sticky="e")
        
    def start_camera(self):
        """Start or stop the camera feed"""
        if self.camera_running:
            self.stop_camera()
            return
            
        try:
            # Update button state
            self.camera_button.configure(text="Starting...", state="disabled")
            
            # Get camera index
            try:
                camera_index = int(self.camera_var.get())
            except ValueError:
                camera_index = 0
                
            # Start camera in a thread
            self.camera_thread = threading.Thread(target=self._initialize_camera, args=(camera_index,))
            self.camera_thread.daemon = True
            self.camera_running = True
            self.camera_thread.start()
            
            self.log("Starting camera...", level="info")
            self.show_status("Starting camera...", "blue")
            
        except Exception as e:
            logger.error(f"Error starting camera: {e}")
            self.log(f"Error starting camera: {e}", level="error")
            self.show_status(f"Camera error: {e}", "red")
            self._camera_start_failed()
    
    def _initialize_camera(self, camera_index):
        """Initialize the camera"""
        try:
            # First try with DirectShow (Windows)
            self.camera = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
            
            # If DirectShow fails, try the default method
            if not self.camera.isOpened():
                self.log("DirectShow failed, trying default method", level="warning")
                self.camera = cv2.VideoCapture(camera_index)
                
            # Check if camera opened
            if not self.camera.isOpened():
                self.log("Failed to open camera", level="error")
                self.after(0, self._camera_start_failed)
                return
                
            # Set resolution
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
            # Get actual resolution
            width = self.camera.get(cv2.CAP_PROP_FRAME_WIDTH)
            height = self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
            self.log(f"Camera resolution: {width}x{height}", level="info")
            
            # Read test frame
            ret, frame = self.camera.read()
            if not ret or frame is None:
                self.log("Failed to read from camera", level="error")
                self.after(0, self._camera_start_failed)
                return
                
            # Camera started successfully
            self.after(0, self._camera_start_success)
            
            # Run camera processing loop
            self._camera_processing_loop()
            
        except Exception as e:
            logger.error(f"Error initializing camera: {e}")
            self.log(f"Error initializing camera: {e}", level="error")
            self.after(0, self._camera_start_failed)
    
    def _camera_start_success(self):
        """Handle successful camera start"""
        self.camera_button.configure(
            text="Stop Camera",
            state="normal",
            fg_color=("#e74c3c", "#c0392b")
        )
        self.capture_button.configure(state="normal")
        self.log("Camera started successfully", level="info")
        self.show_status("Camera ready", "green")
    
    def _camera_start_failed(self):
        """Handle camera start failure"""
        self.camera_running = False
        self.camera_button.configure(
            text="Start Camera",
            state="normal",
            fg_color=("#3a7ebf", "#1f538d")
        )
        self.capture_button.configure(state="disabled")
        self.log("Failed to start camera", level="error")
        self.show_status("Camera failed to start", "red")
    
    def _camera_processing_loop(self):
        """Process camera frames"""
        try:
            frame_count = 0
            last_fps_time = time.time()
            
            while self.camera_running and self.camera and self.camera.isOpened():
                # Read frame
                ret, frame = self.camera.read()
                
                if not ret:
                    logger.error("Failed to read frame")
                    time.sleep(0.1)
                    continue
                
                # Store frame for capture
                self.current_frame = frame.copy()
                
                # Process frame - face detection, etc.
                processed_frame = self._process_camera_frame(frame)
                
                # Update UI with processed frame
                self.after(0, lambda f=processed_frame: self._update_camera_display(f))
                
                # Calculate FPS
                frame_count += 1
                current_time = time.time()
                if current_time - last_fps_time >= 1.0:
                    fps = frame_count / (current_time - last_fps_time)
                    self.after(0, lambda f=fps: self._update_fps(f))
                    frame_count = 0
                    last_fps_time = current_time
                
                # Limit frame rate
                time.sleep(0.03)  # ~30 fps
        
        except Exception as e:
            logger.error(f"Error in camera loop: {e}")
            self.log(f"Camera error: {e}", level="error")
        finally:
            # Clean up
            if self.camera:
                self.camera.release()
                self.camera = None
            
            # Update UI
            self.camera_running = False
            self.log("Camera stopped", level="info")
            
            # Reset UI if it still exists
            if self.winfo_exists():
                self.after(0, self._reset_camera_ui)
    
    def _update_fps(self, fps):
        """Update FPS display"""
        if hasattr(self, 'fps_label') and self.fps_label.winfo_exists():
            self.fps_label.configure(text=f"FPS: {fps:.1f}")
    
    def _reset_camera_ui(self):
        """Reset UI after camera stops"""
        self.camera_button.configure(
            text="Start Camera",
            state="normal",
            fg_color=("#3a7ebf", "#1f538d")
        )
        self.capture_button.configure(state="disabled")
        if hasattr(self, 'camera_view'):
            self.camera_view.configure(text="Camera feed will appear here", image=None)
    
    def _process_camera_frame(self, frame):
        """Process a frame for display and face detection"""
        try:
            # Mirror image horizontally for more intuitive display
            frame = cv2.flip(frame, 1)
            
            # Convert to RGB (OpenCV uses BGR)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Detect faces
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
            
            # Draw rectangle around detected faces
            for (x, y, w, h) in faces:
                cv2.rectangle(rgb_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                
                # Add face detected label
                label_background = rgb_frame[max(0, y-25):y, x:min(x+w, rgb_frame.shape[1]-1)]
                if label_background.size > 0:  # Check if the region is valid
                    label_background[:] = (70, 70, 200)  # Blue background
                    
                cv2.putText(rgb_frame, "Face", (x+5, y-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            return rgb_frame
            
        except Exception as e:
            logger.error(f"Error processing frame: {e}")
            return frame  # Return original frame if processing fails
    
    def _update_camera_display(self, frame):
        """Update the camera display with the current frame"""
        try:
            # Check if view still exists
            if not self.winfo_exists():
                return
            
            if frame is None:
                logger.warning("Received None frame in _update_camera_display")
                return
                
            # Convert to PIL image if it's a numpy array
            if isinstance(frame, np.ndarray):
                pil_image = Image.fromarray(frame)
            else:
                pil_image = frame
            
            # Check if camera_view still exists
            if not hasattr(self, 'camera_view') or not self.camera_view.winfo_exists():
                return
            
            # Get current dimensions of the camera view
            width = self.camera_view.winfo_width() or 640
            height = self.camera_view.winfo_height() or 480
            
            # Create CTkImage from PIL image
            ctk_image = ctk.CTkImage(
                light_image=pil_image,
                dark_image=pil_image,
                size=(width, height)
            )
            
            # Update camera view
            self.camera_view.configure(image=ctk_image, text="")
            
            # Store reference to prevent garbage collection
            self.current_image = ctk_image
            
        except Exception as e:
            logger.error(f"Error updating camera display: {e}")
            import traceback
            traceback.print_exc()
    
    def stop_camera(self):
        """Stop the camera"""
        self.camera_running = False
        self.camera_button.configure(text="Stopping...", state="disabled")
        self.capture_button.configure(state="disabled")
        self.log("Stopping camera...", level="info")
    
    def capture_image(self):
        """Capture a face image"""
        if not self.camera_running or not hasattr(self, 'current_frame') or self.current_frame is None:
            self.show_status("Camera not running", "red")
            return
            
        try:
            # Get student ID and name
            student_id = self.student_id_var.get().strip()
            student_name = self.student_name_var.get().strip()
            
            if not student_id:
                self.show_status("Please enter student ID", "red")
                return
                
            if not student_name:
                self.show_status("Please enter student name", "red")
                return
            
            # Get number of images to capture
            try:
                self.target_images = int(self.image_count_var.get())
                if self.target_images <= 0:
                    self.target_images = 20
            except:
                self.target_images = 20
            
            # Create directory for student images
            image_dir = os.path.join(self.images_dir, student_id)
            os.makedirs(image_dir, exist_ok=True)
            
            # Detect faces in current frame
            gray = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2GRAY)
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
            
            if len(faces) == 0:
                self.show_status("No face detected", "red")
                return
                
            if len(faces) > 1:
                self.show_status("Multiple faces detected", "red")
                return
            
            # Save image
            image_path = os.path.join(image_dir, f"{student_id}_{self.images_captured}.jpg")
            cv2.imwrite(image_path, self.current_frame)
            
            # Increment counter
            self.images_captured += 1
            self.capture_counter.configure(text=f"Images: {self.images_captured}/{self.target_images}")
            
            # Update progress
            progress = self.images_captured / self.target_images
            self.progress_bar.set(progress)
            
            # Show status
            self.show_status(f"Image {self.images_captured} captured", "green")
            self.log(f"Captured image {self.images_captured}/{self.target_images} for student {student_id}", level="info")
            
            # Flash effect
            original_fg = self.camera_view.cget("fg_color")
            self.camera_view.configure(fg_color="green")
            self.after(200, lambda: self.camera_view.configure(fg_color=original_fg))
            
            # Auto-start training if all images captured
            if self.images_captured >= self.target_images:
                self.show_status("All images captured", "green")
                self.after(1000, self.start_training)
                
        except Exception as e:
            logger.error(f"Error capturing image: {e}")
            self.show_status(f"Error capturing image", "red")
            self.log(f"Error capturing image: {e}", level="error")
    
    def start_training(self):
        """Start or stop the face recognition training process"""
        if self.training_running:
            # Stop training
            self.training_running = False
            self.training_button.configure(
                text="Start Training",
                fg_color=("#2ecc71", "#27ae60")
            )
            self.log("Training cancelled", level="warning")
            return
            
        # Get student info
        student_id = self.student_id_var.get().strip()
        student_name = self.student_name_var.get().strip()
        
        if not student_id:
            self.show_status("Please enter student ID", "red")
            return
            
        if not student_name:
            self.show_status("Please enter student name", "red")
            return
            
        # Check if we have captured images
        if self.images_captured == 0:
            self.show_status("Please capture images first", "red")
            return
            
        # Start training
        self.training_running = True
        self.training_button.configure(
            text="Cancel Training",
            fg_color=("#e74c3c", "#c0392b")
        )
        
        # Reset progress
        self.progress_bar.set(0)
        self.progress_label.configure(text="Starting training...")
        
        # Clear log
        self.log_text.configure(state="normal")
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state="disabled")
        
        # Start training in background
        self.log("Starting face recognition training...", level="info")
        self.show_status("Training started", "blue")
        
        # Start training thread
        self.training_thread = threading.Thread(target=self._training_process)
        self.training_thread.daemon = True
        self.training_thread.start()
        
    def _training_process(self):
        """Run the face recognition training process"""
        try:
            # Define steps and update initial UI
            steps = ["Finding training images", "Preprocessing images", "Extracting features", 
                    "Training recognizer", "Saving model", "Finalizing"]
            total_steps = len(steps)
            
            # Progress setup
            progress = 0
            self.after(0, lambda p=progress, s=steps[0]: self._update_progress_ui(p, s))
            self.log(f"Step 1/{total_steps}: {steps[0]}", level="info")
            
            # Step 1: Finding training images
            student_id = self.student_id_var.get().strip()
            if not student_id:
                self.log("Error: No student ID provided", level="error")
                self.after(0, lambda: self._update_training_progress_ui(False))
                return
                
            # Look for training images in the student's directory
            image_dir = os.path.join(self.images_dir, student_id)
            if not os.path.exists(image_dir):
                self.log(f"Error: No training images found for student {student_id}", level="error")
                self.after(0, lambda: self._update_training_progress_ui(False))
                return
                
            image_paths = glob.glob(os.path.join(image_dir, f"{student_id}_*.jpg"))
            if not image_paths:
                self.log(f"Error: No training images found for student {student_id}", level="error")
                self.after(0, lambda: self._update_training_progress_ui(False))
                return
                
            self.log(f"Found {len(image_paths)} training images for student {student_id}", level="info")
            time.sleep(0.5)
            
            # Update progress
            progress = 1/total_steps
            self.after(0, lambda p=progress, s=steps[1]: self._update_progress_ui(p, s))
            self.log(f"Step 2/{total_steps}: {steps[1]}", level="info")
            
            # Step 2: Preprocessing images
            faces = []
            labels = []
            label_id = int(student_id) if student_id.isdigit() else hash(student_id) % 1000000
            
            # Face cascade for detection
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            
            for img_path in image_paths:
                # Check if training was cancelled
                if not self.training_running:
                    self.log("Training cancelled", level="warning")
                    self.after(0, lambda: self._update_training_progress_ui(False))
                    return
                    
                # Read and process image
                img = cv2.imread(img_path)
                if img is None:
                    self.log(f"Failed to read image: {img_path}", level="warning")
                    continue
                    
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                detected_faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
                
                if len(detected_faces) == 0:
                    self.log(f"No face detected in image: {os.path.basename(img_path)}", level="warning")
                    continue
                    
                if len(detected_faces) > 1:
                    self.log(f"Multiple faces detected in image: {os.path.basename(img_path)}", level="warning")
                    # Use the largest face
                    detected_faces = sorted(detected_faces, key=lambda x: x[2]*x[3], reverse=True)
                    
                # Extract face ROI and add to training data
                x, y, w, h = detected_faces[0]
                face_roi = gray[y:y+h, x:x+w]
                
                # Resize to a consistent size for training
                face_roi = cv2.resize(face_roi, (100, 100))
                faces.append(face_roi)
                labels.append(label_id)
                
            # Check if we have enough faces to train
            if len(faces) == 0:
                self.log("Error: No valid faces found in training images", level="error")
                self.after(0, lambda: self._update_training_progress_ui(False))
                return
                
            self.log(f"Preprocessed {len(faces)} valid faces for training", level="info")
            time.sleep(0.5)
            
            # Update progress
            progress = 2/total_steps
            self.after(0, lambda p=progress, s=steps[2]: self._update_progress_ui(p, s))
            self.log(f"Step 3/{total_steps}: {steps[2]}", level="info")
            
            # Check if cancelled
            if not self.training_running:
                self.log("Training cancelled", level="warning")
                self.after(0, lambda: self._update_training_progress_ui(False))
                return
                
            # Step 3: Create and train face recognizer
            time.sleep(0.5)
            progress = 3/total_steps
            self.after(0, lambda p=progress, s=steps[3]: self._update_progress_ui(p, s))
            self.log(f"Step 4/{total_steps}: {steps[3]}", level="info")
            
            # Initialize face recognizer
            face_recognizer = cv2.face.LBPHFaceRecognizer_create()
            
            # Convert faces and labels to numpy arrays
            faces_array = np.array(faces)
            labels_array = np.array(labels)
            
            # Train the recognizer
            face_recognizer.train(faces_array, labels_array)
            
            self.log(f"Face recognizer trained with {len(faces)} images", level="info")
            time.sleep(0.5)
            
            # Update progress
            progress = 4/total_steps
            self.after(0, lambda p=progress, s=steps[4]: self._update_progress_ui(p, s))
            self.log(f"Step 5/{total_steps}: {steps[4]}", level="info")
            
            # Check if cancelled
            if not self.training_running:
                self.log("Training cancelled", level="warning")
                self.after(0, lambda: self._update_training_progress_ui(False))
                return
                
            # Step 4: Save the trained model
            os.makedirs(self.models_dir, exist_ok=True)
            
            # Two saving methods:
            # 1. Save student-specific model for backup
            student_model_path = os.path.join(self.models_dir, f"face_recognizer_{student_id}.yml")
            face_recognizer.write(student_model_path)
            
            # 2. For the main model, we need to load existing model if it exists 
            # and merge with the new student data, or create a new one
            main_model_path = os.path.join(self.models_dir, "face_recognizer.yml")
            
            if os.path.exists(main_model_path):
                # Try to read existing model file first
                try:
                    # Create a new recognizer to avoid training again
                    main_recognizer = cv2.face.LBPHFaceRecognizer_create()
                    main_recognizer.read(main_model_path)
                    
                    # Update with the new faces for this student
                    # If student already exists, this will update their data
                    for face, label in zip(faces, labels):
                        main_recognizer.update([face], np.array([label]))
                    
                    # Save the updated model
                    main_recognizer.write(main_model_path)
                    self.log("Updated existing face recognition model", level="info")
                    
                except Exception as e:
                    logger.error(f"Failed to update existing model: {e}")
                    self.log(f"Error: Failed to update existing model. Creating new one.", level="warning")
                    # Fall back to creating a new model
                    face_recognizer.write(main_model_path)
                    self.log("Created new face recognition model", level="info")
            else:
                # No existing model, save the new one
                face_recognizer.write(main_model_path)
                self.log("Created new face recognition model", level="info")
            
            # Update the student info in CSV file
            self._update_student_info(student_id, self.student_name_var.get().strip())
            
            # Cleanup and final step
            time.sleep(0.5)
            progress = 5/total_steps
            self.after(0, lambda p=progress, s=steps[5]: self._update_progress_ui(p, s))
            self.log(f"Step 6/{total_steps}: {steps[5]}", level="info")
            
            # Set final progress
            time.sleep(0.5)
            self.after(0, lambda: self._update_progress_ui(1.0, "Training complete"))
            self.log("Face recognition model trained and saved successfully", level="info")
            
            # Update UI for completion
            self.after(0, lambda: self._update_training_progress_ui(True))
            
        except Exception as e:
            logger.error(f"Error in training process: {e}")
            self.log(f"Error in training process: {e}", level="error")
            import traceback
            traceback.print_exc()
            self.after(0, lambda: self._update_training_progress_ui(False))
            
    def _update_student_info(self, student_id, student_name):
        """Update student information in the students CSV file"""
        try:
            # Path to the students CSV file
            csv_path = os.path.join(self.data_dir, "students.csv")
            
            # Read existing CSV or create new one
            if os.path.exists(csv_path):
                try:
                    import pandas as pd
                    df = pd.read_csv(csv_path)
                    
                    # Check if student already exists
                    if student_id in df['ID'].values:
                        # Update existing student
                        idx = df.index[df['ID'] == student_id][0]
                        df.at[idx, 'Name'] = student_name
                    else:
                        # Add new student
                        new_row = {'ID': student_id, 'Name': student_name}
                        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                except Exception as e:
                    logger.error(f"Error reading students CSV: {e}")
                    # Create new DataFrame
                    import pandas as pd
                    df = pd.DataFrame([{'ID': student_id, 'Name': student_name}])
            else:
                # Create new CSV with headers
                import pandas as pd
                df = pd.DataFrame([{'ID': student_id, 'Name': student_name}])
            
            # Save the updated CSV
            df.to_csv(csv_path, index=False)
            self.log(f"Updated student information for ID: {student_id}", level="info")
            
        except Exception as e:
            logger.error(f"Error updating student information: {e}")
            self.log(f"Error updating student information: {e}", level="warning")
    
    def _update_progress_ui(self, progress, status_text):
        """Update progress UI elements"""
        if hasattr(self, 'progress_bar'):
            self.progress_bar.set(progress)
        if hasattr(self, 'progress_label'):
            self.progress_label.configure(text=status_text)
    
    def _update_training_progress_ui(self, success):
        """Update UI after training process completes"""
        self.training_running = False
        self.training_button.configure(
            text="Start Training",
            fg_color=("#2ecc71", "#27ae60")
        )
        
        if success:
            self.show_status("Training completed successfully", "green")
            # Reset capture counter for next student
            self.images_captured = 0
            self.capture_counter.configure(text=f"Images: 0/{self.target_images}")
        else:
            self.show_status("Training failed or cancelled", "red")
    
    def log(self, message, level="info"):
        """Add a message to the log"""
        try:
            # Check if view still exists
            if not self.winfo_exists():
                # Just log to system logger
                if level == "info":
                    logger.info(message)
                elif level == "error":
                    logger.error(message)
                elif level == "warning":
                    logger.warning(message)
                return
            
            if hasattr(self, "log_text") and self.log_text is not None and self.log_text.winfo_exists():
                timestamp = datetime.now().strftime("%H:%M:%S")
                log_message = f"[{timestamp}] {message}\n"
                
                # Get the current state - with error handling
                try:
                    # Enable for editing
                    self.log_text.configure(state="normal")
                    
                    # Insert the message at the end
                    self.log_text.insert("end", log_message)
                    
                    # Scroll to the end
                    self.log_text.see("end")
                    
                    # Set back to disabled state
                    self.log_text.configure(state="disabled")
                except Exception as e:
                    logger.error(f"Error updating log text: {e}")
                
            # Also send to logger
            if level == "info":
                logger.info(message)
            elif level == "error":
                logger.error(message)
            elif level == "warning":
                logger.warning(message)
        except Exception as e:
            logger.error(f"Error in log method: {e}")
            
    def show_status(self, message, color="black"):
        """Update the status display with a message"""
        try:
            # Convert color name to supported color
            text_color = None
            if color == "green":
                text_color = ("green", "#00aa00")
            elif color == "red":
                text_color = ("red", "#ee5555")
            elif color == "orange":
                text_color = ("orange", "#ff9900")
            elif color == "blue":
                text_color = ("blue", "#0066ff")
                
            # Update status display
            if hasattr(self, 'status_display') and self.status_display is not None:
                prefix = "Status: "
                if not message.startswith(prefix):
                    message = f"{prefix}{message}"
                    
                if text_color:
                    self.status_display.configure(text=message, text_color=text_color)
                else:
                    self.status_display.configure(text=message, text_color=("gray10", "gray90"))
                
        except Exception as e:
            logger.error(f"Error updating status: {e}")
    
    def update_statistics(self):
        """Update training statistics"""
        try:
            # Check for model file
            if hasattr(self, 'model_path') and os.path.exists(self.model_path):
                self.log(f"Found existing face recognition model", level="info")
                modification_time = datetime.fromtimestamp(os.path.getmtime(self.model_path))
                self.log(f"Model last modified: {modification_time.strftime('%Y-%m-%d %H:%M:%S')}", level="info")
            else:
                self.log("No face recognition model found. Training required.", level="warning")
        except Exception as e:
            logger.error(f"Error updating statistics: {e}")
    
    def _initialize_data(self):
        """Initialize data for the training view"""
        try:
            # Create directory structure if it doesn't exist
            self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
            self.images_dir = os.path.join(self.data_dir, "training_images")
            os.makedirs(self.images_dir, exist_ok=True)
            
            # Initialize student data if controller exists
            if self.controller and hasattr(self.controller, "get_students"):
                self.student_data = self.controller.get_students()
                self.log(f"Loaded {len(self.student_data)} students from database")
            
            # Check for model
            self.models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "models")
            os.makedirs(self.models_dir, exist_ok=True)
            
            self.model_path = os.path.join(self.models_dir, "face_recognizer.yml")
            if os.path.exists(self.model_path):
                self.log(f"Found existing face recognition model")
            else:
                self.log("No face recognition model found. Training required.")
                
        except Exception as e:
            logger.error(f"Error initializing data: {e}")
            self.show_status(f"Error: {str(e)}", color="red")
    
    def cleanup(self):
        """Clean up resources when view is closed"""
        # Set the running flag to False first to stop any loops
        self.camera_running = False
        self.training_running = False
        
        # Stop camera if running
        if self.camera is not None:
            try:
                self.camera.release()
            except:
                pass
            self.camera = None
        
        # Cancel any pending after calls
        if hasattr(self, 'after_ids'):
            for after_id in self.after_ids:
                try:
                    self.after_cancel(after_id)
                except Exception as e:
                    logger.error(f"Error canceling after ID {after_id}: {e}")
                    
            # Clear the list
            self.after_ids = []
            
        logger.info("Training View resources cleaned up")
        return True
        
    def after(self, ms, func=None, *args):
        """Override after to track IDs for cleanup"""
        if func is not None:
            after_id = super().after(ms, func, *args)
            self.after_ids.append(after_id)
            return after_id
        return super().after(ms) 