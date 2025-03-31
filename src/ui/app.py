"""
Main UI application for the Face Detection Attendance System
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
import csv
import customtkinter as ctk  # Import CustomTkinter

# Import from core modules
from src.core.face_recognition.face_detector import FaceDetector
from src.core.database.db_handler import DatabaseHandler
from src.core.utils.video_processor import VideoProcessor
from src.core.utils.config_manager import ConfigManager
from src.models.student import Student
from src.utils.image_utils import draw_rectangle
from src.utils.attendance_analytics import AttendanceAnalytics
from src.ui.analytics_dashboard import AnalyticsDashboard
from src.utils.cloud_sync import CloudSync  # Import CloudSync
from src.utils.camera_manager import CameraManager  # Import CameraManager
from src.ui.settings import SettingsPage  # Import the settings page

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

class FaceAttendanceApp:
    """
    Main application class for the Face Detection Attendance System
    """
    
    def __init__(self, root):
        """
        Initialize the application
        
        Args:
            root (tk.Tk): Root Tkinter window
        """
        self.root = root
        self.root.title("Face Recognition Attendance System")
        self.root.geometry('1280x720')
        self.root.configure(background='grey80')
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Initialize components
        try:
            print("Initializing face detector...")
            self.face_detector = FaceDetector()
            print("Initializing database...")
            self.db = DatabaseHandler()  # Use DatabaseHandler from core
            
            # Camera and capture variables
            self.cam = None
            self.is_capturing = False
            self.capture_thread = None
            # Initialize camera manager
            self.camera_manager = CameraManager()
            
            # Current subject
            self.current_subject = None
            
            # Load the trained model if it exists
            model_path = "TrainingImageLabel/trainner.yml"
            if os.path.isfile(model_path):
                print(f"Loading model from {model_path}")
                self.face_detector.load_model(model_path)
            else:
                print(f"Model file not found: {model_path}")
            
            print("Initializing cloud sync...")
            self.cloud_sync = CloudSync(
                bucket_name='your-bucket-name',
                aws_access_key='your-access-key',
                aws_secret_key='your-secret-key'
            )
            
            # Create menu bar
            self.create_menu_bar()
            
            # Initialize the UI
            self.setup_ui()
            
            # Show splash message
            self.after_idle_callback = self.root.after(500, self.show_splash_message)
        except Exception as e:
            messagebox.showerror("Initialization Error", f"Failed to initialize the application: {e}")
            raise
    
    def create_menu_bar(self):
        """Create the application menu bar"""
        menu_bar = tk.Menu(self.root)
        self.root.config(menu=menu_bar)
        
        # File menu
        file_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Import Student Details", command=self.import_student_details)
        file_menu.add_command(label="Upload Student Images", command=self.upload_student_images)
        file_menu.add_command(label="Manage Subjects", command=self.manage_subjects)
        file_menu.add_separator()
        file_menu.add_command(label="Organize Folders", command=self.organize_folders)
        file_menu.add_command(label="Enhanced Cleanup", command=self.enhanced_cleanup)
        file_menu.add_command(label="Backup to Cloud", command=self.backup_to_cloud)
        file_menu.add_command(label="Restore from Cloud", command=self.restore_from_cloud)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)
        
        # Analytics menu
        analytics_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="Analytics", menu=analytics_menu)
        analytics_menu.add_command(label="View Dashboard", command=self.open_analytics_dashboard)
        analytics_menu.add_command(label="Generate Reports", command=self.generate_reports)
        
        # Settings menu
        settings_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="Application Settings", command=self.open_settings)
        settings_menu.add_command(label="Camera Settings", command=self.camera_settings)
        
        # Help menu
        help_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
        help_menu.add_command(label="Instructions", command=self.show_instructions)
    
    def organize_folders(self):
        """Organize the TrainingImage and Attendance folders"""
        try:
            from src.utils.organize_folders import organize_training_images, organize_attendance_records
            # Show info message
            messagebox.showinfo("Organizing Folders", 
                              "The system will now organize your training images and attendance records.\n"
                              "This may take a moment. Please wait...")
            
            # Run the organization in a separate thread to keep UI responsive
            def organize_thread():
                try:
                    # Update status
                    self.update_status("Organizing folders...")
                    
                    # Organize training images
                    train_success = organize_training_images()
                    
                    # Organize attendance records
                    attend_success = organize_attendance_records()
                    
                    # Show completion message
                    if train_success or attend_success:
                        messagebox.showinfo("Organization Complete", 
                                          "Folders have been successfully organized.")
                        self.update_status("Folder organization completed")
                    else:
                        messagebox.showwarning("Organization Notice", 
                                            "No files were found to organize.")
                        self.update_status("No files to organize")
                        
                except Exception as e:
                    messagebox.showerror("Organization Error", f"Error organizing folders: {e}")
                    self.update_status(f"Organization error: {e}")
            
            # Start the organization thread
            thread = threading.Thread(target=organize_thread)
            thread.daemon = True
            thread.start()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to organize folders: {e}")
    
    def show_about(self):
        """Show the about dialog"""
        about_text = """Face Recognition Attendance System
Version 1.0

A facial recognition based attendance tracking system
that automates the process of marking attendance.

© Parul University
"""
        messagebox.showinfo("About", about_text)
    
    def show_instructions(self):
        """Show usage instructions"""
        instructions = """Using the Face Recognition Attendance System:

1. Register Students:
   - Enter student ID and name
   - Click 'Take Images' to capture training images
   - Take at least 20 images for best results

2. Train the System:
   - After registering students, click 'Train Images'
   - Wait for training to complete

3. Track Attendance:
   - Enter the subject name
   - Click 'Track Images' to start recognition
   - Students are automatically marked present

4. View Records:
   - Click 'View Attendance' to see attendance records
   - Export records to CSV if needed

5. Organize Files:
   - Use File > Organize Folders to keep data neat
