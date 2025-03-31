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
    
    def __init__(self, master):
        """
        Initialize the training view
        
        Args:
            master: Parent widget
        """
        super().__init__(master)
        
        # Initialize variables
        self.is_training = False
        self.training_thread = None
        self.progress_value = 0
        
        # Track after IDs for cleanup
        self.after_ids = []
        
        # Create UI elements
        self._setup_ui()
        
        logger.info("Training View initialized")
    
    def _setup_ui(self):
        """Set up the training view UI"""
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Title
        self.grid_rowconfigure(1, weight=0)  # Info panel
        self.grid_rowconfigure(2, weight=1)  # Content area
        self.grid_rowconfigure(3, weight=0)  # Controls
        
        # Title
        self.title_label = ctk.CTkLabel(
            self,
            text="Face Recognition Training",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.title_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        
        # Info panel
        self.info_frame = ctk.CTkFrame(self)
        self.info_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        
        self.info_text = ctk.CTkLabel(
            self.info_frame,
            text="Train the face recognition model with student images.\n" +
                 "This will improve recognition accuracy and performance.",
            font=ctk.CTkFont(size=14),
            anchor="w",
            justify="left"
        )
        self.info_text.pack(padx=20, pady=20, fill="both")
        
        # Content area
        self.content_frame = ctk.CTkFrame(self)
        self.content_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=0)  # Stats
        self.content_frame.grid_rowconfigure(1, weight=1)  # Training info and camera
        
        # Stats frame
        self.stats_frame = ctk.CTkFrame(self.content_frame)
        self.stats_frame.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        
        self.stats_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        # Student count
        self.student_frame = ctk.CTkFrame(self.stats_frame, fg_color=("gray90", "gray20"))
        self.student_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        
        self.student_count_label = ctk.CTkLabel(
            self.student_frame,
            text="0",
            font=ctk.CTkFont(size=36, weight="bold")
        )
        self.student_count_label.pack(pady=(15, 5))
        
        ctk.CTkLabel(self.student_frame, text="Students").pack(pady=(0, 15))
        
        # Image count
        self.image_frame = ctk.CTkFrame(self.stats_frame, fg_color=("gray90", "gray20"))
        self.image_frame.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        self.image_count_label = ctk.CTkLabel(
            self.image_frame,
            text="0",
            font=ctk.CTkFont(size=36, weight="bold")
        )
        self.image_count_label.pack(pady=(15, 5))
        
        ctk.CTkLabel(self.image_frame, text="Images").pack(pady=(0, 15))
        
        # Model info
        self.model_frame = ctk.CTkFrame(self.stats_frame, fg_color=("gray90", "gray20"))
        self.model_frame.grid(row=0, column=2, padx=10, pady=10, sticky="ew")
        
        self.model_status_label = ctk.CTkLabel(
            self.model_frame,
            text="Not Trained",
            text_color="orange",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.model_status_label.pack(pady=(15, 5))
        
        self.model_date_label = ctk.CTkLabel(
            self.model_frame,
            text="No model available",
            font=ctk.CTkFont(size=12)
        )
        self.model_date_label.pack(pady=(0, 15))
        
        # Training info frame - Now includes camera feed and training log side by side
        self.training_info_frame = ctk.CTkFrame(self.content_frame)
        self.training_info_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        
        self.training_info_frame.grid_columnconfigure(0, weight=1)
        self.training_info_frame.grid_columnconfigure(1, weight=1)
        self.training_info_frame.grid_rowconfigure(0, weight=0)  # Title
        self.training_info_frame.grid_rowconfigure(1, weight=1)  # Log/Camera
        self.training_info_frame.grid_rowconfigure(2, weight=0)  # Progress
        
        # Left Side: Camera feed
        self.camera_frame = ctk.CTkFrame(self.training_info_frame)
        self.camera_frame.grid(row=1, column=0, padx=(20, 10), pady=(0, 10), sticky="nsew")
        
        self.camera_title = ctk.CTkLabel(
            self.training_info_frame,
            text="Camera Feed",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w"
        )
        self.camera_title.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        # Camera display
        self.camera_label = ctk.CTkLabel(
            self.camera_frame,
            text="Camera feed will appear here",
            height=300
        )
        self.camera_label.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Right Side: Training log title
        self.log_title = ctk.CTkLabel(
            self.training_info_frame,
            text="Training Log",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w"
        )
        self.log_title.grid(row=0, column=1, padx=20, pady=(20, 10), sticky="w")
        
        # Training log
        self.log_frame = ctk.CTkFrame(self.training_info_frame)
        self.log_frame.grid(row=1, column=1, padx=(10, 20), pady=(0, 10), sticky="nsew")
        
        # Use native Tkinter Text widget for the log
        self.log_text = tk.Text(
            self.log_frame,
            wrap="word",
            font=("Consolas", 11),
            bg="#2b2b2b" if ctk.get_appearance_mode() == "Dark" else "#f0f0f0",
            fg="#e0e0e0" if ctk.get_appearance_mode() == "Dark" else "#000000",
            height=10
        )
        self.log_text.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        
        # Scrollbar for log
        self.log_scrollbar = ctk.CTkScrollbar(self.log_frame, command=self.log_text.yview)
        self.log_scrollbar.pack(side="right", fill="y")
        self.log_text.configure(yscrollcommand=self.log_scrollbar.set)
        
        # Disable editing
        self.log_text.configure(state="disabled")
        
        # Progress frame
        self.progress_frame = ctk.CTkFrame(self.training_info_frame)
        self.progress_frame.grid(row=2, column=0, columnspan=2, padx=20, pady=(0, 20), sticky="ew")
        
        self.progress_frame.grid_columnconfigure(0, weight=1)
        
        # Progress bar
        self.progress_label = ctk.CTkLabel(
            self.progress_frame,
            text="Progress: 0%",
            font=ctk.CTkFont(size=12),
            anchor="w"
        )
        self.progress_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame)
        self.progress_bar.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.progress_bar.set(0)
        
        # Controls frame
        self.controls_frame = ctk.CTkFrame(self)
        self.controls_frame.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="ew")
        
        self.controls_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        # Refresh button
        self.refresh_button = ctk.CTkButton(
            self.controls_frame,
            text="Refresh Stats",
            command=self.refresh_stats,
            height=40,
            corner_radius=10
        )
        self.refresh_button.grid(row=0, column=0, padx=(20, 10), pady=20, sticky="ew")
        
        # Auto-capture checkbox
        self.auto_capture_var = ctk.BooleanVar(value=True)
        self.auto_capture_checkbox = ctk.CTkCheckBox(
            self.controls_frame,
            text="Auto-Capture",
            variable=self.auto_capture_var,
            height=40
        )
        self.auto_capture_checkbox.grid(row=0, column=1, padx=10, pady=20, sticky="ew")
        
        # Train button
        self.train_button = ctk.CTkButton(
            self.controls_frame,
            text="Start Training",
            command=self.start_training,
            height=40,
            corner_radius=10,
            fg_color="#27ae60",
            hover_color="#219653"
        )
        self.train_button.grid(row=0, column=2, padx=(10, 20), pady=20, sticky="ew")
        
        # Initialize camera variables
        self.camera_feed = None
        self.camera_thread = None
        self.is_capturing = False
        self.camera_id = 0
        
        # Initialize stats
        self.refresh_stats()
    
    def refresh_stats(self):
        """Refresh the statistics about students and images"""
        try:
            # Get student count from TrainingImage directory
            student_directories = 0
            image_count = 0
            
            training_dir = "TrainingImage"
            if os.path.exists(training_dir):
                # Count student directories
                student_ids = set()
                
                # Walk through the directory
                for root, dirs, files in os.walk(training_dir):
                    for file in files:
                        if file.endswith(('.jpg', '.jpeg', '.png')):
                            # Extract student ID from filename
                            try:
                                student_id = file.split('_')[0]
                                student_ids.add(student_id)
                                image_count += 1
                            except:
                                pass
                
                student_directories = len(student_ids)
            
            # Update UI
            self.student_count_label.configure(text=str(student_directories))
            self.image_count_label.configure(text=str(image_count))
            
            # Check if model exists
            model_path = os.path.join("TrainingImageLabel", "Trainner.yml")
            if os.path.exists(model_path):
                # Get modification time
                mod_time = os.path.getmtime(model_path)
                mod_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mod_time))
                
                self.model_status_label.configure(text="Trained", text_color="green")
                self.model_date_label.configure(text=f"Last updated: {mod_time_str}")
            else:
                self.model_status_label.configure(text="Not Trained", text_color="orange")
                self.model_date_label.configure(text="No model available")
            
            self.log_message("Statistics refreshed. Ready to train.")
            
        except Exception as e:
            logger.error(f"Error refreshing stats: {e}")
            self.log_message(f"Error refreshing stats: {str(e)}", level="error")
    
    def start_training(self):
        """Start or stop the training process"""
        if self.is_training:
            # Stop training if already in progress
            self.is_training = False
            self.train_button.configure(
                text="Start Training",
                fg_color="#27ae60",
                hover_color="#219653"
            )
            self.log_message("Training canceled by user", level="warning")
            
            # Stop camera if it's running
            self.stop_camera()
            return
        
        # Start training
        self.is_training = True
        self.train_button.configure(
            text="Cancel Training",
            fg_color="#e74c3c",
            hover_color="#c0392b"
        )
        
        # Reset progress
        self._update_progress(0)
        
        # Clear log
        self.log_text.configure(state="normal")
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state="disabled")
        
        # Start camera for auto-capture if enabled
        if self.auto_capture_var.get():
            self.start_camera()
        
        # Start training in a separate thread
        self.training_thread = threading.Thread(target=self._training_process)
        self.training_thread.daemon = True
        self.training_thread.start()
        
        self.log_message("Training process started")
    
    def start_camera(self):
        """Start the camera feed"""
        if self.is_capturing:
            return
        
        try:
            # Initialize the camera
            self.camera_feed = cv2.VideoCapture(self.camera_id)
            
            if not self.camera_feed.isOpened():
                self.log_message("Failed to open camera. Please check your camera connection.", level="error")
                return
            
            # Update UI
            self.is_capturing = True
            
            # Start camera thread
            self.camera_thread = threading.Thread(target=self._camera_loop)
            self.camera_thread.daemon = True
            self.camera_thread.start()
            
            self.log_message("Camera started for training")
        
        except Exception as e:
            self.log_message(f"Error starting camera: {str(e)}", level="error")
    
    def stop_camera(self):
        """Stop the camera feed"""
        self.is_capturing = False
        
        if self.camera_feed is not None:
            self.camera_feed.release()
            self.camera_feed = None
        
        # Clear the camera label
        self.camera_label.configure(text="Camera feed will appear here", image=None)
        
        self.log_message("Camera stopped")
    
    def _camera_loop(self):
        """Main camera loop that runs in a separate thread"""
        last_update_time = time.time()
        frame_skip = 0  # For performance optimization
        
        while self.is_capturing and self.camera_feed is not None:
            try:
                # Read frame
                ret, frame = self.camera_feed.read()
                if not ret:
                    time.sleep(0.1)
                    continue
                
                # Skip frames for better performance (process every 2nd frame)
                frame_skip = (frame_skip + 1) % 2
                if frame_skip != 0:
                    continue
                
                # Process frame for display
                # Convert to RGB for display
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Detect faces
                face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, 1.3, 5)
                
                # Draw rectangle around faces
                for (x, y, w, h) in faces:
                    cv2.rectangle(rgb_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                
                # Convert to PIL Image
                img = Image.fromarray(rgb_frame)
                
                # Resize for display while maintaining aspect ratio
                img_width, img_height = img.size
                max_height = 300
                
                if img_height > max_height:
                    ratio = max_height / img_height
                    new_width = int(img_width * ratio)
                    img = img.resize((new_width, max_height), Image.LANCZOS)
                
                # Convert to CTkImage
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
                
                # Update display at lower frequency for better performance
                current_time = time.time()
                if current_time - last_update_time >= 0.1:  # Update at ~10 FPS
                    self.after(0, lambda: self.camera_label.configure(image=ctk_img, text=""))
                    last_update_time = current_time
                
            except Exception as e:
                logger.error(f"Error in camera loop: {e}")
                time.sleep(0.5)
        
        # Clear the camera label when done
        if not self.is_capturing:
            self.after(0, lambda: self.camera_label.configure(text="Camera feed will appear here", image=None))
    
    def _training_process(self):
        """The main training process that runs in a separate thread"""
        try:
            # Check if TrainingImage directory exists
            training_dir = "TrainingImage"
            if not os.path.exists(training_dir):
                os.makedirs(training_dir, exist_ok=True)
                self.log_message("Created Training Image directory", level="info")
            
            # Check if there are students to train
            student_ids = set()
            student_dirs = {}
            total_images = 0
            
            # Auto-capture mode
            if self.auto_capture_var.get() and self.is_capturing:
                self.log_message("Starting auto-capture mode...", level="info")
                
                # Get student info
                student_id = ""
                student_name = ""
                
                # Ask for student info
                def get_student_info():
                    nonlocal student_id, student_name
                    from tkinter import simpledialog
                    
                    student_id = simpledialog.askstring("Student ID", "Enter student ID:")
                    if not student_id:
                        return False
                        
                    student_name = simpledialog.askstring("Student Name", "Enter student name:")
                    if not student_name:
                        return False
                    
                    return True
                
                # Run on main thread
                self.after(0, lambda: self.after(100, lambda: setattr(self, '_student_info_result', get_student_info())))
                
                # Wait for result
                for _ in range(50):  # Wait up to 5 seconds
                    if hasattr(self, '_student_info_result'):
                        break
                    time.sleep(0.1)
                
                if not hasattr(self, '_student_info_result') or not self._student_info_result:
                    self.log_message("Student information not provided. Aborting auto-capture.", level="warning")
                    self.is_training = False
                    self._update_ui_after_training(success=False)
                    return
                
                delattr(self, '_student_info_result')
                
                # Auto-capture images
                self.log_message(f"Auto-capturing images for student {student_name} (ID: {student_id})", level="info")
                
                # Get number of images to capture
                num_images = 20  # Default
                
                # Create a proper student directory
                images_captured = 0
                last_capture_time = time.time()
                
                # Main capture loop
                while self.is_training and self.is_capturing and images_captured < num_images:
                    if not self.camera_feed or not self.camera_feed.isOpened():
                        self.log_message("Camera not available. Stopping auto-capture.", level="error")
                        break
                        
                    # Throttle captures (one every 0.5 seconds)
                    current_time = time.time()
                    if current_time - last_capture_time < 0.5:
                        time.sleep(0.1)
                        continue
                        
                    # Capture frame
                    ret, frame = self.camera_feed.read()
                    if not ret:
                        self.log_message("Failed to capture image from camera.", level="error")
                        time.sleep(0.5)
                        continue
                    
                    # Detect faces
                    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    faces = face_cascade.detectMultiScale(gray, 1.3, 5)
                    
                    if len(faces) == 0:
                        # No face detected
                        continue
                    
                    if len(faces) > 1:
                        # Multiple faces detected
                        self.log_message("Multiple faces detected. Ensure only one person is in frame.", level="warning")
                        time.sleep(1)
                        continue
                    
                    # Save image
                    image_filename = os.path.join(training_dir, f"{student_id}.{student_name}.{images_captured+1}.jpg")
                    cv2.imwrite(image_filename, frame)
                    
                    images_captured += 1
                    last_capture_time = current_time
                    
                    # Update progress
                    progress = (images_captured / num_images) * 50  # First half of progress bar
                    self._update_progress(progress)
                    
                    self.log_message(f"Captured image {images_captured}/{num_images}.", level="info")
                    
                    # Short delay to allow user to reposition
                    time.sleep(0.2)
                
                if images_captured > 0:
                    student_ids.add(student_id)
                    student_dirs[student_id] = images_captured
                    total_images += images_captured
                    self.log_message(f"Auto-capture completed. Captured {images_captured} images for student {student_name}.", level="info")
                else:
                    self.log_message("No images captured. Aborting training.", level="error")
                    self.is_training = False
                    self._update_ui_after_training(success=False)
                    return
            
            # Regular training process continues here
            # Find existing images
            if not student_ids:  # If we didn't auto-capture, scan directory
                image_files = []
                for ext in ('*.jpg', '*.jpeg', '*.png'):
                    image_files.extend(glob.glob(os.path.join(training_dir, "**", ext), recursive=True))
                
                if not image_files:
                    self.log_message("No training images found. Cannot train model.", level="error")
                    self.is_training = False
                    self._update_ui_after_training(success=False)
                    return
                
                # Count unique student IDs from filenames
                for image_path in image_files:
                    filename = os.path.basename(image_path)
                    try:
                        student_id = filename.split('.')[0]
                        student_ids.add(student_id)
                        
                        if student_id not in student_dirs:
                            student_dirs[student_id] = 0
                        student_dirs[student_id] += 1
                        total_images += 1
                    except:
                        pass
            
            self.log_message(f"Found {len(student_ids)} students with a total of {total_images} images")
            
            # Create TrainingImageLabel directory if it doesn't exist
            label_dir = "TrainingImageLabel"
            os.makedirs(label_dir, exist_ok=True)
            
            # Start face recognition training
            self.log_message("Initializing face detector...")
            
            # Initialize face detector
            face_detector = FaceDetector(detection_method="haarcascade")
            
            self.log_message("Preparing training data...")
            
            # Lists for training data and labels
            faces = []
            ids = []
            
            # Process each student's images
            processed_images = 0
            
            # Get all image files again if we didn't do it earlier
            if self.auto_capture_var.get():
                image_files = []
                for ext in ('*.jpg', '*.jpeg', '*.png'):
                    image_files.extend(glob.glob(os.path.join(training_dir, "**", ext), recursive=True))
            
            for i, image_path in enumerate(image_files):
                if not self.is_training:
                    # User canceled training
                    break
                
                try:
                    # Read the image
                    img = cv2.imread(image_path)
                    
                    # Convert to grayscale
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    
                    # Get student ID from filename
                    filename = os.path.basename(image_path)
                    student_id = filename.split('.')[0]
                    
                    # Detect faces
                    face_locations = face_detector.detect_faces_only(gray)
                    
                    if face_locations:
                        for (x, y, w, h) in face_locations:
                            # Extract face ROI
                            face_roi = gray[y:y+h, x:x+w]
                            
                            # Add face and label
                            faces.append(face_roi)
                            ids.append(int(student_id))
                    
                    # Update progress - start from 50% if we did auto-capture
                    start_progress = 50 if self.auto_capture_var.get() else 0
                    progress = start_progress + ((i + 1) / len(image_files) * (100 - start_progress))
                    self._update_progress(progress)
                    
                    processed_images += 1
                    if (processed_images % 10 == 0) or (processed_images == len(image_files)):
                        self.log_message(f"Processed {processed_images}/{len(image_files)} images...")
                
                except Exception as e:
                    logger.error(f"Error processing image {image_path}: {e}")
                    self.log_message(f"Error with image {os.path.basename(image_path)}: {str(e)}", level="error")
            
            # Check if training was canceled
            if not self.is_training:
                self.log_message("Training canceled by user", level="warning")
                self._update_ui_after_training(success=False)
                return
            
            # Check if we have training data
            if len(faces) == 0 or len(ids) == 0:
                self.log_message("No valid face images found. Cannot train model.", level="error")
                self.is_training = False
                self._update_ui_after_training(success=False)
                return
            
            self.log_message(f"Starting model training with {len(faces)} face images...")
            
            # Train LBPH face recognizer
            recognizer = cv2.face.LBPHFaceRecognizer_create()
            recognizer.train(faces, np.array(ids))
            
            # Save the model
            model_path = os.path.join(label_dir, "Trainner.yml")
            recognizer.write(model_path)
            
            self.log_message(f"Model training completed successfully!")
            self.log_message(f"Model saved to {model_path}")
            
            # Training completed
            self.is_training = False
            self._update_ui_after_training(success=True)
            
        except Exception as e:
            logger.error(f"Error in training process: {e}")
            self.log_message(f"Training failed: {str(e)}", level="error")
            self.is_training = False
            self._update_ui_after_training(success=False)
    
    def _update_progress(self, value):
        """Update the progress bar and label"""
        # Schedule UI update in the main thread
        if self.winfo_exists():
            self.after(0, lambda: self._safe_update_progress(value))
    
    def _safe_update_progress(self, value):
        """Safe update for progress from the main thread"""
        try:
            self.progress_value = value
            if hasattr(self, 'progress_bar') and self.progress_bar.winfo_exists():
                self.progress_bar.set(value / 100)
            if hasattr(self, 'progress_label') and self.progress_label.winfo_exists():
                self.progress_label.configure(text=f"Progress: {int(value)}%")
        except Exception as e:
            logger.error(f"Error updating progress: {e}")
    
    def _update_ui_after_training(self, success):
        """Update UI elements after training is complete"""
        # Schedule UI update in the main thread
        if self.winfo_exists():
            self.after(0, lambda: self._safe_update_ui_after_training(success))
    
    def _safe_update_ui_after_training(self, success):
        """Safe update for UI from the main thread"""
        try:
            if hasattr(self, 'train_button') and self.train_button.winfo_exists():
                self.train_button.configure(text="Start Training", fg_color="#27ae60", hover_color="#219653")
            
            if success:
                if hasattr(self, 'progress_bar') and self.progress_bar.winfo_exists():
                    self.progress_bar.set(1.0)
                if hasattr(self, 'progress_label') and self.progress_label.winfo_exists():
                    self.progress_label.configure(text="Progress: 100%")
                # Refresh stats to show updated model info
                self.refresh_stats()
        except Exception as e:
            logger.error(f"Error updating UI after training: {e}")
    
    def log_message(self, message, level="info"):
        """Add a message to the log with timestamp"""
        # Schedule UI update in the main thread
        if self.winfo_exists():
            self.after(0, lambda: self._safe_log_message(message, level))
    
    def _safe_log_message(self, message, level="info"):
        """Safe method to update log messages from main thread"""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            full_message = f"[{timestamp}] {message}"
            
            # Set text color based on level
            text_color = "#333333"  # Default
            if level == "error":
                text_color = "#e74c3c"  # Red
            elif level == "warning":
                text_color = "#f39c12"  # Orange
            elif level == "success":
                text_color = "#27ae60"  # Green
            
            # Add to log text widget if it exists
            if hasattr(self, 'log_text') and self.log_text.winfo_exists():
                self.log_text.configure(state="normal")
                self.log_text.insert("end", full_message + "\n", level)
                self.log_text.tag_configure(level, foreground=text_color)
                self.log_text.configure(state="disabled")
                self.log_text.see("end")  # Scroll to end
            
            # Log to system logger
            if level == "error":
                logger.error(message)
            elif level == "warning":
                logger.warning(message)
            else:
                logger.info(message)
        except Exception as e:
            logger.error(f"Error updating log: {e}")
    
    def after(self, ms, func=None, *args):
        """Override after to track IDs for cleanup"""
        if func is not None:
            after_id = super().after(ms, func, *args)
            self.after_ids.append(after_id)
            return after_id
        return super().after(ms)
    
    def cleanup(self):
        """Clean up resources when view is closed"""
        # Stop camera if running
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
            
        return True
    
    def _stop_camera(self):
        """Stop the camera feed"""
        self.is_capturing = False
        
        if self.camera_feed is not None:
            self.camera_feed.release()
            self.camera_feed = None
        
        # Clear the camera label
        self.camera_label.configure(text="Camera feed will appear here", image=None)
        
        self.log_message("Camera stopped")
    
    def on_close(self):
        """Clean up resources when view is closed"""
        # Stop training if in progress
        self.is_training = False
        
        # Stop camera if running
        self._stop_camera()
        
        logger.info("Training View resources cleaned up") 