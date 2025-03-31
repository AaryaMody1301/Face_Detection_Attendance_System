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
        self.current_student_id = None
        self.current_student_name = None
        self.current_student_course = None
        self.current_frame = None
        
        # Track after IDs for cleanup
        self.after_ids = []
        
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
            
            # Initialize face detection
            self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            
            # Update UI
            self.is_capturing = True
            self.start_button.configure(text="Stop Camera")
            self.capture_button.configure(state="normal")
            
            # Start camera loop in a thread to avoid freezing UI
            logger.info("Camera started for student registration")
            
            # Start the camera loop in a separate thread
            self.camera_thread = threading.Thread(target=self._camera_loop)
            self.camera_thread.daemon = True
            self.camera_thread.start()
            
        except Exception as e:
            self.show_status(f"Failed to start camera: {str(e)}", "red")
            logger.error(f"Error starting camera: {e}")
    
    def stop_camera(self):
        """Stop the camera feed"""
        if not self.is_capturing:
            return
            
        try:
            # Update status
            self.is_capturing = False
            
            # Release camera
            if self.camera_feed and self.camera_feed.isOpened():
                self.camera_feed.release()
                self.camera_feed = None
            
            # Update UI
            self.start_button.configure(text="Start Camera")
            self.capture_button.configure(state="disabled")
            self.camera_label.configure(image=None, text="Camera stopped")
            
            logger.info("Camera stopped for student registration")
            
        except Exception as e:
            logger.error(f"Error stopping camera: {e}")
    
    def _camera_loop(self):
        """Process camera frames for the registration view"""
        try:
            while self.is_capturing and self.camera_feed and self.camera_feed.isOpened():
                try:
                    ret, frame = self.camera_feed.read()
                    if not ret:
                        continue
                        
                    # Store current frame for capture operations
                    self.current_frame = frame.copy()
                    
                    # Flip the frame horizontally for a more intuitive view
                    frame = cv2.flip(frame, 1)
                    
                    # Apply face detection
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                    faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(30, 30))
                    
                    # Create a copy for drawing
                    display_frame = frame.copy()
                    
                    # Draw face guidelines if no faces detected
                    if len(faces) == 0:
                        # Draw a central rectangle as a guide
                        h, w = display_frame.shape[:2]
                        center_x, center_y = w // 2, h // 2
                        rect_w, rect_h = 200, 250
                        cv2.rectangle(
                            display_frame,
                            (center_x - rect_w//2, center_y - rect_h//2),
                            (center_x + rect_w//2, center_y + rect_h//2),
                            (0, 165, 255),  # Orange color
                            2
                        )
                        # Add guidance text
                        cv2.putText(
                            display_frame,
                            "Position face here",
                            (center_x - 90, center_y - rect_h//2 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.7,
                            (0, 165, 255),
                            2
                        )
                    
                    # Draw rectangles around detected faces
                    for (x, y, w, h) in faces:
                        # Draw rectangle around the face
                        cv2.rectangle(display_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                        
                        # If multiple faces detected, show warning
                        if len(faces) > 1:
                            cv2.putText(
                                display_frame,
                                "Multiple faces detected",
                                (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.7,
                                (0, 0, 255),
                                2
                            )
                    
                    # Add capture instruction text at the bottom
                    cv2.putText(
                        display_frame,
                        f"Captured: {self.capture_count}/{self.max_captures} - Press 'Capture' to continue",
                        (10, display_frame.shape[0] - 20),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (255, 255, 255),
                        2
                    )
                    
                    # Convert the OpenCV BGR frame to RGB
                    rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
                    
                    # Convert to PIL Image and resize to fit the label
                    img = Image.fromarray(rgb_frame)
                    img = self._resize_image_to_fit(img, self.camera_label.winfo_width(), self.camera_label.winfo_height())
                    
                    # Convert to CTkImage
                    ctk_img = ctk.CTkImage(
                        light_image=img, 
                        dark_image=img, 
                        size=(img.width, img.height)
                    )
                    
                    # Update the camera label with the new image
                    self.photo = ctk_img  # Keep reference to prevent garbage collection
                    
                    # Update label in main thread
                    self.after(0, lambda: self.camera_label.configure(image=self.photo, text=""))
                    
                    # Sleep to reduce CPU usage - use a short sleep to keep UI responsive
                    time.sleep(0.02)
                    
                except KeyboardInterrupt:
                    logger.info("Camera loop interrupted by keyboard")
                    break
                except Exception as e:
                    logger.error(f"Error processing camera frame: {e}")
                    # Continue the loop instead of breaking
                    continue
                
        except Exception as e:
            logger.error(f"Error in camera loop: {e}")
            # Notify the main thread about the error
            if self.winfo_exists():
                self.after(0, lambda: self.show_status(f"Camera error: {e}", "red"))
            
        finally:
            # Make sure we clean up no matter how we exit the loop
            if self.camera_feed:
                self.camera_feed.release()
            self.camera_feed = None
            self.is_capturing = False
            logger.info("Camera stopped for student registration")
            
            # Update the UI to show the camera has stopped
            if self.winfo_exists():
                if hasattr(self, 'camera_label') and self.camera_label.winfo_exists():
                    self.after(0, lambda: self.camera_label.configure(
                        text="Camera stopped. Click 'Start Camera' to restart.",
                        image=None
                    ))
                if hasattr(self, 'start_button') and self.start_button.winfo_exists():
                    self.after(0, lambda: self.start_button.configure(text="Start Camera"))
                if hasattr(self, 'capture_button') and self.capture_button.winfo_exists():
                    self.after(0, lambda: self.capture_button.configure(state="disabled"))
    
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
        """Register a new student with face data"""
        # Check if required fields are filled
        student_id = self.id_entry.get().strip()
        name = self.name_entry.get().strip()
        course = self.course_entry.get().strip()
        year = self.year_var.get().strip()
        
        if not student_id or not name:
            self.show_status("Student ID and Name are required fields.", "red")
            return
        
        # Check if we have captured at least one face image
        if self.capture_count == 0 and self.is_capturing:
            # Ask user if they want to continue without face images
            confirm = ctk.CTkInputDialog(
                title="No Face Images", 
                text="No face images have been captured. Register student without face data?"
            ).get_input()
            
            if confirm.lower() not in ['yes', 'y']:
                self.show_status("Registration cancelled. Please capture face images first.", "orange")
                return
                
        # Save student details
        try:
            # Save to CSV files
            success = self.save_student_details(student_id, name, course, year)
            
            if success:
                # Show success message
                self.show_status(f"Student {name} (ID: {student_id}) registered successfully!", "green")
                
                # Create a success animation
                success_frame = ctk.CTkFrame(self, corner_radius=10, fg_color=("#2ecc71", "#27ae60"))
                success_frame.place(relx=0.5, rely=0.5, anchor="center")
                
                success_label = ctk.CTkLabel(
                    success_frame,
                    text="✓ Registration Complete",
                    font=ctk.CTkFont(size=20, weight="bold"),
                    text_color="white"
                )
                success_label.pack(padx=40, pady=40)
                
                # Remove after 2 seconds
                def remove_success():
                    success_frame.destroy()
                    self.reset_form()
                
                self.after(2000, remove_success)
                
                # If we have face images and camera is running, trigger training
                if self.capture_count > 0:
                    self.trigger_model_training()
            else:
                self.show_status("Error saving student details. Please try again.", "red")
        except Exception as e:
            logger.error(f"Error registering student: {e}")
            self.show_status(f"Error registering student: {e}", "red")
    
    def save_student_details(self, student_id, name, course, year):
        """
        Save student details to CSV files
        
        This saves to both the legacy StudentDetails.csv file and the 
        face_detector compatible data/students.csv file
        """
        try:
            # First, save to legacy CSV for backward compatibility
            legacy_csv_path = os.path.join("StudentDetails", "StudentDetails.csv")
            os.makedirs(os.path.dirname(legacy_csv_path), exist_ok=True)
            
            # Create columns if file doesn't exist
            if not os.path.isfile(legacy_csv_path):
                df_legacy = pd.DataFrame(columns=["ID", "Name", "Course", "Year", "RegisteredDate"])
            else:
                df_legacy = pd.read_csv(legacy_csv_path)
            
            # Check if the student ID already exists
            if student_id in df_legacy["ID"].values:
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
            
            if os.path.isfile(face_detector_csv_path):
                df_face = pd.read_csv(face_detector_csv_path)
                
                # Check if ID exists
                if student_id in df_face["ID"].values:
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