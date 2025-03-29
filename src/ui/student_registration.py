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
from PIL import Image, ImageTk
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
        self.camera_frame.grid_rowconfigure(2, weight=0)  # Controls
        self.camera_frame.grid_columnconfigure(0, weight=1)
        
        # Camera title
        self.camera_title = ctk.CTkLabel(
            self.camera_frame,
            text="Capture Face Images",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.camera_title.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        
        # Camera feed - use a label to display the video
        self.camera_label = ctk.CTkLabel(
            self.camera_frame,
            text="Camera feed will appear here",
            font=ctk.CTkFont(size=14),
            height=400
        )
        self.camera_label.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        
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
    
    def start_camera(self):
        """Start the camera feed"""
        if self.is_capturing:
            self.stop_camera()
            return
        
        try:
            # Initialize the camera
            self.camera_feed = cv2.VideoCapture(self.camera_id)
            
            if not self.camera_feed.isOpened():
                self.show_status("Failed to open camera. Please check your camera connection.", "red")
                logger.error(f"Failed to open camera with ID: {self.camera_id}")
                return
            
            # Update UI
            self.is_capturing = True
            self.start_button.configure(text="Stop Camera")
            self.capture_button.configure(state="normal")
            
            # Start camera thread
            self.camera_thread = threading.Thread(target=self._camera_loop)
            self.camera_thread.daemon = True
            self.camera_thread.start()
            
            self.show_status("Camera started. Position your face in the frame and capture.", "green")
            logger.info("Camera started for student registration")
        
        except Exception as e:
            self.show_status(f"Error starting camera: {str(e)}", "red")
            logger.error(f"Error starting camera: {e}")
    
    def stop_camera(self):
        """Stop the camera feed"""
        self.is_capturing = False
        
        if self.camera_feed is not None:
            self.camera_feed.release()
            self.camera_feed = None
        
        # Update UI
        self.start_button.configure(text="Start Camera")
        self.capture_button.configure(state="disabled")
        
        # Clear the camera label
        self.camera_label.configure(text="Camera feed will appear here", image=None)
        
        logger.info("Camera stopped for student registration")
    
    def _camera_loop(self):
        """Camera feed loop to update the UI with camera frames"""
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        while self.is_capturing:
            try:
                # Read frame
                ret, frame = self.camera_feed.read()
                if not ret:
                    logger.warning("Failed to read frame from camera")
                    time.sleep(0.1)
                    continue
                
                # Detect faces
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, 1.3, 5)
                
                # Draw rectangle around faces
                for (x, y, w, h) in faces:
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                
                # Convert to RGB for PIL
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Convert to PIL Image
                pil_img = Image.fromarray(rgb_frame)
                
                # Resize to fit in the label
                pil_img = self.resize_image_to_fit(pil_img, 500, 400)
                
                # Convert to PhotoImage
                tk_img = ImageTk.PhotoImage(pil_img)
                
                # Update label with new image
                self.camera_label.configure(image=tk_img, text="")
                self.camera_label.image = tk_img  # Keep a reference
            
            except Exception as e:
                logger.error(f"Error in camera loop: {e}")
                time.sleep(0.1)
        
        logger.info("Camera loop ended")
    
    def capture_image(self):
        """Capture an image from the camera feed"""
        if not self.is_capturing or self.camera_feed is None:
            self.show_status("Camera is not active. Please start camera first.", "red")
            return
        
        try:
            # Read frame
            ret, frame = self.camera_feed.read()
            if not ret:
                self.show_status("Failed to capture image.", "red")
                return
            
            # Detect faces
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.3, 5)
            
            if len(faces) == 0:
                self.show_status("No face detected. Please position your face in the frame.", "red")
                return
            
            if len(faces) > 1:
                self.show_status("Multiple faces detected. Please ensure only one face is in the frame.", "orange")
                return
            
            # Store the captured image
            self.captured_images.append(frame)
            self.capture_count += 1
            
            # Update progress
            self.update_progress()
            
            # If we've captured enough images, enable the register button
            if self.capture_count >= self.max_captures:
                self.show_status(f"All {self.max_captures} images captured. You can now register the student.", "green")
                self.stop_camera()
            else:
                self.show_status(f"Image {self.capture_count} captured. Please change face angle for next capture.", "green")
        
        except Exception as e:
            self.show_status(f"Error capturing image: {str(e)}", "red")
            logger.error(f"Error capturing image: {e}")
    
    def update_progress(self):
        """Update the progress bar and label for captures"""
        progress = self.capture_count / self.max_captures
        self.progress_bar.set(progress)
        self.progress_label.configure(text=f"Captured: {self.capture_count}/{self.max_captures}")
    
    def register_student(self):
        """Register a new student with the captured face images"""
        # Validate form
        student_id = self.id_entry.get().strip()
        name = self.name_entry.get().strip()
        course = self.course_entry.get().strip()
        year = self.year_var.get().strip()
        
        if not student_id or not name or not course:
            self.show_status("Please fill in all required fields.", "red")
            return
        
        # Validate images
        if self.capture_count < self.max_captures:
            self.show_status(f"Please capture {self.max_captures} face images before registering.", "red")
            return
        
        try:
            # Create directories if they don't exist
            training_dir = "TrainingImage"
            os.makedirs(training_dir, exist_ok=True)
            
            # Save images with proper naming convention
            for i, image in enumerate(self.captured_images):
                # Format: ID.Name.1.jpg, ID.Name.2.jpg, etc.
                image_filename = os.path.join(training_dir, f"{student_id}.{name}.{i+1}.jpg")
                cv2.imwrite(image_filename, image)
            
            # Update student details CSV
            self.save_student_details(student_id, name, course, year)
            
            # Reset form and captured images
            self.reset_form()
            
            # Show success message
            self.show_status(f"Student {name} registered successfully with ID {student_id}!", "green")
            logger.info(f"Student registered: {student_id} - {name}")
        
        except Exception as e:
            self.show_status(f"Error registering student: {str(e)}", "red")
            logger.error(f"Error registering student: {e}")
    
    def save_student_details(self, student_id, name, course, year):
        """Save student details to CSV file"""
        csv_path = os.path.join("StudentDetails", "StudentDetails.csv")
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        
        # Create columns if file doesn't exist
        if not os.path.isfile(csv_path):
            df = pd.DataFrame(columns=["ID", "Name", "Course", "Year", "RegisteredDate"])
        else:
            df = pd.read_csv(csv_path)
        
        # Check if the student ID already exists
        if student_id in df["ID"].values:
            # Update existing record
            idx = df.index[df["ID"] == student_id][0]
            df.at[idx, "Name"] = name
            df.at[idx, "Course"] = course
            df.at[idx, "Year"] = year
            df.at[idx, "RegisteredDate"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        else:
            # Add new record
            new_row = {
                "ID": student_id,
                "Name": name,
                "Course": course,
                "Year": year,
                "RegisteredDate": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        
        # Save to CSV
        df.to_csv(csv_path, index=False)
    
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
    
    def show_status(self, message, color="green"):
        """Show status message with specified color"""
        self.status_label.configure(text=message, text_color=color)
        
        # Reset message after 5 seconds if it's a success message
        if color == "green":
            self.after(5000, lambda: self.status_label.configure(text=""))
    
    def resize_image_to_fit(self, pil_img, width, height):
        """Resize an image to fit within specified dimensions while preserving aspect ratio"""
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
        
        # Resize the image
        return pil_img.resize((new_w, new_h), Image.LANCZOS)
    
    def cleanup(self):
        """Clean up resources before destroying the widget"""
        # Stop the camera if it's running
        if self.is_capturing:
            self.stop_camera()