"""
Student Registration module for Face Detection Attendance System
"""
import os
import cv2
import time
import logging
import numpy as np
import tkinter as tk
import pandas as pd
import threading
import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw, ImageFont
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)

class StudentRegistrationView(ctk.CTkFrame):
    """Student Registration View to add new students and capture their face data"""
    
    def __init__(self, master):
        """
        Initialize the student registration view
        
        Args:
            master: Parent widget
        """
        super().__init__(master)
        
        # Initialize variables
        self.camera_feed = None
        self.camera_thread = None
        self.is_capturing = False
        self.camera_id = 0
        self.captured_images = []
        self.capture_count = 0
        self.max_captures = 5  # Number of face images to capture per student
        self.current_student_id = None
        self.current_student_name = None
        self.current_student_course = None
        self.current_frame = None
        
        # Track after IDs for cleanup
        self.after_ids = []
        
        # Initialize face detection
        self._init_face_detection()
        
        # Create UI elements
        self._setup_ui()
        
        logger.info("Student Registration View initialized")
    
    def _setup_ui(self):
        """Set up the registration form UI"""
        # Configure grid layout (2x1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)  # Form column
        self.grid_columnconfigure(1, weight=1)  # Camera column
        
        # Create form frame
        self.form_frame = ctk.CTkFrame(self)
        self.form_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        # Configure form frame grid layout
        self.form_frame.grid_rowconfigure(11, weight=1)  # Push everything up
        self.form_frame.grid_columnconfigure(0, weight=1)
        
        # Title
        self.title_label = ctk.CTkLabel(
            self.form_frame,
            text="Student Registration",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.title_label.grid(row=0, column=0, padx=20, pady=(20, 30), sticky="ew")
        
        # Form fields
        # Student ID
        self.id_label = ctk.CTkLabel(
            self.form_frame,
            text="Student ID:",
            anchor="w",
            font=ctk.CTkFont(size=14)
        )
        self.id_label.grid(row=1, column=0, padx=20, pady=(10, 5), sticky="w")
        
        self.id_entry = ctk.CTkEntry(
            self.form_frame,
            placeholder_text="Enter student ID"
        )
        self.id_entry.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")
        
        # Name
        self.name_label = ctk.CTkLabel(
            self.form_frame,
            text="Name:",
            anchor="w",
            font=ctk.CTkFont(size=14)
        )
        self.name_label.grid(row=3, column=0, padx=20, pady=(10, 5), sticky="w")
        
        self.name_entry = ctk.CTkEntry(
            self.form_frame,
            placeholder_text="Enter student name"
        )
        self.name_entry.grid(row=4, column=0, padx=20, pady=(0, 10), sticky="ew")
        
        # Course/Subject
        self.course_label = ctk.CTkLabel(
            self.form_frame,
            text="Course/Subject:",
            anchor="w",
            font=ctk.CTkFont(size=14)
        )
        self.course_label.grid(row=5, column=0, padx=20, pady=(10, 5), sticky="w")
        
        self.course_entry = ctk.CTkEntry(
            self.form_frame,
            placeholder_text="Enter course or subject"
        )
        self.course_entry.grid(row=6, column=0, padx=20, pady=(0, 10), sticky="ew")
        
        # Year
        self.year_label = ctk.CTkLabel(
            self.form_frame,
            text="Year:",
            anchor="w",
            font=ctk.CTkFont(size=14)
        )
        self.year_label.grid(row=7, column=0, padx=20, pady=(10, 5), sticky="w")
        
        current_year = datetime.now().year
        years = [str(y) for y in range(current_year-4, current_year+2)]
        self.year_var = ctk.StringVar(value=str(current_year))
        self.year_combobox = ctk.CTkComboBox(
            self.form_frame,
            values=years,
            variable=self.year_var,
            state="readonly"
        )
        self.year_combobox.grid(row=8, column=0, padx=20, pady=(0, 20), sticky="ew")
        
        # Register button
        self.register_button = ctk.CTkButton(
            self.form_frame,
            text="Register Student",
            command=self.register_student,
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40
        )
        self.register_button.grid(row=9, column=0, padx=20, pady=(20, 10), sticky="ew")
        
        # Status message
        self.status_label = ctk.CTkLabel(
            self.form_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="green"
        )
        self.status_label.grid(row=10, column=0, padx=20, pady=(5, 20), sticky="ew")
        
        # Create camera frame
        self.camera_frame = ctk.CTkFrame(self)
        self.camera_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        
        # Configure camera frame grid layout
        self.camera_frame.grid_rowconfigure(0, weight=0)  # Title
        self.camera_frame.grid_rowconfigure(1, weight=1)  # Camera feed
        self.camera_frame.grid_rowconfigure(2, weight=0)  # Progress
        self.camera_frame.grid_rowconfigure(3, weight=0)  # Controls
        self.camera_frame.grid_rowconfigure(4, weight=0)  # Note
        self.camera_frame.grid_columnconfigure(0, weight=1)
        
        # Camera title
        self.camera_title = ctk.CTkLabel(
            self.camera_frame,
            text="Capture Face Images",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.camera_title.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        
        # Camera container - fixed size wrapper to maintain aspect ratio
        camera_container = ctk.CTkFrame(self.camera_frame, fg_color="transparent", width=640, height=480)
        camera_container.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        camera_container.grid_propagate(False)  # Prevent container from resizing
        camera_container.grid_columnconfigure(0, weight=1)
        camera_container.grid_rowconfigure(0, weight=1)
        
        # Create black background for camera view
        bg_color = "black" if ctk.get_appearance_mode() == "Dark" else "#333333"
        
        # Camera feed - use a label to display the video
        self.camera_label = ctk.CTkLabel(
            camera_container,
            text="Camera feed will appear here",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=bg_color,
            text_color="white",
            corner_radius=8
        )
        self.camera_label.grid(row=0, column=0, sticky="nsew")
        
        # Progress indicator for multiple captures
        self.progress_frame = ctk.CTkFrame(self.camera_frame)
        self.progress_frame.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.progress_frame.grid_columnconfigure(0, weight=1)
        
        self.progress_label = ctk.CTkLabel(
            self.progress_frame,
            text=f"Captured: 0/{self.max_captures}",
            font=ctk.CTkFont(size=12)
        )
        self.progress_label.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="w")
        
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame)
        self.progress_bar.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="ew")
        self.progress_bar.set(0)
        
        # Camera controls
        self.controls_frame = ctk.CTkFrame(self.camera_frame)
        self.controls_frame.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="ew")
        
        self.controls_frame.grid_columnconfigure(0, weight=1)
        self.controls_frame.grid_columnconfigure(1, weight=1)
        
        # Start Camera button
        self.start_button = ctk.CTkButton(
            self.controls_frame,
            text="Start Camera",
            command=self.start_camera,
            font=ctk.CTkFont(size=14),
            height=35
        )
        self.start_button.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="ew")
        
        # Capture button
        self.capture_button = ctk.CTkButton(
            self.controls_frame,
            text="Capture Image",
            command=self.capture_image,
            font=ctk.CTkFont(size=14),
            height=35,
            state="disabled"
        )
        self.capture_button.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="ew")
        
        # Capture note
        self.capture_note = ctk.CTkLabel(
            self.camera_frame,
            text="Please capture 5 different face angles for better recognition",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.capture_note.grid(row=4, column=0, padx=20, pady=(0, 10), sticky="ew")
    
    def _init_face_detection(self):
        """Initialize face detection components"""
        try:
            # Load Haar cascade classifier
            haar_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                     "resources", "haarcascades", 
                                     "haarcascade_frontalface_default.xml")
            
            # Check if cascade file exists, otherwise try OpenCV's built-in path
            if not os.path.exists(haar_path):
                haar_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                
            self.face_cascade = cv2.CascadeClassifier(haar_path)
            
            if self.face_cascade.empty():
                logger.error("Failed to load face cascade. Using built-in OpenCV cascade.")
                self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                
            logger.info("Face detection initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing face detection: {e}")
            # Set a fallback cascade
            self.face_cascade = None
    
    def start_camera(self):
        """Start the camera feed"""
        if self.is_capturing:
            self.stop_camera()
            return
        
        try:
            # Initialize the camera with DirectShow (Windows) or fallback to default
            try:
                self.camera_feed = cv2.VideoCapture(self.camera_id, cv2.CAP_DSHOW)
                if not self.camera_feed.isOpened():
                    logger.warning("DirectShow failed, trying default method")
                    self.camera_feed = cv2.VideoCapture(self.camera_id)
            except Exception:
                logger.warning("DirectShow not supported, using default method")
                self.camera_feed = cv2.VideoCapture(self.camera_id)
            
            if not self.camera_feed.isOpened():
                self.show_status("Failed to open camera. Please check your camera connection.", "red")
                logger.error(f"Failed to open camera with ID: {self.camera_id}")
                return
            
            # Set resolution
            self.camera_feed.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera_feed.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
            # Read a test frame
            ret, frame = self.camera_feed.read()
            if not ret:
                self.show_status("Failed to read from camera", "red")
                logger.error("Failed to read initial frame from camera")
                self.camera_feed.release()
                self.camera_feed = None
                return
            
            # Update UI
            self.is_capturing = True
            self.start_button.configure(
                text="Stop Camera",
                fg_color=("#e74c3c", "#c0392b")  # Red color for stop
            )
            self.capture_button.configure(state="normal")
            
            # Log camera start
            logger.info("Camera started for student registration")
            self.show_status("Camera started successfully", "green")
            
            # Start the camera loop in a separate thread
            self.camera_thread = threading.Thread(target=self._camera_loop)
            self.camera_thread.daemon = True
            self.camera_thread.start()
            
        except Exception as e:
            self.show_status(f"Failed to start camera: {str(e)}", "red")
            logger.error(f"Error starting camera: {e}")
            
    def stop_camera(self):
        """Stop the camera feed"""
        logger.info("Stopping camera feed")
        
        try:
            # Set flag to stop the camera loop
            self.is_capturing = False
            
            # Wait for camera loop to finish
            if self.camera_thread and self.camera_thread.is_alive():
                self.camera_thread.join(timeout=1.0)
                self.camera_thread = None
            
            # Release OpenCV resources
            if self.camera_feed and self.camera_feed.isOpened():
                self.camera_feed.release()
                self.camera_feed = None
            
            # Update UI safely after camera is stopped
            self.after(100, self._reset_camera_ui)
            
            logger.info("Camera feed stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping camera: {e}")
            # Still try to update UI even if there was an error
            self.after(100, self._reset_camera_ui)
    
    def _reset_camera_ui(self):
        """Reset UI elements after camera stops"""
        self.is_capturing = False
        self.start_button.configure(
            text="Start Camera",
            fg_color=("#3a7ebf", "#1f538d")  # Blue color for start
        )
        self.capture_button.configure(state="disabled")
        self.show_status("Camera stopped", "blue")
    
    def _camera_loop(self):
        """Process frames from the camera in a background thread"""
        try:
            logger.info("Camera loop started")
            frame_count = 0
            last_fps_time = time.time()
            
            while self.is_capturing and self.camera_feed and self.camera_feed.isOpened():
                # Read frame from camera
                ret, frame = self.camera_feed.read()
                
                if not ret or frame is None:
                    logger.warning("Failed to read frame from camera")
                    time.sleep(0.1)
                    continue
                
                # Save current frame for capture
                self.current_frame = frame.copy()
                
                # Process the frame
                processed_frame = self._process_camera_frame(frame)
                
                # Convert to PIL Image for display
                pil_image = Image.fromarray(processed_frame)
                
                # Update the UI in the main thread
                self.after(0, lambda img=pil_image: self._update_camera_display(img))
                
                # Calculate FPS
                frame_count += 1
                current_time = time.time()
                elapsed = current_time - last_fps_time
                
                if elapsed >= 1.0:
                    fps = frame_count / elapsed
                    frame_count = 0
                    last_fps_time = current_time
                
                # Limit frame rate to reduce CPU usage
                time.sleep(0.033)  # ~30 FPS
                
        except Exception as e:
            logger.error(f"Error in camera loop: {e}")
        finally:
            logger.info("Camera loop terminated")
            # Release camera resources if still running
            if self.camera_feed is not None:
                try:
                    self.camera_feed.release()
                except:
                    pass
                self.camera_feed = None
                
            # Reset UI safely
            if self.winfo_exists():
                self.after(0, self._reset_camera_ui)
    
    def _update_camera_display(self, img):
        """Update camera display with the latest frame"""
        try:
            if img is None:
                return
                
            if hasattr(self, 'camera_label') and self.camera_label.winfo_exists():
                # Get the current size of the camera label
                width = self.camera_label.winfo_width() or 640
                height = self.camera_label.winfo_height() or 480
                
                # Create CTkImage for better display quality
                ctk_img = ctk.CTkImage(
                    light_image=img,
                    dark_image=img,
                    size=(width, height)
                )
                
                # Update the label
                self.camera_label.configure(image=ctk_img, text="")
                
                # Keep a reference to prevent garbage collection
                self.current_image = ctk_img
                
        except Exception as e:
            logger.error(f"Error updating camera display: {e}")
            
    def _process_camera_frame(self, frame):
        """Process a camera frame with face detection"""
        try:
            # Flip horizontally for a mirror effect
            frame = cv2.flip(frame, 1)
            
            # Convert to RGB for display
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Detect faces in the frame
            faces = self.detect_faces(frame)
            
            # Draw rectangles around detected faces
            for (x, y, w, h) in faces:
                cv2.rectangle(rgb_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                
                # Add a background behind the text for better readability
                label_background = rgb_frame[max(0, y-25):y, x:min(x+w, rgb_frame.shape[1]-1)]
                if label_background.size > 0:
                    label_background[:] = (70, 70, 200)  # Blue background
                
                # Show text "Face Detected"
                cv2.putText(rgb_frame, "Face Detected", (x+5, y-10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
            return rgb_frame
            
        except Exception as e:
            logger.error(f"Error processing camera frame: {e}")
            return frame if frame is not None else np.zeros((480, 640, 3), dtype=np.uint8)
    
    def capture_image(self):
        """Capture a face image for registration"""
        if not self.is_capturing:
            self.show_status("Camera not started. Please start the camera first.", "red")
            return
        
        if self.capture_count >= self.max_captures:
            self.show_status("Maximum number of images already captured.", "orange")
            return
        
        # Check if form fields are filled
        student_id = self.id_entry.get().strip()
        if not student_id:
            self.show_status("Please enter a student ID before capturing.", "red")
            self.id_entry.focus_set()
            return
        
        # Create directory structure that matches face_detector expectations
        # Main training directory path - should be src/data/training_images/[student_id]
        src_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        training_dir = os.path.join(src_dir, "data", "training_images", student_id)
        os.makedirs(training_dir, exist_ok=True)
        
        # Capture the current frame
        if hasattr(self, 'current_frame') and self.current_frame is not None:
            try:
                # Apply face detection to ensure a face is present
                gray = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2GRAY)
                face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
                
                if len(faces) == 0:
                    self.show_status("No face detected. Please align your face with the camera.", "red")
                    return
                
                if len(faces) > 1:
                    self.show_status("Multiple faces detected. Please ensure only one face is visible.", "red")
                    return
                
                # Save the captured frame using the expected naming convention: student_id_count.jpg
                img_path = os.path.join(training_dir, f"{student_id}_{self.capture_count}.jpg")
                cv2.imwrite(img_path, self.current_frame)
                
                # Add to captured images list
                self.captured_images.append(img_path)
                
                # Increment counter and update progress
                self.capture_count += 1
                self.update_progress()
                
                # Show success message
                self.show_status(f"Image {self.capture_count}/{self.max_captures} captured successfully!", "green")
                
                # Flash effect for the camera label to indicate capture
                original_bg = self.camera_label.cget("fg_color")
                self.camera_label.configure(fg_color="green")
                self.after(200, lambda: self.camera_label.configure(fg_color=original_bg))
                
                # Auto-register if all images captured
                if self.capture_count >= self.max_captures:
                    self.show_status("All images captured! Processing registration...", "blue")
                    self.after(1000, self.register_student)
                
            except Exception as e:
                logger.error(f"Error capturing image: {e}")
                self.show_status(f"Error capturing image: {e}", "red")
        else:
            self.show_status("No camera frame available. Try restarting the camera.", "red")
    
    def update_progress(self):
        """Update the progress bar and label for captures"""
        progress = self.capture_count / self.max_captures
        self.progress_bar.set(progress)
        self.progress_label.configure(text=f"Captured: {self.capture_count}/{self.max_captures}")
    
    def register_student(self):
        """Register a new student with captured images"""
        try:
            # Get student details
            student_id = self.id_entry.get().strip()
            student_name = self.name_entry.get().strip()
            course = self.course_entry.get().strip()
            year = self.year_var.get().strip()
            
            # Validate input
            if not student_id:
                self.show_status("Please enter a Student ID", "red")
                return
                
            if not student_name:
                self.show_status("Please enter a Student Name", "red")
                return
                
            # Check if we have captured at least one image
            if not hasattr(self, 'captured_images') or not self.captured_images:
                # Use modern dialog confirmation instead of messagebox
                self._show_confirmation_dialog(
                    "No images captured",
                    "You haven't captured any images. Would you like to register without images?",
                    lambda result: self._complete_registration(result, student_id, student_name, course, year)
                )
                return
                
            # Show confirmation dialog
            self._show_confirmation_dialog(
                "Confirm Registration",
                f"Register student {student_name} (ID: {student_id}) with {len(self.captured_images)} images?",
                lambda result: self._complete_registration(result, student_id, student_name, course, year)
            )
            
        except Exception as e:
            logger.error(f"Error in student registration: {e}")
            self.show_status(f"Error in registration: {e}", "red")
            
    def _show_confirmation_dialog(self, title, message, callback):
        """Show a modern confirmation dialog and call the callback with the result"""
        try:
            # Create dialog
            dialog = ctk.CTkToplevel(self)
            dialog.title(title)
            dialog.geometry("400x200")
            dialog.transient(self)
            dialog.grab_set()
            
            # Make dialog modal
            dialog.focus_set()
            
            # Center the dialog
            dialog.update_idletasks()
            x = self.winfo_rootx() + (self.winfo_width() - dialog.winfo_width()) // 2
            y = self.winfo_rooty() + (self.winfo_height() - dialog.winfo_height()) // 2
            dialog.geometry(f"+{x}+{y}")
            
            # Add message
            message_label = ctk.CTkLabel(
                dialog, 
                text=message,
                wraplength=350,
                font=ctk.CTkFont(size=14),
                anchor="center",
                justify="center"
            )
            message_label.pack(pady=(30, 20), padx=20, fill="both", expand=True)
            
            # Buttons frame
            button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
            button_frame.pack(pady=(0, 20), padx=20, fill="x")
            
            # Cancel button
            cancel_button = ctk.CTkButton(
                button_frame,
                text="Cancel",
                command=lambda: self._handle_dialog_result(dialog, callback, False),
                fg_color="transparent",
                border_width=1,
                text_color=("gray10", "gray90")
            )
            cancel_button.pack(side="left", padx=(0, 10), fill="x", expand=True)
            
            # Confirm button
            confirm_button = ctk.CTkButton(
                button_frame,
                text="Confirm",
                command=lambda: self._handle_dialog_result(dialog, callback, True)
            )
            confirm_button.pack(side="left", fill="x", expand=True)
            
            # Handle dialog closure
            dialog.protocol("WM_DELETE_WINDOW", lambda: self._handle_dialog_result(dialog, callback, False))
            
        except Exception as e:
            logger.error(f"Error showing confirmation dialog: {e}")
            # Fallback to simple callback
            callback(False)
            
    def _handle_dialog_result(self, dialog, callback, result):
        """Handle dialog result and cleanup"""
        dialog.grab_release()
        dialog.destroy()
        callback(result)
            
    def _complete_registration(self, confirmed, student_id, student_name, course, year):
        """Complete the registration process after confirmation"""
        if not confirmed:
            self.show_status("Registration cancelled", "blue")
            return
            
        # Proceed with registration
        self.show_status(f"Registering student {student_name}...", "blue")
        
        # Save student details
        if self.save_student_details(student_id, student_name, course, year):
            # Show success message
            self.show_status(f"Student {student_name} registered successfully!", "green")
            
            # Reset the form after a short delay
            self.after(2000, self.reset_form)
            
            # Trigger model training if we have images
            if hasattr(self, 'captured_images') and self.captured_images:
                self.after(500, self.trigger_model_training)
        else:
            self.show_status("Failed to register student", "red")
    
    def save_student_details(self, student_id, name, course, year):
        """
        Save student details to CSV files
        
        This saves to both the legacy StudentDetails.csv file and the 
        face_detector compatible data/students.csv file
        """
        try:
            # Validate inputs
            if not student_id or not isinstance(student_id, str):
                logger.error(f"Invalid student ID: {student_id}")
                return False
            
            # First, save to legacy CSV for backward compatibility
            legacy_csv_path = os.path.join("StudentDetails", "StudentDetails.csv")
            os.makedirs(os.path.dirname(legacy_csv_path), exist_ok=True)
            
            # Create columns if file doesn't exist
            if not os.path.isfile(legacy_csv_path):
                df_legacy = pd.DataFrame(columns=["ID", "Name", "Course", "Year", "RegisteredDate"])
            else:
                try:
                    df_legacy = pd.read_csv(legacy_csv_path)
                    # Ensure all required columns exist
                    for col in ["ID", "Name", "Course", "Year", "RegisteredDate"]:
                        if col not in df_legacy.columns:
                            df_legacy[col] = ""
                except Exception as csv_err:
                    logger.error(f"Error reading legacy CSV: {csv_err}")
                    # Create a new DataFrame if reading fails
                    df_legacy = pd.DataFrame(columns=["ID", "Name", "Course", "Year", "RegisteredDate"])
            
            # Check if the student ID already exists
            if "ID" in df_legacy.columns and student_id in df_legacy["ID"].values:
                # Update existing record
                idx = df_legacy.index[df_legacy["ID"] == student_id][0]
                df_legacy.at[idx, "Name"] = name
                df_legacy.at[idx, "Course"] = course
                df_legacy.at[idx, "Year"] = year
                df_legacy.at[idx, "RegisteredDate"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            else:
                # Add new record
                new_row = {
                    "ID": student_id,
                    "Name": name,
                    "Course": course,
                    "Year": year,
                    "RegisteredDate": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                df_legacy = pd.concat([df_legacy, pd.DataFrame([new_row])], ignore_index=True)
            
            # Save legacy CSV
            df_legacy.to_csv(legacy_csv_path, index=False)
            
            # Now, save to the face_detector compatible CSV
            face_detector_csv_path = os.path.join("data", "students.csv")
            os.makedirs(os.path.dirname(face_detector_csv_path), exist_ok=True)
            
            if os.path.isfile(face_detector_csv_path):
                try:
                    df_face = pd.read_csv(face_detector_csv_path)
                    # Ensure required columns exist
                    for col in ["ID", "Name", "Course", "Year"]:
                        if col not in df_face.columns:
                            df_face[col] = ""
                except Exception as face_csv_err:
                    logger.error(f"Error reading face detector CSV: {face_csv_err}")
                    # Create a new DataFrame if reading fails
                    df_face = pd.DataFrame(columns=["ID", "Name", "Course", "Year"])
                
                # Check if ID exists
                if "ID" in df_face.columns and student_id in df_face["ID"].values:
                    # Update existing
                    idx = df_face.index[df_face["ID"] == student_id][0]
                    df_face.at[idx, "Name"] = name
                    df_face.at[idx, "Course"] = course
                    df_face.at[idx, "Year"] = year
                else:
                    # Add new
                    new_row = {
                        "ID": student_id,
                        "Name": name,
                        "Course": course,
                        "Year": year
                    }
                    df_face = pd.concat([df_face, pd.DataFrame([new_row])], ignore_index=True)
            else:
                # Create new DataFrame
                df_face = pd.DataFrame([{
                    "ID": student_id,
                    "Name": name,
                    "Course": course,
                    "Year": year
                }])
            
            # Save face detector CSV
            df_face.to_csv(face_detector_csv_path, index=False)
            
            logger.info(f"Student {name} (ID: {student_id}) registered successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error saving student details: {e}")
            return False
    
    def trigger_model_training(self):
        """
        Trigger face recognizer model training 
        
        This notifies the user that images have been captured and training is needed
        """
        try:
            # Show a notification
            info_frame = ctk.CTkFrame(self, corner_radius=10, fg_color=("#3498db", "#2980b9"))
            info_frame.place(relx=0.5, rely=0.7, anchor="center")
            
            info_label = ctk.CTkLabel(
                info_frame,
                text="Face images captured successfully!\nPlease visit the Training section to update the recognition model.",
                font=ctk.CTkFont(size=14),
                text_color="white"
            )
            info_label.pack(padx=30, pady=20)
            
            # Remove after 4 seconds
            self.after(4000, info_frame.destroy)
            
        except Exception as e:
            logger.error(f"Error triggering model training: {e}")
    
    def reset_form(self):
        """Reset the form and captured images"""
        self.id_entry.delete(0, 'end')
        self.name_entry.delete(0, 'end')
        self.course_entry.delete(0, 'end')
        self.year_var.set(str(datetime.now().year))
        
        # Reset captured images
        self.captured_images = []
        self.capture_count = 0
        self.update_progress()
    
    def show_status(self, message, color="black"):
        """Show a status message"""
        try:
            if hasattr(self, 'status_label') and self.status_label.winfo_exists():
                self.status_label.configure(text=message, text_color=color)
            logger.info(message)
        except Exception as e:
            logger.error(f"Error showing status: {e}")
    
    def _resize_image_to_fit(self, pil_img, width, height):
        """Resize an image to fit within specified dimensions while preserving aspect ratio"""
        try:
            # Get original dimensions
            w, h = pil_img.size
            
            # Calculate aspect ratios
            aspect_img = w / h
            aspect_win = width / height
            
            # Determine new dimensions based on aspect ratio
            if aspect_img > aspect_win:
                # Image is wider than the target aspect ratio
                new_w = width
                new_h = int(width / aspect_img)
            else:
                # Image is taller than the target aspect ratio
                new_h = height
                new_w = int(height * aspect_img)
            
            # Ensure dimensions are at least 1 pixel
            new_w = max(1, new_w)
            new_h = max(1, new_h)
            
            # Resize the image
            return pil_img.resize((new_w, new_h), Image.LANCZOS)
        except Exception as e:
            logger.error(f"Error resizing image: {e}")
            # If resize fails, return original image
            return pil_img
    
    def cleanup(self):
        """Clean up resources when the view is closed"""
        # Stop camera if running
        if self.is_capturing:
            self.is_capturing = False
            if self.camera_feed and hasattr(self.camera_feed, 'release'):
                self.camera_feed.release()
                self.camera_feed = None
        
        # Cancel any pending after calls
        if hasattr(self, 'after_ids'):
            for after_id in self.after_ids:
                try:
                    self.after_cancel(after_id)
                except Exception as e:
                    logger.error(f"Error canceling after ID {after_id}: {e}")
            # Clear the list
            self.after_ids = []
            
        logger.info("Student Registration View resources cleaned up")
        return True

    def detect_faces(self, frame):
        """Detect faces in the given frame using Haar cascade"""
        try:
            if self.face_cascade is None:
                self._init_face_detection()
                
            if self.face_cascade is None:
                logger.error("Face cascade not available for detection")
                return []
                
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30),
                flags=cv2.CASCADE_SCALE_IMAGE
            )
            
            return faces
        except Exception as e:
            logger.error(f"Error detecting faces: {e}")
            return []

    def _update_fps(self, fps):
        """Update the FPS label"""
        try:
            if hasattr(self, 'fps_label') and self.fps_label.winfo_exists():
                self.fps_label.configure(text=f"FPS: {fps:.2f}")
        except Exception as e:
            logger.error(f"Error updating FPS: {e}")