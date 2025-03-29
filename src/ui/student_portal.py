"""
Student Portal for self-registration and face upload
"""
import os
import cv2
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import numpy as np
from PIL import Image, ImageTk
import datetime
import time
import threading
import logging
import pandas as pd
import customtkinter as ctk

from src.face_recognition.detector import FaceDetector
from src.database.sqlite_handler import SQLiteHandler
from src.utils.camera_manager import CameraManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

class StudentPortal(ctk.CTkFrame):
    """
    A portal for students to register themselves and upload face images
    """
    
    def __init__(self, master, app_instance=None):
        """
        Initialize the student portal
        
        Args:
            master: Parent widget
            app_instance: Main application instance for callbacks
        """
        super().__init__(master)
        
        self.master = master
        self.app_instance = app_instance
        
        # Initialize components
        self.db = SQLiteHandler()
        self.face_detector = FaceDetector()
        self.camera_manager = CameraManager()
        
        # Camera and capture variables
        self.cam = None
        self.is_capturing = False
        self.capture_thread = None
        
        # Setup UI components
        self.setup_ui()

    def setup_ui(self):
        """Set up the student portal UI"""
        # Use CTkFrame for better appearance
        self.configure(corner_radius=10)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        # Title
        title_label = ctk.CTkLabel(
            self, 
            text="Student Self-Registration Portal",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=(20, 10), sticky="ew")
        
        # Left side - Registration form
        self.form_frame = ctk.CTkFrame(self, corner_radius=8)
        self.form_frame.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")
        
        # Registration form
        ctk.CTkLabel(
            self.form_frame, 
            text="Student Registration",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=(15, 10))
        
        # Student ID
        id_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        id_frame.pack(fill="x", padx=20, pady=(10, 5))
        
        ctk.CTkLabel(id_frame, text="Student ID:", width=100).pack(side="left")
        self.student_id_entry = ctk.CTkEntry(id_frame, width=200)
        self.student_id_entry.pack(side="left", padx=10, fill="x", expand=True)
        
        # Student Name
        name_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        name_frame.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkLabel(name_frame, text="Full Name:", width=100).pack(side="left")
        self.student_name_entry = ctk.CTkEntry(name_frame, width=200)
        self.student_name_entry.pack(side="left", padx=10, fill="x", expand=True)
        
        # Department/Course
        dept_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        dept_frame.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkLabel(dept_frame, text="Department:", width=100).pack(side="left")
        self.department_entry = ctk.CTkEntry(dept_frame, width=200)
        self.department_entry.pack(side="left", padx=10, fill="x", expand=True)
        
        # Email
        email_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        email_frame.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkLabel(email_frame, text="Email:", width=100).pack(side="left")
        self.email_entry = ctk.CTkEntry(email_frame, width=200)
        self.email_entry.pack(side="left", padx=10, fill="x", expand=True)
        
        # Phone
        phone_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        phone_frame.pack(fill="x", padx=20, pady=(5, 15))
        
        ctk.CTkLabel(phone_frame, text="Phone:", width=100).pack(side="left")
        self.phone_entry = ctk.CTkEntry(phone_frame, width=200)
        self.phone_entry.pack(side="left", padx=10, fill="x", expand=True)
        
        # Divider
        separator = ttk.Separator(self.form_frame, orient='horizontal')
        separator.pack(fill='x', padx=20, pady=10)
        
        # Instructions
        ctk.CTkLabel(
            self.form_frame,
            text="After registering, you need to capture your face images.\n"
                 "Please ensure good lighting and a clear background.",
            font=ctk.CTkFont(size=12),
            justify="left"
        ).pack(padx=20, pady=10, fill="x")

        # Register button
        self.register_btn = ctk.CTkButton(
            self.form_frame,
            text="Register & Capture Face Images",
            command=self.register_and_capture,
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            fg_color="#4CAF50",
            hover_color="#388E3C"
        )
        self.register_btn.pack(padx=20, pady=(10, 20), fill="x")
        
        # Right side - Camera feed
        self.camera_frame = ctk.CTkFrame(self, corner_radius=8)
        self.camera_frame.grid(row=1, column=1, padx=20, pady=20, sticky="nsew")
        
        # Camera label
        ctk.CTkLabel(
            self.camera_frame,
            text="Camera Preview",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=(15, 10))
        
        # Camera view
        self.camera_view = ctk.CTkLabel(
            self.camera_frame,
            text="Camera will appear here",
            width=400,
            height=300
        )
        self.camera_view.pack(padx=20, pady=10)
        
        # Camera controls
        control_frame = ctk.CTkFrame(self.camera_frame, fg_color="transparent")
        control_frame.pack(fill="x", padx=20, pady=10)
        
        # Status message
        self.status_var = tk.StringVar(value="Ready")
        self.status_label = ctk.CTkLabel(
            self.camera_frame,
            textvariable=self.status_var,
            font=ctk.CTkFont(size=12),
            text_color="#666666"
        )
        self.status_label.pack(pady=(5, 15))
        
    def register_and_capture(self):
        """Register student and capture face images"""
        # Get form values
        student_id = self.student_id_entry.get().strip()
        name = self.student_name_entry.get().strip()
        department = self.department_entry.get().strip()
        email = self.email_entry.get().strip()
        phone = self.phone_entry.get().strip()
        
        # Validate form
        if not student_id or not name:
            messagebox.showerror("Error", "Student ID and Name are required fields")
            return
        
        # Check if student ID already exists
        if self.db.student_exists(student_id):
            existing_data = self.db.get_student_by_id(student_id)
            
            if existing_data and existing_data.get('Name') != name:
                result = messagebox.askyesno(
                    "Student ID Already Registered", 
                    f"Student ID {student_id} is already registered with the name: {existing_data.get('Name')}.\n\n"
                    f"Do you want to update your information and capture new face images?"
                )
                if not result:
                    return
            else:
                result = messagebox.askyesno(
                    "Student Already Registered", 
                    f"You are already registered as {name}.\n\n"
                    f"Do you want to capture additional face images?"
                )
                if not result:
                    return
        
        # Add student to database with extended info
        success = self.db.add_student_extended(
            student_id, name, department=department, email=email, phone=phone
        )
        
        if success:
            # Ask for the number of images to capture
            sample_num = simpledialog.askinteger(
                "Face Images", 
                "Number of face images to capture (15-30 recommended):", 
                minvalue=5, 
                maxvalue=50, 
                initialvalue=20
            )
            
            if not sample_num:
                return
            
            # Create directory if it doesn't exist
            if not os.path.isdir("TrainingImage"):
                os.makedirs("TrainingImage")
            
            # Start camera capture
            self.start_camera_capture(student_id, name, sample_num)
        else:
            messagebox.showerror("Error", f"Failed to register student {name}")
            
    def start_camera_capture(self, student_id, name, sample_num):
        """Start camera capture for face images"""
        if self.is_capturing:
            self.stop_camera_capture()
        
        try:
            # Get camera
            camera_result = self.camera_manager.get_best_camera()
            
            if camera_result.success:
                self.cam = camera_result.camera
                
                # Set camera properties for better quality
                self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.cam.set(cv2.CAP_PROP_FPS, 30)
                
                # Update status
                self.is_capturing = True
                self.update_status("Camera activated. Preparing to capture...")
                
                # Start the capture thread
                self.capture_thread = threading.Thread(
                    target=self._capture_face_images,
                    args=(student_id, name, sample_num),
                    daemon=True
                )
                self.capture_thread.start()
                
                return True
            else:
                messagebox.showerror("Camera Error", "Could not initialize camera")
                return False
        except Exception as e:
            messagebox.showerror("Camera Error", f"Failed to start camera: {e}")
            logger.error(f"Camera error: {e}")
            return False
    
    def _capture_face_images(self, student_id, name, sample_num):
        """Capture multiple face images in a thread"""
        count = 0
        delay_between_captures = 0.5  # seconds
        last_capture_time = time.time() - delay_between_captures  # Allow immediate first capture
        
        # Show instructions
        messagebox.showinfo(
            "Capture Instructions", 
            "Please look at the camera and follow these guidelines:\n\n"
            "1. Look directly at the camera\n"
            "2. Move your head slightly between captures\n"
            "3. Try different facial expressions\n"
            "4. Ensure good lighting on your face\n\n"
            "Click OK to begin capturing images."
        )
        
        # Update status
        self.update_status("Starting image capture...")
        
        while self.is_capturing and count < sample_num:
            try:
                ret, img = self.cam.read()
                if not ret:
                    self.update_status("Camera error. Stopping capture.")
                    break
                
                # Create a copy for display
                display_img = img.copy()
                
                # Convert to grayscale for face detection
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                faces = self.face_detector.detect_faces(gray)
                
                # Draw rectangles around all faces
                for (x, y, w, h) in faces:
                    cv2.rectangle(display_img, (x, y), (x+w, y+h), (0, 255, 0), 2)
                
                # Add information to the display image
                cv2.putText(
                    display_img, 
                    f"Images: {count}/{sample_num}", 
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 
                    0.8, 
                    (0, 0, 255), 
                    2
                )
                
                cv2.putText(
                    display_img, 
                    "Move slightly between captures", 
                    (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 
                    0.6, 
                    (0, 0, 255), 
                    2
                )
                
                # Display the video frame
                self.show_frame(display_img)
                
                # Check if enough time has passed since last capture
                current_time = time.time()
                if current_time - last_capture_time >= delay_between_captures:
                    # Only save image if a face is detected
                    if len(faces) > 0:
                        # Sort faces by area (largest first)
                        faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
                        
                        # Get the largest face
                        x, y, w, h = faces[0]
                        
                        # Save the face image with standardized filename
                        file_name = f"{name}.{student_id}.{count}.jpg"
                        file_path = os.path.join("TrainingImage", file_name)
                        
                        # Save the face region
                        face_img = gray[y:y+h, x:x+w]
                        
                        # Standardize size for better training
                        face_img = cv2.resize(face_img, (200, 200))
                        
                        # Save the image
                        cv2.imwrite(file_path, face_img)
                        
                        count += 1
                        last_capture_time = current_time
                        
                        # Update status
                        self.update_status(f"Images Captured: {count}/{sample_num}")
                
            except Exception as e:
                logger.error(f"Error capturing image: {e}")
                self.update_status(f"Error: {e}")
                time.sleep(0.1)
        
        # Stop capture when done
        self.stop_camera_capture()
        
        # Show completion message
        if count >= sample_num:
            messagebox.showinfo(
                "Registration Complete",
                f"Registration successful! {count} face images captured.\n\n"
                f"Student ID: {student_id}\n"
                f"Name: {name}\n\n"
                "The system will now be trained with your face images."
            )
            
            # Train the model with the new images
            self.train_model()
        else:
            messagebox.showwarning(
                "Capture Incomplete",
                f"Only {count}/{sample_num} images were captured.\n"
                "You may need to register again with better lighting."
            )
    
    def train_model(self):
        """Train the face recognition model with the new images"""
        self.update_status("Training model with face images...")
        
        try:
            # Create model directory if it doesn't exist
            os.makedirs("TrainingImageLabel", exist_ok=True)
            
            # Train the recognizer
            success = self.face_detector.train_recognizer("TrainingImage")
            
            if success:
                # Save the model
                model_path = os.path.join("TrainingImageLabel", "trainner.yml")
                save_success = self.face_detector.save_model(model_path)
                
                if save_success:
                    self.update_status("Training completed successfully!")
                    messagebox.showinfo(
                        "Training Complete",
                        "Face recognition model has been trained successfully.\n\n"
                        "You can now use the attendance system with face recognition."
                    )
                else:
                    self.update_status("Failed to save the trained model")
                    messagebox.showwarning(
                        "Training Warning",
                        "Training was completed, but there was an error saving the model."
                    )
            else:
                self.update_status("Training failed")
                messagebox.showerror(
                    "Training Error",
                    "Failed to train the face recognition model.\n"
                    "Please try registering again with clearer face images."
                )
        
        except Exception as e:
            self.update_status(f"Training error: {e}")
            messagebox.showerror("Training Error", f"An error occurred during training: {e}")
    
    def show_frame(self, frame):
        """Display a frame in the camera view"""
        try:
            if frame is None:
                return
            
            # Convert from BGR (OpenCV format) to RGB (PIL format)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Convert to PIL format and resize
            pil_image = Image.fromarray(rgb_frame)
            pil_image = pil_image.resize((400, 300), Image.LANCZOS)
            
            # Convert to CTkImage
            ctk_image = ctk.CTkImage(
                light_image=pil_image,
                dark_image=pil_image,
                size=(400, 300)
            )
            
            # Update the camera view
            self.camera_view.configure(image=ctk_image)
            self.camera_view.image = ctk_image  # Keep a reference
            
        except Exception as e:
            logger.error(f"Error showing frame: {e}")
    
    def stop_camera_capture(self):
        """Stop camera capture and release resources"""
        try:
            if self.is_capturing:
                self.is_capturing = False
                
                # Release camera
                if hasattr(self, 'cam') and self.cam is not None:
                    self.cam.release()
                    self.cam = None
                
                # Clear camera view
                self.camera_view.configure(image=None, text="Camera Off")
                
                self.update_status("Camera stopped")
                return True
            
            return False
        
        except Exception as e:
            logger.error(f"Error stopping camera: {e}")
            return False
    
    def update_status(self, message):
        """Update the status label"""
        try:
            if hasattr(self, 'status_var'):
                self.status_var.set(message)
                # Force update
                self.update_idletasks()
        except Exception as e:
            logger.error(f"Error updating status: {e}")
    
    def on_close(self):
        """Handle closing"""
        if self.is_capturing:
            self.stop_camera_capture()

# Standalone testing
if __name__ == "__main__":
    root = ctk.CTk()
    root.title("Student Self-Registration Portal")
    root.geometry("1000x600")
    
    # Set the appearance mode
    ctk.set_appearance_mode("system")
    ctk.set_default_color_theme("blue")
    
    app = StudentPortal(root)
    app.pack(fill="both", expand=True, padx=20, pady=20)
    
    # Handle closing
    root.protocol("WM_DELETE_WINDOW", lambda: (app.on_close(), root.destroy()))
    
    root.mainloop()