"""
        messagebox.showinfo("Instructions", instructions)
    
    def show_splash_message(self):
        """Show welcome message and usage instructions"""
        messagebox.showinfo(
            "Welcome", 
            "Welcome to Face Recognition Attendance System!\n\n"
            "To use this application:\n"
            "1. Register students with 'Take Images'\n"
            "2. Train the model with 'Train Images'\n"
            "3. Enter subject name and mark attendance with 'Track Images'\n\n"
            "For help, contact system administrator."
        )
    
    def setup_ui(self):
        """Set up the user interface"""
        # Title
        title_label = tk.Label(self.root, text="Face Recognition Attendance System", 
                              bg="grey80", fg="black", font=('times', 30, ' bold '))
        title_label.pack(pady=20)
        
        # Add a tabbed interface for better navigation
        self.tab_view = ctk.CTkTabview(self.root)
        self.tab_view.pack(fill="both", expand=True, padx=20, pady=20)

        # Add tabs for different sections
        self.attendance_tab = self.tab_view.add("Attendance")
        self.settings_tab = self.tab_view.add("Settings")
        self.analytics_tab = self.tab_view.add("Analytics")

        # Set up the attendance tab
        self.setup_attendance_tab(self.attendance_tab)

        # Set up the settings tab
        self.settings_page = SettingsPage(self.settings_tab)
        self.settings_page.pack(fill="both", expand=True)

        # Set up the analytics tab
        self.analytics_dashboard = AnalyticsDashboard(self.analytics_tab)
        self.analytics_dashboard.pack(fill="both", expand=True)

    def setup_attendance_tab(self, parent):
        """Set up the attendance tab"""
        # Move existing attendance-related UI setup here
        # Main frame
        self.main_frame = tk.Frame(parent, bg="grey80")
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Left frame (for video and controls)
        left_frame = tk.Frame(self.main_frame, bg="grey80")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Video frame with fixed dimensions for better stability
        video_container = tk.Frame(left_frame, bg="black", width=640, height=480)
        video_container.pack(padx=10, pady=10)
        video_container.pack_propagate(False)  # Prevent container from resizing to fit contents
        
        self.video_frame = tk.Label(video_container, bg="black")
        self.video_frame.pack(fill=tk.BOTH, expand=True)
        
        # Control buttons frame
        control_frame = tk.Frame(left_frame, bg="grey80")
        control_frame.pack(padx=10, pady=10, fill=tk.X)
        
        # Buttons with improved styling
        button_style = {
            'font': ('times', 12, ' bold '),
            'width': 12,
            'height': 2,
            'border': 0,
            'cursor': 'hand2'
        }
        
        self.take_img_btn = tk.Button(control_frame, text="Take Images", 
                                     command=self.take_images, bg="#4CAF50", fg="white",
                                     **button_style)
        self.take_img_btn.grid(row=0, column=0, padx=10, pady=10)
        
        self.train_img_btn = tk.Button(control_frame, text="Train Images", 
                                     command=self.train_images, bg="#2196F3", fg="white",
                                     **button_style)
        self.train_img_btn.grid(row=0, column=1, padx=10, pady=10)
        
        self.track_img_btn = tk.Button(control_frame, text="Track Images", 
                                     command=self.track_images, bg="#FF9800", fg="white",
                                     **button_style)
        self.track_img_btn.grid(row=0, column=2, padx=10, pady=10)
        
        self.group_attendance_btn = tk.Button(control_frame, text="Group Attendance", 
                                     command=self.group_attendance, bg="#673AB7", fg="white",
                                     **button_style)
        self.group_attendance_btn.grid(row=0, column=3, padx=10, pady=10)
        
        # Right frame (for student details)
        right_frame = tk.Frame(self.main_frame, bg="grey80", width=350)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)
        right_frame.pack_propagate(False)  # Prevent frame from shrinking
        
        # Student registration frame with styling
        student_frame = tk.LabelFrame(right_frame, text="Student Registration", 
                                     bg="grey80", font=('times', 14, ' bold '),
                                     padx=10, pady=10)
        student_frame.pack(padx=10, pady=10, fill=tk.X)
        
        # Student ID
        tk.Label(student_frame, text="Enrollment ID:", bg="grey80", 
                font=('times', 12, 'bold')).grid(row=0, column=0, padx=5, pady=10, sticky=tk.W)
        self.student_id_entry = tk.Entry(student_frame, width=20, font=('times', 12))
        self.student_id_entry.grid(row=0, column=1, padx=5, pady=10)
        
        # Student Name
        tk.Label(student_frame, text="Student Name:", bg="grey80", 
                font=('times', 12, 'bold')).grid(row=1, column=0, padx=5, pady=10, sticky=tk.W)
        self.student_name_entry = tk.Entry(student_frame, width=20, font=('times', 12))
        self.student_name_entry.grid(row=1, column=1, padx=5, pady=10)
        
        # Attendance frame with styling
        attendance_frame = tk.LabelFrame(right_frame, text="Attendance", 
                                       bg="grey80", font=('times', 14, ' bold '),
                                       padx=10, pady=10)
        attendance_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # Subject
        tk.Label(attendance_frame, text="Subject:", bg="grey80", 
                font=('times', 12, 'bold')).grid(row=0, column=0, padx=5, pady=10, sticky=tk.W)
        self.subject_entry = tk.Entry(attendance_frame, width=20, font=('times', 12))
        self.subject_entry.grid(row=0, column=1, padx=5, pady=10)
        
        # Quick subjects frame
        subjects_frame = tk.Frame(attendance_frame, bg="grey80")
        subjects_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=5)
        
        # Add some predefined subjects for quick selection
        quick_subjects = ["Python", "Java", "Web Dev", "Data Science"]
        for i, subject in enumerate(quick_subjects):
            btn = tk.Button(subjects_frame, text=subject, 
                           command=lambda s=subject: self.set_subject(s),
                           bg="#673AB7", fg="white", font=('times', 10))
            btn.grid(row=0, column=i, padx=5, pady=5)
        
        # Mark attendance button
        self.mark_attendance_btn = tk.Button(attendance_frame, text="Mark Attendance", 
                                           command=self.mark_attendance, bg="#673AB7", fg="white",
                                           font=('times', 12, ' bold '), width=15, height=2)
        self.mark_attendance_btn.grid(row=2, column=0, columnspan=2, padx=5, pady=15)
        
        # View attendance button
        self.view_attendance_btn = tk.Button(attendance_frame, text="View Attendance", 
                                           command=self.view_attendance, bg="#009688", fg="white",
                                           font=('times', 12, ' bold '), width=15, height=2)
        self.view_attendance_btn.grid(row=3, column=0, columnspan=2, padx=5, pady=15)
        
        # Status frame with better styling
        status_frame = tk.Frame(self.root, bg="#f0f0f0", height=30)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.status_label = tk.Label(status_frame, text="Status: Ready", bg="#f0f0f0", 
                                   font=('times', 10), anchor=tk.W, padx=10, pady=5)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Right side status - show current camera state and student count
        self.camera_status = tk.Label(status_frame, text="Camera: Inactive", bg="#f0f0f0",
                                    font=('times', 10), anchor=tk.E, padx=10, pady=5)
        self.camera_status.pack(side=tk.RIGHT)
        
        # Footer with styling
        footer_frame = tk.Frame(self.root, bg="#f0f0f0", height=25)
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        footer_text = "© Face Detection Attendance System - Parul University"
        footer_label = tk.Label(footer_frame, text=footer_text, bg="#f0f0f0", 
                              font=('times', 10))
        footer_label.pack(pady=5)
        
        # Initial message in video frame
        init_text = "Camera feed will appear here\nClick 'Take Images' to start"
        init_label = tk.Label(self.video_frame, text=init_text, bg="black", fg="white",
                            font=('times', 14))
        init_label.pack(expand=True)

    def setup_analytics_tab(self, parent):
        """Set up the analytics tab"""
        # Integrate the analytics dashboard
        self.analytics_dashboard = AnalyticsDashboard(parent)
        self.analytics_dashboard.pack(fill="both", expand=True)

    def set_subject(self, subject):
        """Set the subject entry field with the provided subject"""
        self.subject_entry.delete(0, tk.END)
        self.subject_entry.insert(0, subject)
        self.update_status(f"Subject set to: {subject}")
    
    def update_status(self, message, error=False):
        """
        Update the status label
        
        Args:
            message (str): Status message
            error (bool): Whether this is an error message
        """
        try:
            if hasattr(self, 'status_label') and self.status_label.winfo_exists():
                if error:
                    self.status_label.config(text=f"Error: {message}", fg="red")
                else:
                    self.status_label.config(text=f"Status: {message}", fg="black")
                # Force update to show status immediately
                self.root.update_idletasks()
        except Exception as e:
            print(f"Error updating status: {e}")
    
    def take_images(self):
        """Capture multiple images of a student for training"""
        # Get enrollment ID and name
        enrollment = self.student_id_entry.get()
        name = self.student_name_entry.get()
        
        if not enrollment or not name:
            messagebox.showerror("Error", "Please enter enrollment ID and name")
            return
            
        # Try to add student to the database
        success = self.db.add_student(enrollment, name)
        if not success:
            messagebox.showerror("Error", "Failed to add student to database")
            return
            
        # Ask for the number of images to capture
        sample_num = simpledialog.askinteger("Input", "Number of images to capture", 
                                           minvalue=10, maxvalue=100, initialvalue=20)
        if not sample_num:
            return
            
        # Create directory if it doesn't exist
        if not os.path.isdir("TrainingImage"):
            os.makedirs("TrainingImage")
            
        # Start video capture
        if not self.start_capture():
            return
            
        # Initialize counter
        count = 0
        
        self.update_status("Capturing images. Please move your face slightly between captures.")
        messagebox.showinfo("Instructions", 
                         "We'll capture multiple images for training.\n\n"
                         "1. Look directly at the camera\n"
                         "2. Move your head slightly between captures\n"
                         "3. Try different expressions\n"
                         "4. Stand still during each capture\n\n"
                         "Press OK to begin.")
        
        # Start capturing images in a separate thread
        def capture_thread():
            nonlocal count
            
            delay_between_captures = 0.5  # seconds
            last_capture_time = time.time() - delay_between_captures  # allow immediate first capture
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
                    
                    # Show counter and instructions on the image
                    cv2.putText(display_img, f"Images: {count}/{sample_num}", (10, 30),
                             cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                    cv2.putText(display_img, "Move slightly between captures", (10, 60),
                             cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                    
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
                            file_name = f"{name}.{enrollment}.{count}.jpg"
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
                    print(f"Error capturing image: {e}")
                    time.sleep(0.1)
            
            # Stop capture when done
            self.stop_capture()
            
            # Show completion message
            if count >= sample_num:
                self.update_status(f"Captured {count} images successfully")
                messagebox.showinfo("Success", f"{count} images captured successfully")
            else:
                self.update_status(f"Capture stopped. Only {count}/{sample_num} images captured")
                messagebox.showwarning("Warning", f"Capture stopped. Only {count}/{sample_num} images captured")
        
        # Start the capture thread
        self.capture_thread = threading.Thread(target=capture_thread)
        self.capture_thread.daemon = True
        self.capture_thread.start()
    
    def train_images(self):
        """Train the face recognition model with captured images"""
        # Check if training directory exists and has images
        if not os.path.isdir("TrainingImage"):
            messagebox.showerror("Error", "Training directory does not exist")
            return
            
        image_files = [f for f in os.listdir("TrainingImage") 
                     if os.path.isfile(os.path.join("TrainingImage", f)) and
                     f.lower().endswith(('.png', '.jpg', '.jpeg'))]
                     
        if not image_files:
            messagebox.showerror("Error", "No training images found")
            return
            
        # Start training in a background thread to keep UI responsive
        self.update_status("Starting model training. This may take a moment...")
        
        # Create a progress dialog
        progress_window = tk.Toplevel(self.root)
        progress_window.title("Training Progress")
        progress_window.geometry("400x150")
        progress_window.resizable(False, False)
        progress_window.transient(self.root)  # Set as transient to main window
        
        # Center the progress window
        progress_window.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - progress_window.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - progress_window.winfo_height()) // 2
        progress_window.geometry(f"+{x}+{y}")
        
        # Add a label
        info_label = tk.Label(progress_window, text=f"Training model with {len(image_files)} images...", padx=20, pady=10)
        info_label.pack()
        
        # Add a progress bar
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(progress_window, variable=progress_var, maximum=100)
        progress_bar.pack(fill=tk.X, padx=20, pady=10)
        
        # Status label
        status_label = tk.Label(progress_window, text="Initializing training...", padx=20)
        status_label.pack()
        
        # Define the training thread
        def train_thread():
            try:
                # Update progress dialog
                progress_var.set(10)
                progress_window.update_idletasks()
                status_label.config(text="Processing training images...")
                
                # Update status
                self.update_status("Processing training images...")
                
                # Train the model
                success = self.face_detector.train_recognizer("TrainingImage")
                
                # Update progress
                progress_var.set(70)
                progress_window.update_idletasks()
                status_label.config(text="Saving model...")
                
                if not success:
                    # Close progress dialog
                    progress_window.destroy()
                    messagebox.showerror("Training Error", "Failed to train the model")
                    self.update_status("Training failed")
                    return
                
                # Create model directory if it doesn't exist
                os.makedirs("TrainingImageLabel", exist_ok=True)
                
                # Save the model
                model_path = os.path.join("TrainingImageLabel", "trainner.yml")
                save_success = self.face_detector.save_model(model_path)
                
                # Update progress
                progress_var.set(100)
                progress_window.update_idletasks()
                status_label.config(text="Training completed successfully!")
                
                # Wait a moment so user can see 100% complete
                time.sleep(1)
                
                # Close progress dialog
                progress_window.destroy()
                
                if save_success:
                    messagebox.showinfo("Success", "Training completed successfully!")
                    self.update_status("Training completed successfully")
                else:
                    messagebox.showerror("Error", "Failed to save the trained model")
                    self.update_status("Failed to save the trained model")
                
            except Exception as e:
                # Close progress dialog
                progress_window.destroy()
                messagebox.showerror("Error", f"An error occurred during training: {e}")
                self.update_status(f"Training error: {e}")
        
        # Start the training thread
        training_thread = threading.Thread(target=train_thread)
        training_thread.daemon = True
        training_thread.start()
    
    def track_images(self):
        """Track and recognize faces in the video feed"""
        if not os.path.isfile("TrainingImageLabel/trainner.yml"):
            messagebox.showerror("Error", "Please train the model first")
            return
        
        # Get the subject
        subject = self.subject_entry.get()
        if not subject:
            messagebox.showerror("Error", "Please enter a subject name")
            return
            
        self.current_subject = subject
        
        # Create a new attendance file
        now = datetime.datetime.now()
        date = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H-%M-%S")
        attendance_file = self.db.create_attendance_record(subject, date, time_str)
        
        if not attendance_file:
            messagebox.showerror("Error", "Could not create attendance record")
            return
        
        # Load the trained model
        self.face_detector.load_model("TrainingImageLabel/trainner.yml")
        
        # Get student details
        students_df = self.db.get_student_details()
        
        if students_df.empty:
            messagebox.showwarning("Warning", "No students in database. Please register students first.")
            return
        
        # Start video capture
        if not self.start_capture():
            return
        
        # Dictionary to keep track of recognized students
        recognized_students = {}
        
        # Face recognition stabilizer to reduce false positives
        recognition_buffer = {}  # Format: {face_id: [sequence of confidences]}
        buffer_size = 5          # Number of consecutive frames needed for stable recognition
        min_recognized_frames = 3 # Minimum number of frames needed to consider recognition valid
        
        # Set confidence threshold (lower is stricter)
        confidence_threshold = 60
        
        self.update_status("Tracking started. Auto-marking attendance when faces are recognized.")
        
        # Start a separate thread for tracking
        def tracking_thread():
            nonlocal recognized_students
            start_time = time.time()
            while self.is_capturing:
                try:
                    ret, img = self.cam.read()
                    if not ret:
                        self.update_status("Camera error. Stopping tracking.")
                        break
                    display_img = img.copy()
                    face_locations, face_names = self.face_detector.recognize_faces(img)
                    for (top, right, bottom, left), name in zip(face_locations, face_names):
                        if name != "Unknown":
                            student_data = students_df[students_df['Name'] == name]
                            if not student_data.empty:
                                face_id = student_data.iloc[0]['Enrollment']
                                student_key = f"{face_id}_{name}"
                                if student_key not in recognized_students:
                                    self.db.mark_attendance(face_id, name, file_path=attendance_file)
                                    recognized_students[student_key] = True
                                    self.update_status(f"✓ Marked attendance for {name}")
                        label = f"{name}"
                        color = (0, 255, 0) if name != "Unknown" else (0, 165, 255)
                        cv2.rectangle(display_img, (left, top), (right, bottom), color, 2)
                        y_pos = top - 10 if top - 10 > 10 else bottom + 20
                        cv2.putText(display_img, label, (left, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                    attendance_count = len(recognized_students)
                    attendance_text = f"Attendance Count: {attendance_count}"
                    cv2.putText(display_img, attendance_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (50, 50, 255), 2)
                    subject_text = f"Subject: {subject}"
                    cv2.putText(display_img, subject_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50, 50, 255), 2)
                    elapsed_time = time.time() - start_time
                    time_text = f"Time: {int(elapsed_time)}s"
                    cv2.putText(display_img, time_text, (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50, 50, 255), 2)
                    self.show_frame(display_img)
                except Exception as e:
                    print(f"Error in tracking: {e}")
                    time.sleep(0.1)
            attendance_count = len(recognized_students)
            self.update_status(f"Tracking stopped. {attendance_count} students marked present.")
            if attendance_count > 0:
                summary = f"Attendance Summary\n\nSubject: {subject}\nDate: {date}\nTime: {time_str}\n\nStudents Present ({attendance_count}):\n"
                for student_key in recognized_students:
                    student_id, student_name = student_key.split("_", 1)
                    summary += f"• {student_name} (ID: {student_id})\n"
                messagebox.showinfo("Attendance Complete", summary)
            else:
                messagebox.showinfo("Attendance Complete", "No students were recognized during this session.")
        self.capture_thread = threading.Thread(target=tracking_thread)
        self.capture_thread.daemon = True
        self.capture_thread.start()
    
    def mark_attendance(self):
        """Mark attendance manually"""
        subject = self.subject_entry.get()
        if not subject:
            messagebox.showerror("Error", "Please enter a subject name")
            return
            
        enrollment = self.student_id_entry.get()
        name = self.student_name_entry.get()
        
        if not enrollment or not name:
            messagebox.showerror("Error", "Please enter enrollment ID and name")
            return
            
        now = datetime.datetime.now()
        date = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")
        
        # Create a new attendance file or use existing
        file_prefix = f"Manually Attendance{subject}"
        manual_files = [f for f in os.listdir("Attendance") 
                      if f.startswith(file_prefix) and f.endswith(".csv")]
        
        file_path = None
        if manual_files:
            # Use the most recent file
            file_path = os.path.join("Attendance", manual_files[-1])
        else:
            # Create a new file
            time_for_file = now.strftime("%Y_%m_%d_Time_%H_%M_%S")
            file_name = f"{file_prefix}_{time_for_file}.csv"
            file_path = os.path.join("Attendance", file_name)
            with open(file_path, 'w', newline='') as f:
                f.write("Enrollment,Name,Date,Time\n")
        
        # Mark attendance
        success = self.db.mark_attendance(enrollment, name, subject, date, time_str)
        
        if success:
            messagebox.showinfo("Success", "Attendance marked successfully")
            self.update_status("Attendance marked")
        else:
            messagebox.showerror("Error", "Failed to mark attendance")
            self.update_status("Failed to mark attendance")
    
    def view_attendance(self):
        """View attendance records"""
        subject = self.subject_entry.get()
        if not subject:
            messagebox.showerror("Error", "Please enter a subject name")
            return
            
        attendance_records = self.db.get_attendance_records(subject=subject)
        
        if not attendance_records:
            messagebox.showinfo("Info", "No attendance records found for this subject")
            return
            
        # Create a new window to display attendance
        attendance_window = tk.Toplevel(self.root)
        attendance_window.title(f"Attendance Records - {subject}")
        attendance_window.geometry("900x600")
        attendance_window.configure(background='grey90')
        
        # Add a header
        header_frame = tk.Frame(attendance_window, bg="grey90")
        header_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(header_frame, text=f"Attendance Records for '{subject}'", 
               font=('times', 16, 'bold'), bg="grey90").pack(side=tk.LEFT)
        
        # Add export button
        export_btn = tk.Button(header_frame, text="Export to CSV", 
                             command=lambda: self.export_attendance(attendance_records))
        export_btn.pack(side=tk.RIGHT, padx=10)
        
        # Create a frame for file list
        list_frame = tk.Frame(attendance_window, bg="grey90")
        list_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        
        # Add a label
        tk.Label(list_frame, text="Attendance Files:", 
               font=('times', 12, 'bold'), bg="grey90").pack(anchor=tk.W, pady=5)
        
        # Create a listbox for files with scrollbar
        list_scrollbar = tk.Scrollbar(list_frame)
        list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        files_listbox = tk.Listbox(list_frame, yscrollcommand=list_scrollbar.set, 
                                 width=30, font=('times', 11))
        files_listbox.pack(side=tk.LEFT, fill=tk.Y, expand=True)
        list_scrollbar.config(command=files_listbox.yview)
        
        # Create a container for the data view
        data_container = tk.Frame(attendance_window, bg="grey90")
        data_container.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Scrollbars for the data view
        h_scroll = tk.Scrollbar(data_container, orient=tk.HORIZONTAL)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        
        v_scroll = tk.Scrollbar(data_container)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Canvas for scrollable content
        canvas = tk.Canvas(data_container, bg="white", 
                         xscrollcommand=h_scroll.set, 
                         yscrollcommand=v_scroll.set)
        canvas.pack(fill=tk.BOTH, expand=True)
        
        h_scroll.config(command=canvas.xview)
        v_scroll.config(command=canvas.yview)
        
        # Frame inside canvas for content
        data_frame = tk.Frame(canvas, bg="white")
        canvas.create_window((0, 0), window=data_frame, anchor=tk.NW)
        
        # Add files to listbox
        for file in attendance_records.keys():
            files_listbox.insert(tk.END, file)
        
        # Function to display selected file's data
        def show_file_data(event):
            # Clear previous data
            for widget in data_frame.winfo_children():
                widget.destroy()
                
            # Get selected file
            selection = files_listbox.curselection()
            if not selection:
                return
                
            file = files_listbox.get(selection[0])
            df = attendance_records[file]
            
            # Display the data with styling
            title = tk.Label(data_frame, text=f"File: {file}", font=('times', 14, 'bold'),
                          bg="white", anchor=tk.W, padx=10, pady=10)
            title.grid(row=0, column=0, columnspan=len(df.columns)+1, sticky=tk.W)
            
            # Add info row
            info_text = f"Total Students: {len(df)} | Date: {df['Date'].iloc[0] if not df.empty and 'Date' in df.columns else 'N/A'}"
            info = tk.Label(data_frame, text=info_text, font=('times', 12),
                         bg="white", anchor=tk.W, padx=10, pady=5)
            info.grid(row=1, column=0, columnspan=len(df.columns)+1, sticky=tk.W)
            
            # Create headers with styling
            columns = df.columns
            for i, col in enumerate(columns):
                header = tk.Label(data_frame, text=col, font=('times', 12, 'bold'),
                               bg="#4CAF50", fg="white", pady=8, padx=10,
                               borderwidth=1, relief="solid", width=15)
                header.grid(row=2, column=i, padx=1, pady=1, sticky=tk.NSEW)
            
            # Add rows with alternating colors
            for r, row in df.iterrows():
                bg_color = "#f9f9f9" if r % 2 == 0 else "white"
                for c, col in enumerate(columns):
                    cell = tk.Label(data_frame, text=row[col], font=('times', 11),
                                 bg=bg_color, pady=5, padx=10,
                                 borderwidth=1, relief="solid", width=15)
                    cell.grid(row=r+3, column=c, padx=1, pady=1, sticky=tk.NSEW)
            
            # Update scrollable region
            data_frame.update_idletasks()
            canvas.config(scrollregion=canvas.bbox(tk.ALL))
        
        # Bind the selection event
        files_listbox.bind('<<ListboxSelect>>', show_file_data)
        
        # Select the first item if available
        if files_listbox.size() > 0:
            files_listbox.selection_set(0)
            files_listbox.event_generate('<<ListboxSelect>>')
    
    def export_attendance(self, attendance_records):
        """Export attendance records to CSV"""
        try:
            selection = simpledialog.askstring(
                "Export Attendance", 
                "Enter export filename (without extension):",
                initialvalue=f"attendance_export_{datetime.datetime.now().strftime('%Y%m%d')}"
            )
            
            if not selection:
                return
                
            # Create exports directory if it doesn't exist
            export_dir = os.path.join("Attendance", "Exports")
            os.makedirs(export_dir, exist_ok=True)
            
            # Combine all records into one DataFrame
            all_records = pd.concat(attendance_records.values())
            
            # Export to CSV
            export_path = os.path.join(export_dir, f"{selection}.csv")
            all_records.to_csv(export_path, index=False)
            
            messagebox.showinfo("Export Successful", 
                              f"Attendance records exported to:\n{export_path}")
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export attendance: {e}")
            print(f"Export error: {e}")
    
    def start_capture(self):
        """Start video capture using the CameraManager"""
        try:
            if not self.is_capturing:
                logger.info("Starting camera capture")
                
                # Initialize camera manager if not already done
                if not hasattr(self, 'camera_manager'):
                    from src.utils.camera_manager import CameraManager
                    self.camera_manager = CameraManager()
                
                # First try to get the preferred camera from settings
                try:
                    from src.utils.user_preferences import UserPreferences
                    preferences = UserPreferences()
                    preferences.load()
                    preferred_device = preferences.get_preference("camera", "device", "Auto-detect (default)")
                    
                    # Extract camera index from setting
                    if preferred_device != "Auto-detect (default)" and preferred_device != "Auto-detect (refreshed)":
                        # Extract index from "Camera X"
                        camera_id = int(preferred_device.split(" ")[1])
                        
                        # Try the specific camera first
                        camera_result = self.camera_manager.get_camera(camera_id)
                        
                        if not camera_result.success:
                            # If that fails, fall back to the best available camera
                            self.update_status(f"Preferred camera {camera_id} not available. Trying fallback options...")
                            camera_result = self.camera_manager.get_best_camera()
                    else:
                        # Use the best available camera
                        camera_result = self.camera_manager.get_best_camera()
                except (ImportError, Exception) as e:
                    logger.warning(f"Could not load preferences: {e}. Using default camera.")
                    camera_result = self.camera_manager.get_best_camera()
                
                if camera_result.success:
                    self.cam = camera_result.camera
                    self.camera_id = camera_result.camera_id
                    self.camera_info = camera_result.camera_info
                    
                    # Try to set camera properties if preferences exist
                    try:
                        # Get resolution preference
                        resolution = preferences.get_preference("camera", "resolution", "640x480")
                        width, height = map(int, resolution.split("x"))
                        
                        # Get FPS preference
                        fps = preferences.get_preference("camera", "fps", 30)
                        
                        # Set properties
                        import cv2
                        self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                        self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                        self.cam.set(cv2.CAP_PROP_FPS, fps)
                        
                        logger.info(f"Camera settings applied: {width}x{height} at {fps} FPS")
                    except Exception as e:
                        logger.warning(f"Could not apply camera settings: {e}")
                    
                    logger.info(f"Using camera: {self.camera_info}")
                    self.is_capturing = True
                    
                    # Start a thread to continuously update the video frame
                    self.capture_thread = threading.Thread(target=self._update_frame, daemon=True)
                    self.capture_thread.start()
                    
                    # Update UI elements
                    self.camera_status.config(text=f"Camera: Active (ID: {self.camera_id})", fg="green")
                    self.update_status(f"Camera started successfully: {self.camera_info}")
                    
                    # Try to enable the track_img_btn if it exists
                    try:
                        if hasattr(self, 'track_img_btn'):
                            self.track_img_btn.configure(state=tk.NORMAL)
                    except Exception as btn_err:
                        # Just log and continue if this fails
                        logger.debug(f"Could not enable track button: {btn_err}")
                    
                    return True
                else:
                    logger.error("Failed to initialize camera. No cameras available.")
                    self.update_status("Error: No cameras available", error=True)
                    messagebox.showerror("Camera Error", 
                                       "Failed to initialize camera. Please check your camera connections.")
                    return False
            
            return False
        except Exception as e:
            logger.exception(f"Error starting camera: {e}")
            self.update_status(f"Camera error: {str(e)}", error=True)
            messagebox.showerror("Camera Error", f"Failed to initialize camera: {str(e)}")
            return False
    
    def stop_capture(self):
        """Stop video capture and release resources"""
        try:
            if self.is_capturing:
                logger.info("Stopping camera capture")
                
                # Signal to the update thread to stop
                self.is_capturing = False
                
                # Wait for the capture thread to finish
                if hasattr(self, 'capture_thread') and self.capture_thread is not None and self.capture_thread.is_alive():
                    self.capture_thread.join(timeout=2.0)
                    if self.capture_thread.is_alive():
                        logger.warning("Capture thread did not terminate within timeout period")
                
                # Release camera resources
                if hasattr(self, 'cam') and self.cam is not None:
                    try:
                        # Attempt to release the camera multiple times if needed
                        release_attempts = 0
                        max_attempts = 3
                        while release_attempts < max_attempts:
                            try:
                                self.cam.release()
                                break
                            except Exception as release_err:
                                release_attempts += 1
                                logger.warning(f"Camera release attempt {release_attempts} failed: {release_err}")
                                if release_attempts >= max_attempts:
                                    raise
                                time.sleep(0.2)  # Wait before retrying
                                
                        self.cam = None
                        logger.info("Camera released successfully")
                    except Exception as cam_err:
                        logger.error(f"Failed to release camera: {cam_err}")
                
                # Clear camera references
                self.camera_id = None
                self.camera_info = None
                
                # Update UI elements
                self.camera_status.config(text="Camera: Inactive", fg="red")
                self.update_status("Camera stopped")
                
                # Reset the display frame
                self._display_default_frame()
                
                logger.info("Camera resources released successfully")
                return True
                
            return False
        except Exception as e:
            logger.exception(f"Error stopping camera: {e}")
            self.update_status(f"Error stopping camera: {str(e)}", error=True)
            return False
            
    def _display_default_frame(self):
        """Display the default frame when no camera is active"""
        try:
            # Clear existing widgets in the video frame
            for widget in self.video_frame.winfo_children():
                widget.destroy()
                
            # Add default message
            init_text = "Camera feed will appear here\nClick 'Take Images' to start"
            init_label = tk.Label(self.video_frame, text=init_text, bg="black", fg="white",
                                font=('times', 14))
            init_label.pack(expand=True)
            
        except Exception as e:
            logger.exception(f"Error displaying default frame: {e}")
            
    def _update_frame(self):
        """Update the video frame with the camera feed"""
        try:
            # Continue updating while capture is active
            while self.is_capturing:
                # Read a frame from the camera
                ret, frame = self.cam.read()
                
                # If frame was successfully read
                if ret:
                    # Display the frame
                    self.show_frame(frame)
                else:
                    logger.warning("Failed to read frame from camera")
                    
                    # Try to recover by reinitializing the camera
                    if hasattr(self, 'camera_manager') and hasattr(self, 'camera_id'):
                        try:
                            # Try to get the same camera again
                            camera_result = self.camera_manager.get_camera(self.camera_id)
                            
                            if camera_result.success:
                                logger.info(f"Successfully recovered camera connection to camera {self.camera_id}")
                                self.cam = camera_result.camera
                            else:
                                # If that fails, try to get any camera
                                logger.warning(f"Failed to recover camera {self.camera_id}, trying any available camera")
                                camera_result = self.camera_manager.get_best_camera()
                                
                                if camera_result.success:
                                    logger.info(f"Recovered with different camera: {camera_result.camera_info}")
                                    self.cam = camera_result.camera
                                    self.camera_id = camera_result.camera_id
                                    self.camera_info = camera_result.camera_info
                                    self.camera_status.config(text=f"Camera: Active (ID: {self.camera_id})", fg="green")
                                else:
                                    # If no camera is available, stop capturing
                                    logger.error("Could not recover camera connection, stopping capture")
                                    self.is_capturing = False
                                    break
                        except Exception as recovery_err:
                            logger.error(f"Error during camera recovery: {recovery_err}")
                            # Wait a bit before trying to read again
                            time.sleep(0.5)
                    else:
                        # Wait a bit before trying to read again
                        time.sleep(0.1)
                
                # Pause to avoid using too much CPU
                time.sleep(0.03)  # ~30 FPS
        except Exception as e:
            logger.exception(f"Error in update frame thread: {e}")
            self.is_capturing = False
    
    def clear_video_frame(self):
        """Clear the video frame and display a message"""
        # Clear any existing content
        for widget in self.video_frame.winfo_children():
            widget.destroy()
            
        # Add a message
        tk.Label(self.video_frame, text="Camera Inactive", bg="black", fg="white",
               font=('times', 14)).pack(expand=True)
            
    def show_frame(self, frame):
        """
        Display a frame in the video widget
        
        Args:
            frame (numpy.ndarray): Frame to display
        """
        try:
            if frame is None:
                return
                
            # Convert from BGR (OpenCV format) to RGB (PIL format)
            cv_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Convert to PIL format
            pil_image = Image.fromarray(cv_image)
            
            # Resize to fit the video frame while maintaining aspect ratio
            frame_width = self.video_frame.winfo_width()
            frame_height = self.video_frame.winfo_height()
            
            if frame_width > 1 and frame_height > 1:
                # Calculate new dimensions while maintaining aspect ratio
                img_width, img_height = pil_image.size
                ratio = min(frame_width/img_width, frame_height/img_height)
                new_width = int(img_width * ratio)
                new_height = int(img_height * ratio)
                
                pil_image = pil_image.resize((new_width, new_height), Image.LANCZOS)
            
            # Convert to Tkinter format
            tk_image = ImageTk.PhotoImage(pil_image)
            
            # Update the video frame
            self.video_frame.config(image=tk_image)
            self.video_frame.image = tk_image  # Keep a reference to prevent garbage collection
            
            # Process UI events to keep the interface responsive
            self.root.update_idletasks()
            
        except Exception as e:
            print(f"Error showing frame: {e}")
    
    def on_closing(self):
        """Handle window closing event"""
        if self.is_capturing:
            self.stop_capture()
        self.root.destroy()

    def enhanced_cleanup(self):
        """Run the enhanced cleanup utility to thoroughly clean Attendance and TrainingImage folders"""
        try:
            from src.utils.enhanced_cleanup import cleanup_attendance_folder, cleanup_training_images
            
            # Ask for confirmation
            confirm = messagebox.askyesno(
                "Confirm Enhanced Cleanup",
                "This will thoroughly clean and organize your Attendance and TrainingImage folders.\n\n"
                "It will:\n"
                "- Create backups of all files\n"
                "- Move files to appropriate folders\n"
                "- Remove duplicates\n"
                "- Optimize training images\n\n"
                "This process cannot be easily undone. Continue?"
            )
            
            if not confirm:
                return
                
            # Show info message
            messagebox.showinfo(
                "Enhanced Cleanup",
                "The system will now thoroughly clean and organize your folders.\n"
                "This may take some time. A backup will be created automatically.\n\n"
                "Please wait until the process completes."
            )
            
            # Run the cleanup in a separate thread to keep UI responsive
            def cleanup_thread():
                try:
                    # Update status
                    self.update_status("Running enhanced cleanup...")
                    
                    # Clean Attendance folder
                    attendance_success = cleanup_attendance_folder()
                    
                    # Clean TrainingImage folder
                    training_success = cleanup_training_images()
                    
                    # Show completion message
                    if attendance_success or training_success:
                        messagebox.showinfo(
                            "Cleanup Complete", 
                            "Enhanced cleanup has completed successfully.\n\n"
                            "Backups have been created in:\n"
                            "- Attendance/Backup\n"
                            "- TrainingImage/Backup\n\n"
                            "Optimized training images are in TrainingImage/Optimized."
                        )
                        self.update_status("Enhanced cleanup completed")
                    else:
                        messagebox.showwarning(
                            "Cleanup Notice", 
                            "No files were found to clean up."
                        )
                        self.update_status("Nothing to clean up")
                        
                except Exception as e:
                    messagebox.showerror("Cleanup Error", f"Error during enhanced cleanup: {e}")
                    self.update_status(f"Cleanup error: {e}")
            
            # Start the cleanup thread
            thread = threading.Thread(target=cleanup_thread)
            thread.daemon = True
            thread.start()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to run enhanced cleanup: {e}")

    def backup_to_cloud(self):
        attendance_files = [os.path.join('Attendance', f) for f in os.listdir('Attendance') if f.endswith('.csv')]
        for file_path in attendance_files:
            s3_path = f"attendance/{os.path.basename(file_path)}"
            success, message = self.cloud_sync.upload_file(file_path, s3_path)
            if success:
                self.update_status(f"Uploaded {file_path} to cloud")
            else:
                self.update_status(f"Failed to upload {file_path}: {message}")

    def restore_from_cloud(self):
        files, error = self.cloud_sync.list_files('attendance/')
        if error:
            self.update_status(f"Failed to list files: {error}")
            return
        for s3_path in files:
            file_path = os.path.join('Attendance', os.path.basename(s3_path))
            success, message = self.cloud_sync.download_file(s3_path, file_path)
            if success:
                self.update_status(f"Downloaded {s3_path} to {file_path}")
            else:
                self.update_status(f"Failed to download {s3_path}: {message}")

    def import_student_details(self):
        """Import student details from a CSV file"""
        from tkinter import filedialog
        import csv
        
        # Show file dialog
        file_path = filedialog.askopenfilename(
            title="Select Student Details CSV File",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
            initialdir=os.path.join(os.getcwd(), "StudentDetails")
        )
        
        if not file_path:
            return
            
        try:
            # Read the CSV file
            imported_students = []
            duplicate_students = []
            with open(file_path, 'r', newline='') as csvfile:
                reader = csv.reader(csvfile)
                headers = next(reader, None)  # Skip header row
                
                # Check if CSV has required columns
                required_columns = ['Enrollment', 'Name']
                if not headers or not all(col in headers for col in required_columns):
                    messagebox.showerror(
                        "Invalid CSV Format", 
                        "The CSV file must have 'Enrollment' and 'Name' columns."
                    )
                    return
                
                # Find column indices
                enrollment_idx = headers.index('Enrollment')
                name_idx = headers.index('Name')
                
                # Process each row
                for row in reader:
                    if len(row) > max(enrollment_idx, name_idx):
                        enrollment = row[enrollment_idx].strip()
                        name = row[name_idx].strip()
                        
                        if enrollment and name:
                            # Add student to database
                            success = self.db.add_student(enrollment, name)
                            if success:
                                imported_students.append(f"{name} ({enrollment})")
                            else:
                                duplicate_students.append(f"{name} ({enrollment})")
            
            # Show results
            if imported_students:
                result_message = f"Successfully imported {len(imported_students)} students:\n\n"
                result_message += "\n".join(imported_students[:10])  # Show first 10
                if len(imported_students) > 10:
                    result_message += f"\n...and {len(imported_students) - 10} more"
                    
                if duplicate_students:
                    result_message += f"\n\nSkipped {len(duplicate_students)} duplicate students"
                
                messagebox.showinfo("Import Complete", result_message)
                self.update_status(f"Imported {len(imported_students)} students")
            else:
                if duplicate_students:
                    messagebox.showwarning(
                        "Import Results", 
                        f"No new students were imported. {len(duplicate_students)} students already exist in the database."
                    )
                else:
                    messagebox.showwarning("Import Results", "No students found in the CSV file.")
                    
        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to import students: {e}")
            self.update_status(f"Import failed: {e}")
            
    def upload_student_images(self):
        """Upload student images for face recognition training"""
        from tkinter import filedialog
        import shutil
        
        # First, get the student information
        enrollment = self.student_id_entry.get()
        name = self.student_name_entry.get()
        
        if not enrollment or not name:
            # Try to get from a dialog
            student_info = self.select_student_dialog()
            if student_info:
                enrollment, name = student_info
            else:
                messagebox.showerror("Error", "Please enter or select a student first")
                return
        
        # Create TrainingImage directory if it doesn't exist
        if not os.path.isdir("TrainingImage"):
            os.makedirs("TrainingImage")
            
        # Show file dialog for selecting multiple image files
        file_paths = filedialog.askopenfilenames(
            title=f"Select Images for {name} (ID: {enrollment})",
            filetypes=[
                ("Image Files", "*.jpg *.jpeg *.png *.bmp"), 
                ("JPEG Files", "*.jpg *.jpeg"),
                ("PNG Files", "*.png"),
                ("All Files", "*.*")
            ]
        )
        
        if not file_paths:
            return
            
        try:
            # Process each selected image
            imported_count = 0
            skipped_count = 0
            
            # Create a progress dialog
            progress_window = tk.Toplevel(self.root)
            progress_window.title("Importing Images")
            progress_window.geometry("400x150")
            progress_window.resizable(False, False)
            progress_window.transient(self.root)  # Set as transient to main window
            
            # Center the progress window
            progress_window.update_idletasks()
            x = self.root.winfo_x() + (self.root.winfo_width() - progress_window.winfo_width()) // 2
            y = self.root.winfo_y() + (self.root.winfo_height() - progress_window.winfo_height()) // 2
            progress_window.geometry(f"+{x}+{y}")
            
            # Add a label
            info_label = tk.Label(
                progress_window, 
                text=f"Processing {len(file_paths)} images for {name}...", 
                padx=20, pady=10
            )
            info_label.pack()
            
            # Add a progress bar
            progress_var = tk.DoubleVar()
            progress_bar = ttk.Progressbar(
                progress_window, 
                variable=progress_var, 
                maximum=len(file_paths)
            )
            progress_bar.pack(fill=tk.X, padx=20, pady=10)
            
            # Status label
            status_label = tk.Label(progress_window, text="Initializing...", padx=20)
            status_label.pack()
            
            for i, file_path in enumerate(file_paths):
                # Update progress
                progress_var.set(i)
                status_label.config(text=f"Processing image {i+1} of {len(file_paths)}")
                progress_window.update_idletasks()
                
                try:
                    # Read the image
                    img = cv2.imread(file_path)
                    if img is None:
                        skipped_count += 1
                        continue
                        
                    # Convert to grayscale for face detection
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    
                    # Detect faces in the image
                    faces = self.face_detector.detect_faces(gray)
                    
                    if not faces:
                        skipped_count += 1
                        continue
                        
                    # Sort faces by area (largest first)
                    faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
                    
                    # Extract the largest face
                    x, y, w, h = faces[0]
                    face_img = gray[y:y+h, x:x+w]
                    
                    # Standardize size for better training
                    face_img = cv2.resize(face_img, (200, 200))
                    
                    # Save the face image with standardized filename
                    file_name = f"{name}.{enrollment}.{imported_count}.jpg"
                    save_path = os.path.join("TrainingImage", file_name)
                    
                    cv2.imwrite(save_path, face_img)
                    imported_count += 1
                    
                except Exception as e:
                    skipped_count += 1
                    print(f"Error processing image {file_path}: {e}")
            
            # Close progress dialog
            progress_window.destroy()
            
            # Show results
            if imported_count > 0:
                messagebox.showinfo(
                    "Import Complete",
                    f"Successfully imported {imported_count} face images for {name}.\n" +
                    (f"\n{skipped_count} images were skipped due to errors or no face detected." if skipped_count > 0 else "")
                )
                self.update_status(f"Imported {imported_count} images for {name}")
            else:
                messagebox.showwarning(
                    "Import Failed",
                    "No face images were imported. Please ensure the images contain clear, detectable faces."
                )
                self.update_status("Face image import failed")
                
        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to import images: {e}")
            self.update_status(f"Image import failed: {e}")
            
    def select_student_dialog(self):
        """Open a dialog to select a student from the database"""
        # Get students from database
        students_df = self.db.get_student_details()
        
        if students_df.empty:
            messagebox.showinfo("No Students", "No students are registered in the database.")
            return None
            
        # Create a dialog
        select_dialog = tk.Toplevel(self.root)
        select_dialog.title("Select Student")
        select_dialog.geometry("400x400")
        select_dialog.resizable(False, False)
        select_dialog.transient(self.root)
        select_dialog.grab_set()  # Make the dialog modal
        
        # Center the dialog
        select_dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - select_dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - select_dialog.winfo_height()) // 2
        select_dialog.geometry(f"+{x}+{y}")
        
        # Add a label
        tk.Label(
            select_dialog,
            text="Select a student:",
            font=('times', 12, 'bold'),
            pady=10
        ).pack(fill=tk.X)
        
        # Create a search frame
        search_frame = tk.Frame(select_dialog)
        search_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(search_frame, text="Search:").pack(side=tk.LEFT)
        
        search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=5)
        
        # Create a frame for the listbox with scrollbar
        list_frame = tk.Frame(select_dialog)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create scrollbar
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create listbox
        student_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            font=('times', 11),
            selectmode=tk.SINGLE,
            height=15
        )
        student_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=student_listbox.yview)
        
        # Populate listbox with students
        student_data = []  # List to store (enrollment, name) tuples
        
        for _, row in students_df.iterrows():
            enrollment = row['Enrollment']
            name = row['Name']
            student_listbox.insert(tk.END, f"{name} (ID: {enrollment})")
            student_data.append((enrollment, name))
            
        # Function to filter the listbox based on search
        def filter_students(*args):
            search_text = search_var.get().lower()
            student_listbox.delete(0, tk.END)
            student_data.clear()
            
            for _, row in students_df.iterrows():
                enrollment = row['Enrollment']
                name = row['Name']
                
                if search_text in name.lower() or search_text in enrollment.lower():
                    student_listbox.insert(tk.END, f"{name} (ID: {enrollment})")
                    student_data.append((enrollment, name))
                    
        # Bind the search entry to filter function
        search_var.trace("w", filter_students)
        
        # Variable to store the selected student
        selected_student = [None]  # Use a list for non-local reference
        
        # Function to handle selection
        def on_select():
            selection = student_listbox.curselection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a student.")
                return
                
            index = selection[0]
            selected_student[0] = student_data[index]
            select_dialog.destroy()
            
        def on_cancel():
            selected_student[0] = None
            select_dialog.destroy()
            
        # Add buttons
        button_frame = tk.Frame(select_dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        select_button = tk.Button(
            button_frame,
            text="Select",
            command=on_select,
            bg="#4CAF50",
            fg="white",
            font=('times', 11, 'bold'),
            width=10,
            height=1
        )
        select_button.pack(side=tk.RIGHT, padx=5)
        
        cancel_button = tk.Button(
            button_frame,
            text="Cancel",
            command=on_cancel,
            bg="#f44336",
            fg="white",
            font=('times', 11),
            width=10,
            height=1
        )
        cancel_button.pack(side=tk.RIGHT, padx=5)
        
        # Double-click to select
        student_listbox.bind("<Double-Button-1>", lambda e: on_select())
        
        # Set focus to search entry
        search_entry.focus_set()
        
        # Wait for the dialog to be closed
        self.root.wait_window(select_dialog)
        
        # Return the selected student
        return selected_student[0]

    def manage_subjects(self):
        """Open a dialog to manage subjects"""
        # Create a dialog
        subjects_dialog = tk.Toplevel(self.root)
        subjects_dialog.title("Manage Subjects")
        subjects_dialog.geometry("500x500")
        subjects_dialog.resizable(True, True)
        subjects_dialog.transient(self.root)
        subjects_dialog.grab_set()  # Make the dialog modal
        
        # Center the dialog
        subjects_dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - subjects_dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - subjects_dialog.winfo_height()) // 2
        subjects_dialog.geometry(f"+{x}+{y}")
        
        # Add a title
        title_label = tk.Label(
            subjects_dialog,
            text="Manage Subjects",
            font=('times', 16, 'bold'),
            pady=10
        )
        title_label.pack(fill=tk.X)
        
        # Create main content frame
        content_frame = tk.Frame(subjects_dialog)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Create left panel (subject list)
        list_frame = tk.LabelFrame(content_frame, text="Available Subjects")
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create scrollbar for listbox
        list_scrollbar = tk.Scrollbar(list_frame)
        list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create listbox for subjects
        subjects_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=list_scrollbar.set,
            font=('times', 12),
            selectmode=tk.SINGLE,
            width=25,
            height=15
        )
        subjects_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        list_scrollbar.config(command=subjects_listbox.yview)
        
        # Create right panel (actions)
        action_frame = tk.Frame(content_frame)
        action_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)
        
        # Add Subject frame
        add_frame = tk.LabelFrame(action_frame, text="Add New Subject")
        add_frame.pack(fill=tk.X, pady=10)
        
        # Add subject entry
        tk.Label(add_frame, text="Subject Name:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        subject_entry = tk.Entry(add_frame, width=20, font=('times', 11))
        subject_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # Add subject button
        add_btn = tk.Button(
            add_frame, 
            text="Add",
            bg="#4CAF50",
            fg="white",
            width=8,
            command=lambda: add_subject()
        )
        add_btn.grid(row=0, column=2, padx=5, pady=5)
        
        # Function to add a new subject
        def add_subject():
            subject = subject_entry.get().strip()
            if not subject:
                messagebox.showwarning("Warning", "Please enter a subject name")
                return
                
            # Check if subject already exists
            existing_subjects = load_subjects()
            if subject in existing_subjects:
                messagebox.showwarning("Warning", f"Subject '{subject}' already exists")
                return
                
            # Add to database or config
            try:
                # For this simple implementation, just save to a config file
                save_subject(subject)
                
                # Clear the entry
                subject_entry.delete(0, tk.END)
                
                # Update listbox
                refresh_subject_list()
                
                # Update quick subject buttons in main window
                update_quick_subjects()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add subject: {e}")
        
        # Delete subject frame
        delete_frame = tk.LabelFrame(action_frame, text="Delete Subject")
        delete_frame.pack(fill=tk.X, pady=10)
        
        # Delete selected subject button
        delete_btn = tk.Button(
            delete_frame, 
            text="Delete Selected",
            bg="#f44336",
            fg="white",
            width=15,
            command=lambda: delete_subject()
        )
        delete_btn.pack(padx=10, pady=10)
        
        # Function to delete a subject
        def delete_subject():
            selection = subjects_listbox.curselection()
            if not selection:
                messagebox.showwarning("Warning", "Please select a subject to delete")
                return
                
            subject = subjects_listbox.get(selection[0])
            confirm = messagebox.askyesno(
                "Confirm Delete",
                f"Are you sure you want to delete the subject '{subject}'?\n\n"
                "This will not delete any attendance records."
            )
            
            if confirm:
                try:
                    # Remove from database or config
                    remove_subject(subject)
                    
                    # Update listbox
                    refresh_subject_list()
                    
                    # Update quick subject buttons in main window
                    update_quick_subjects()
                    
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to delete subject: {e}")
        
        # Import/Export frame
        imp_exp_frame = tk.LabelFrame(action_frame, text="Import/Export")
        imp_exp_frame.pack(fill=tk.X, pady=10)
        
        # Import button
        import_btn = tk.Button(
            imp_exp_frame, 
            text="Import Subjects",
            bg="#2196F3",
            fg="white",
            width=15,
            command=lambda: import_subjects()
        )
        import_btn.pack(padx=10, pady=5)
        
        # Export button
        export_btn = tk.Button(
            imp_exp_frame, 
            text="Export Subjects",
            bg="#FF9800",
            fg="white",
            width=15,
            command=lambda: export_subjects()
        )
        export_btn.pack(padx=10, pady=5)
        
        # Function to import subjects from CSV
        def import_subjects():
            from tkinter import filedialog
            import csv
            
            file_path = filedialog.askopenfilename(
                title="Import Subjects from CSV",
                filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
            )
            
            if not file_path:
                return
                
            try:
                imported = []
                with open(file_path, 'r', newline='') as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if row and row[0].strip():
                            subject = row[0].strip()
                            save_subject(subject)
                            imported.append(subject)
                
                # Update listbox
                refresh_subject_list()
                
                # Update quick subject buttons in main window
                update_quick_subjects()
                
                if imported:
                    messagebox.showinfo("Import Complete", f"Successfully imported {len(imported)} subjects")
                else:
                    messagebox.showinfo("Import Complete", "No subjects were imported")
                    
            except Exception as e:
                messagebox.showerror("Import Error", f"Failed to import subjects: {e}")
        
        # Function to export subjects to CSV
        def export_subjects():
            from tkinter import filedialog
            import csv
            
            file_path = filedialog.asksaveasfilename(
                title="Export Subjects to CSV",
                defaultextension=".csv",
                filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
            )
            
            if not file_path:
                return
                
            try:
                subjects = load_subjects()
                with open(file_path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    for subject in subjects:
                        writer.writerow([subject])
                
                messagebox.showinfo("Export Complete", f"Successfully exported {len(subjects)} subjects to {file_path}")
                    
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export subjects: {e}")
        
        # Function to load subjects from config file
        def load_subjects():
            try:
                # Create config directory if it doesn't exist
                os.makedirs("config", exist_ok=True)
                
                # Check if subjects file exists
                subjects_file = os.path.join("config", "subjects.txt")
                if not os.path.exists(subjects_file):
                    # Create with default subjects
                    with open(subjects_file, 'w') as f:
                        f.write("Python\nJava\nWeb Dev\nData Science\n")
                
                # Read subjects from file
                with open(subjects_file, 'r') as f:
                    subjects = [line.strip() for line in f.readlines() if line.strip()]
                
                return subjects
                
            except Exception as e:
                print(f"Error loadingssubjects: {e}")
                return ["Python", "Java", "Web Dev", "Data Science"]  # Default subjects
        
        # Function to save a new subject
        def save_subject(subject):
            subjects = load_subjects()
            if subject not in subjects:
                subjects.append(subject)
                
            # Save back to file
            subjects_file = os.path.join("config", "subjects.txt")
            with open(subjects_file, 'w') as f:
                for s in subjects:
                    f.write(f"{s}\n")
        
        # Function to remove a subject
        def remove_subject(subject):
            subjects = load_subjects()
            if subject in subjects:
                subjects.remove(subject)
                
            # Save back to file
            subjects_file = os.path.join("config", "subjects.txt")
            with open(subjects_file, 'w') as f:
                for s in subjects:
                    f.write(f"{s}\n")
        
        # Function to refresh the subject list
        def refresh_subject_list():
            # Clear the listbox
            subjects_listbox.delete(0, tk.END)
            
            # Load subjects
            subjects = load_subjects()
            
            # Add to listbox
            for subject in subjects:
                subjects_listbox.insert(tk.END, subject)
        
        # Function to update quick subject buttons in main UI
        def update_quick_subjects():
            # Get all children of the subjects_frame
            children = self.root.nametowidget(".!frame.!frame.!labelframe2.!frame").winfo_children()
            
            # Remove existing buttons
            for child in children:
                child.destroy()
            
            # Load subjects
            subjects = load_subjects()
            
            # Add quick subject buttons (max 4)
            quick_subjects = subjects[:4]  # Take first 4 subjects
            for i, subject in enumerate(quick_subjects):
                btn = tk.Button(
                    self.root.nametowidget(".!frame.!frame.!labelframe2.!frame"), 
                    text=subject, 
                    command=lambda s=subject: self.set_subject(s),
                    bg="#673AB7", 
                    fg="white", 
                    font=('times', 10)
                )
                btn.grid(row=0, column=i, padx=5, pady=5)
        
        # Initial load of subjects
        refresh_subject_list()
        
        # Add a close button at the bottom
        close_btn = tk.Button(
            subjects_dialog, 
            text="Close",
            command=subjects_dialog.destroy,
            bg="#607D8B",
            fg="white",
            font=('times', 12),
            width=10,
            height=1
        )
        close_btn.pack(pady=15)
        
        # Set focus to subject entry
        subject_entry.focus_set()
        
        # Wait for the dialog to close
        self.root.wait_window(subjects_dialog)

    def open_analytics_dashboard(self):
        """Open the attendance analytics dashboard"""
        try:
            # Check if we have attendance data to show
            subject = self.subject_entry.get()
            if not subject:
                # Show all subjects if none selected
                attendance_records = self.db.get_all_attendance_records()
            else:
                attendance_records = self.db.get_attendance_records(subject=subject)
            
            if not attendance_records:
                messagebox.showwarning(
                    "No Data",
                    "No attendance records found. Please take attendance first."
                )
                return
                
            # Create and show analytics dashboard
            dashboard_window = tk.Toplevel(self.root)
            dashboard = AnalyticsDashboard(dashboard_window)
            
            # Pass attendance data
            dashboard.load_attendance_data(attendance_records)
            
            # Set window properties
            dashboard_window.title("Attendance Analytics Dashboard")
            dashboard_window.geometry("1000x700")
            dashboard_window.protocol("WM_DELETE_WINDOW", lambda: dashboard_window.destroy())
            
            # Center on screen
            dashboard_window.update_idletasks()
            x = self.root.winfo_x() + (self.root.winfo_width() - dashboard_window.winfo_width()) // 2
            y = self.root.winfo_y() + (self.root.winfo_height() - dashboard_window.winfo_height()) // 2
            dashboard_window.geometry(f"+{x}+{y}")
            
        except Exception as e:
            messagebox.showerror("Analytics Error", f"Failed to open analytics dashboard: {e}")
            self.update_status(f"Analytics error: {e}")
            
    def generate_reports(self):
        """Generate attendance reports"""
        try:
            from tkinter import filedialog
            import csv
            
            # Get subject
            subject = self.subject_entry.get()
            
            # Create reports dialog
            reports_window = tk.Toplevel(self.root)
            reports_window.title("Generate Reports")
            reports_window.geometry("500x550")
            reports_window.resizable(False, False)
            
            # TODO: Implement report generation functionality
            
        except Exception as e:
            messagebox.showerror("Report Error", f"Failed to generate report: {e}")
            self.update_status(f"Report generation failed: {e}")

    def open_settings(self):
        """Open application settings dialog"""
        try:
            # Use our new AppConfig and SettingsDialog classes
            from src.ui.settings import AppConfig, SettingsDialog
            
            # Create AppConfig instance
            config = AppConfig()
            
            # Open settings dialog
            dialog = SettingsDialog(self.root, config)
            
            # Wait for the dialog to close before applying changes
            self.root.wait_window(dialog.dialog)
            
            # Apply settings changes
            # Update camera settings
            camera_id = config.get("camera.id", 0)
            resolution = config.get("camera.resolution", [640, 480])
            fps = config.get("camera.fps", 30)
            
            if hasattr(self, 'camera_manager'):
                # Update camera settings in existing manager
                if hasattr(self.camera_manager, 'set_preferred_settings'):
                    self.camera_manager.set_preferred_settings(camera_id, resolution, fps)
            
            # Update application title
            app_name = config.get("app_name", "Face Recognition Attendance System")
            self.root.title(app_name)
            
            # Update UI based on settings
            if config.get("ui.show_status_bar", True):
                # Show status bar
                self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
                self.camera_status.pack(side=tk.RIGHT)
            else:
                # Hide status bar
                self.status_label.pack_forget()
                self.camera_status.pack_forget()
                
            # Set default subject if specified
            default_subject = config.get("attendance.default_subject", "")
            if default_subject and not self.subject_entry.get():
                self.subject_entry.delete(0, tk.END)
                self.subject_entry.insert(0, default_subject)
            
            # Update face detection parameters
            if hasattr(self, 'face_detector'):
                self.face_detector.set_confidence_threshold(
                    config.get("face_detection.confidence_threshold", 60)
                )
            
            # Update status
            self.update_status("Settings applied")
                
        except Exception as e:
            messagebox.showerror("Settings Error", f"Error opening settings: {e}")
            logger.exception(f"Error opening settings: {e}")

    def camera_settings(self):
        """Open camera settings dialog"""
        try:
            # Import the new CameraSettingsDialog
            from src.ui.camera_settings_dialog import CameraSettingsDialog
            from src.ui.settings import AppConfig
            
            # Initialize camera manager if needed
            if not hasattr(self, 'camera_manager'):
                self.camera_manager = CameraManager()
            
            # Get config
            config = AppConfig()
            
            # Create and show the camera settings dialog
            dialog = CameraSettingsDialog(self.root, self.camera_manager, config)
            
            # Wait for the dialog to close before applying changes
            self.root.wait_window(dialog.dialog)
            
            # Update camera settings if needed
            camera_id = config.get("camera.id", 0)
            resolution = config.get("camera.resolution", [640, 480])
            fps = config.get("camera.fps", 30)
            flip_image = config.get("camera.flip_image", False)
            
            # Update camera manager with new settings
            if hasattr(self, 'camera_manager'):
                self.camera_manager.set_preferred_settings(
                    camera_id=camera_id,
                    resolution=resolution,
                    fps=fps,
                    flip=flip_image
                )
            
            # Update status
            self.update_status("Camera settings updated")
                
        except Exception as e:
            messagebox.showerror("Camera Settings", f"Error opening camera settings: {e}")
            logger.exception(f"Error opening camera settings: {e}")

    def group_attendance(self):
        """Mark attendance for a group of students at once"""
        # Get subject
        subject = self.subject_entry.get()
        if not subject:
            messagebox.showerror("Error", "Please enter a subject name first")
            return
            
        # Get students from database
        students_df = self.db.get_student_details()
        if students_df.empty:
            messagebox.showwarning("Warning", "No students registered in the database")
            return
            
        # Create dialog
        group_dialog = tk.Toplevel(self.root)
        group_dialog.title(f"Group Attendance - {subject}")
        group_dialog.geometry("600x500")
        group_dialog.resizable(True, True)
        group_dialog.transient(self.root)
        group_dialog.grab_set()
        
        # Center dialog
        group_dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - group_dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - group_dialog.winfo_height()) // 2
        group_dialog.geometry(f"+{x}+{y}")
        
        # Dialog header
        header_frame = tk.Frame(group_dialog, pady=10)
        header_frame.pack(fill=tk.X)
        
        tk.Label(
            header_frame,
            text=f"Mark Group Attendance for: {subject}",
            font=('times', 14, 'bold')
        ).pack(side=tk.LEFT, padx=20)
        
        # Date/time frame
        date_frame = tk.Frame(group_dialog)
        date_frame.pack(fill=tk.X, padx=20, pady=5)
        
        # Current date and time
        now = datetime.datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")
        
        # Date field
        tk.Label(date_frame, text="Date:", width=10, anchor=tk.W).grid(row=0, column=0, padx=5, pady=5)
        date_var = tk.StringVar(value=date_str)
        date_entry = tk.Entry(date_frame, textvariable=date_var, width=15)
        date_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # Time field
        tk.Label(date_frame, text="Time:", width=10, anchor=tk.W).grid(row=0, column=2, padx=5, pady=5)
        time_var = tk.StringVar(value=time_str)
        time_entry = tk.Entry(date_frame, textvariable=time_var, width=15)
        time_entry.grid(row=0, column=3, padx=5, pady=5)
        
        # Search field
        search_frame = tk.Frame(group_dialog)
        search_frame.pack(fill=tk.X, padx=20, pady=5)
        
        tk.Label(search_frame, text="Search:", width=10, anchor=tk.W).pack(side=tk.LEFT, padx=5)
        search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Student list frame with checkboxes
        list_frame = tk.Frame(group_dialog)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Create a canvas with scrollbar for the student list
        canvas_frame = tk.Frame(list_frame)
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbar
        scrollbar = tk.Scrollbar(canvas_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Canvas
        canvas = tk.Canvas(canvas_frame, yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=canvas.yview)
        
        # Frame inside canvas for checkboxes
        students_frame = tk.Frame(canvas)
        students_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create a window for the frame
        canvas.create_window((0, 0), window=students_frame, anchor=tk.NW)
        
        # Track selected students
        selected_students = {}
        
        # Status tracking
        status_var = tk.StringVar(value="0 students selected")
        
        # Populate the list
        def populate_students(search_text=""):
            # Clear previous widgets
            for widget in students_frame.winfo_children():
                widget.destroy()
                
            # Header row
            header_frame = tk.Frame(students_frame)
            header_frame.pack(fill=tk.X, pady=5)
            
            # Select all checkbox
            select_all_var = tk.BooleanVar(value=False)
            cb = tk.Checkbutton(
                header_frame, 
                text="Select All", 
                variable=select_all_var,
                command=lambda: toggle_all(select_all_var.get())
            )
            cb.pack(side=tk.LEFT, padx=5)
            
            # Column headers
            tk.Label(header_frame, text="ID", width=15, font=('times', 11, 'bold')).pack(side=tk.LEFT, padx=5)
            tk.Label(header_frame, text="Student Name", width=30, font=('times', 11, 'bold')).pack(side=tk.LEFT, padx=5)
            
            # Filter students based on search
            filtered_df = students_df
            if search_text:
                search_text = search_text.lower()
                filtered_df = students_df[
                    students_df['Name'].str.lower().str.contains(search_text) | 
                    students_df['Enrollment'].str.lower().str.contains(search_text)
                ]
            
            # No students found
            if filtered_df.empty:
                no_students_label = tk.Label(
                    students_frame,
                    text="No students match your search",
                    font=('times', 12),
                    fg="gray",
                    pady=20
                )
                no_students_label.pack(fill=tk.X)
                return
            
            # Create checkbox for each student
            for i, (_, row) in enumerate(filtered_df.iterrows()):
                enrollment = row['Enrollment']
                name = row['Name']
                
                # Row frame with alternating background
                bg_color = "#f0f0f0" if i % 2 == 0 else "white"
                row_frame = tk.Frame(students_frame, bg=bg_color)
                row_frame.pack(fill=tk.X, pady=1)
                
                # Student checkbox
                var = tk.BooleanVar(value=enrollment in selected_students)
                cb = tk.Checkbutton(
                    row_frame, 
                    variable=var,
                    bg=bg_color,
                    command=lambda e=enrollment, n=name, v=var: toggle_student(e, n, v.get())
                )
                cb.pack(side=tk.LEFT, padx=5)
                
                # Student info
                tk.Label(row_frame, text=enrollment, width=15, anchor=tk.W, bg=bg_color).pack(side=tk.LEFT, padx=5)
                tk.Label(row_frame, text=name, width=30, anchor=tk.W, bg=bg_color).pack(side=tk.LEFT, padx=5)
            
            # Update canvas scroll region
            students_frame.update_idletasks()
            canvas.config(scrollregion=canvas.bbox(tk.ALL))
            
            # Update status
            update_status()
        
        # Toggle all students
        def toggle_all(selected):
            if selected:
                # Select all visible students
                for widget in students_frame.winfo_children():
                    if isinstance(widget, tk.Frame) and widget.winfo_children():
                        for child in widget.winfo_children():
                            if isinstance(child, tk.Checkbutton):
                                # Extract the enrollment and name from the command
                                cmd = child.cget('command')
                                if cmd and len(cmd.__defaults__) >= 2:
                                    enrollment, name = cmd.__defaults__[0], cmd.__defaults__[1]
                                    selected_students[enrollment] = name
                                # Set the checkbutton to selected
                                child.select()
            else:
                # Deselect all students
                selected_students.clear()
                for widget in students_frame.winfo_children():
                    if isinstance(widget, tk.Frame) and widget.winfo_children():
                        for child in widget.winfo_children():
                            if isinstance(child, tk.Checkbutton):
                                child.deselect()
                                
            # Update status
            update_status()
        
        # Toggle individual student selection
        def toggle_student(enrollment, name, selected):
            if selected:
                selected_students[enrollment] = name
            else:
                if enrollment in selected_students:
                    del selected_students[enrollment]
                    
            # Update status
            update_status()
        
        # Update status text
        def update_status():
            count = len(selected_students)
            status_var.set(f"{count} student{'s' if count != 1 else ''} selected")
        
        # Bind search to update the list
        def on_search_change(*args):
            populate_students(search_var.get())
            
        search_var.trace("w", on_search_change)
        
        # Status indicator
        status_label = tk.Label(group_dialog, textvariable=status_var, anchor=tk.W, pady=5)
        status_label.pack(fill=tk.X, padx=20)
        
        # Buttons frame
        buttons_frame = tk.Frame(group_dialog, pady=10)
        buttons_frame.pack(fill=tk.X, padx=20)
        
        # Mark attendance button
        mark_btn = tk.Button(
            buttons_frame,
            text="Mark Attendance",
            command=lambda: mark_attendance(),
            bg="#4CAF50",
            fg="white",
            font=('times', 12, 'bold'),
            width=15,
            height=2
        )
        mark_btn.pack(side=tk.RIGHT, padx=5)
        
        # Cancel button
        cancel_btn = tk.Button(
            buttons_frame,
            text="Cancel",
            command=group_dialog.destroy,
            width=10,
            height=2
        )
        cancel_btn.pack(side=tk.RIGHT, padx=5)
        
        # Mark attendance function
        def mark_attendance():
            # Check if any students are selected
            if not selected_students:
                messagebox.showwarning("Warning", "No students selected")
                return
                
            # Get date and time
            try:
                date_val = date_var.get()
                time_val = time_var.get()
                
                # Validate date format (YYYY-MM-DD)
                datetime.datetime.strptime(date_val, "%Y-%m-%d")
                
                # Validate time format (HH:MM:SS)
                datetime.datetime.strptime(time_val, "%H:%M:%S")
                
            except ValueError:
                messagebox.showerror("Error", "Invalid date or time format. Use YYYY-MM-DD and HH:MM:SS")
                return
                
            # Create a new attendance file or use existing
            file_prefix = f"Group Attendance{subject}"
            file_name = f"{file_prefix}_{date_val.replace('-', '')}_{time_val.replace(':', '')}.csv"
            file_path = os.path.join("Attendance", file_name)
            
            # Check if directory exists
            if not os.path.isdir("Attendance"):
                os.makedirs("Attendance")
            
            # Create or open file
            success_count = 0
            
            try:
                # Create file with header if it doesn't exist
                if not os.path.exists(file_path):
                    with open(file_path, 'w', newline='') as f:
                        f.write("Enrollment,Name,Date,Time\n")
                
                # Mark attendance for each selected student
                for enrollment, name in selected_students.items():
                    success = self.db.mark_attendance(enrollment, name, subject, date_val, time_val)
                    if success:
                        success_count += 1
                        
                # Show results
                if success_count > 0:
                    messagebox.showinfo(
                        "Success", 
                        f"Marked attendance for {success_count} student{'s' if success_count != 1 else ''}"
                    )
                    self.update_status(f"Marked group attendance for {success_count} students")
                    group_dialog.destroy()
                else:
                    messagebox.showerror(
                        "Error", 
                        "Failed to mark attendance for any students"
                    )
                    
            except Exception as e:
                messagebox.showerror("Error", f"Failed to mark attendance: {e}")
                logger.exception(f"Error marking group attendance: {e}")
        
        # Initial population of the list
        populate_students()
        
        # Set focus to search entry
        search_entry.focus_set()
