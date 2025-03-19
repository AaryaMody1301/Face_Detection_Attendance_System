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

from src.face_recognition.detector import FaceDetector
from src.database.db_handler import AttendanceDB
from src.models.student import Student
from src.utils.image_utils import draw_rectangle
from src.utils.attendance_analytics import AttendanceAnalytics
from src.ui.analytics_dashboard import AnalyticsDashboard

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
            self.db = AttendanceDB()
            
            # Video capture
            self.cam = None
            self.is_capturing = False
            self.capture_thread = None
            
            # Current subject
            self.current_subject = None
            
            # Load the trained model if it exists
            model_path = "TrainingImageLabel/trainner.yml"
            if os.path.isfile(model_path):
                print(f"Loading model from {model_path}")
                self.face_detector.load_model(model_path)
            else:
                print(f"Model file not found: {model_path}")
            
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
        file_menu.add_command(label="Organize Folders", command=self.organize_folders)
        file_menu.add_command(label="Enhanced Cleanup", command=self.enhanced_cleanup)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)
        
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
        
        # Main frame
        self.main_frame = tk.Frame(self.root, bg="grey80")
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
    
    def set_subject(self, subject):
        """Set the subject entry field with the provided subject"""
        self.subject_entry.delete(0, tk.END)
        self.subject_entry.insert(0, subject)
        self.update_status(f"Subject set to: {subject}")
    
    def update_status(self, message):
        """
        Update the status label
        
        Args:
            message (str): Status message
        """
        try:
            if hasattr(self, 'status_label') and self.status_label.winfo_exists():
                self.status_label.config(text=f"Status: {message}")
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
                    
                    # Create a copy of the image for display
                    display_img = img.copy()
                    
                    # Convert to grayscale for face detection
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    
                    # Apply histogram equalization for better contrast
                    gray = cv2.equalizeHist(gray)
                    
                    # Detect faces
                    faces = self.face_detector.detect_faces(gray)
                    
                    if len(faces) == 0:
                        # No faces detected, just display the frame
                        self.show_frame(display_img)
                        continue
                    
                    # Process each detected face
                    for (x, y, w, h) in faces:
                        # Get face region
                        face_roi = gray[y:y+h, x:x+w]
                        
                        # Standardize face size for more consistent recognition
                        face_roi = cv2.resize(face_roi, (100, 100))
                        
                        # Recognize face
                        face_id, conf = self.face_detector.recognizer.predict(face_roi)
                        
                        # Process recognition result
                        if str(face_id) not in recognition_buffer:
                            recognition_buffer[str(face_id)] = []
                        
                        # Add current confidence to buffer (lower is better for OpenCV LBPH)
                        if conf < 100:  # Only add reasonable confidences
                            recognition_buffer[str(face_id)].append(conf)
                            
                            # Limit buffer size
                            if len(recognition_buffer[str(face_id)]) > buffer_size:
                                recognition_buffer[str(face_id)] = recognition_buffer[str(face_id)][-buffer_size:]
                        
                        # Check if we have enough frames with good confidence for this face
                        good_frames = sum(1 for c in recognition_buffer[str(face_id)] if c < confidence_threshold)
                        
                        # If we have enough good frames, mark attendance
                        if good_frames >= min_recognized_frames:
                            # Find student name from ID
                            student_data = students_df[students_df['Enrollment'] == str(face_id)]
                            if not student_data.empty:
                                student_name = student_data.iloc[0]['Name']
                                
                                # Mark attendance if not already marked
                                student_key = f"{face_id}_{student_name}"
                                if student_key not in recognized_students:
                                    self.db.mark_attendance(str(face_id), student_name, file_path=attendance_file)
                                    recognized_students[student_key] = True
                                    self.update_status(f"✓ Marked attendance for {student_name}")
                                
                                # Display name on frame
                                label = f"{student_name} ({face_id})"
                                color = (0, 255, 0)  # Green for good match
                            else:
                                # Unknown student ID
                                label = f"Unknown ID: {face_id}"
                                color = (0, 165, 255)  # Orange for unknown ID
                        else:
                            # Not enough good frames yet
                            label = "Processing..."
                            if len(recognition_buffer[str(face_id)]) > 0:
                                avg_conf = sum(recognition_buffer[str(face_id)]) / len(recognition_buffer[str(face_id)])
                                label = f"Processing... ({good_frames}/{min_recognized_frames})"
                            color = (255, 120, 0)  # Light blue for processing
                        
                        # Draw rectangle around face and display name
                        cv2.rectangle(display_img, (x, y), (x+w, y+h), color, 2)
                        
                        # Calculate position for label (handle if on top edge)
                        y_pos = y - 10 if y - 10 > 10 else y + h + 20
                        cv2.putText(display_img, label, (x, y_pos),
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                    
                    # Display attendance count on the image
                    attendance_count = len(recognized_students)
                    attendance_text = f"Attendance Count: {attendance_count}"
                    cv2.putText(display_img, attendance_text, (10, 30),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.8, (50, 50, 255), 2)
                    
                    # Display the current subject
                    subject_text = f"Subject: {subject}"
                    cv2.putText(display_img, subject_text, (10, 60),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50, 50, 255), 2)
                    
                    # Display elapsed time
                    elapsed_time = time.time() - start_time
                    time_text = f"Time: {int(elapsed_time)}s"
                    cv2.putText(display_img, time_text, (10, 90),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50, 50, 255), 2)
                    
                    # Display the video frame
                    self.show_frame(display_img)
                    
                except Exception as e:
                    print(f"Error in tracking: {e}")
                    time.sleep(0.1)  # Brief pause on error
            
            # Tracking has stopped
            attendance_count = len(recognized_students)
            self.update_status(f"Tracking stopped. {attendance_count} students marked present.")
            
            # Display summary when done
            if attendance_count > 0:
                summary = f"Attendance Summary\n\nSubject: {subject}\nDate: {date}\nTime: {time_str}\n\nStudents Present ({attendance_count}):\n"
                for student_key in recognized_students:
                    student_id, student_name = student_key.split("_", 1)
                    summary += f"• {student_name} (ID: {student_id})\n"
                    
                messagebox.showinfo("Attendance Complete", summary)
            else:
                messagebox.showinfo("Attendance Complete", "No students were recognized during this session.")
        
        # Start the tracking thread
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
        success = self.db.mark_attendance(enrollment, name, file_path=file_path)
        
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
                             command=lambda: self.export_attendance(attendance_records),
                             bg="#4CAF50", fg="white", font=('times', 12))
        export_btn.pack(side=tk.RIGHT, padx=10)
        
        # Create a frame for the main content
        content_frame = tk.Frame(attendance_window, bg="grey90")
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create a frame for the list of files with scrollbar
        files_frame = tk.Frame(content_frame, bg="white", bd=1, relief=tk.GROOVE)
        files_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10, anchor=tk.N)
        
        tk.Label(files_frame, text="Attendance Files:", bg="grey80", 
               font=('times', 12, 'bold'), width=40).pack(fill=tk.X)
        
        # Add a scrollbar to the listbox
        list_scroll = tk.Scrollbar(files_frame)
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        files_listbox = tk.Listbox(files_frame, width=40, height=20, 
                                 yscrollcommand=list_scroll.set, font=('times', 11))
        files_listbox.pack(fill=tk.BOTH, expand=True)
        list_scroll.config(command=files_listbox.yview)
        
        # Create a frame for the attendance data with scrollbars
        data_container = tk.Frame(content_frame, bg="white", bd=1, relief=tk.GROOVE)
        data_container.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Scrollbars for the data frame
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
        """Start video capture"""
        try:
            if self.is_capturing:
                return True  # Already capturing
                
            # Try to open the camera
            self.cam = cv2.VideoCapture(0)
            if not self.cam.isOpened():
                messagebox.showerror("Error", "Could not open camera")
                return False
            
            # Set camera properties for better quality
            self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.cam.set(cv2.CAP_PROP_FPS, 30)
                
            self.is_capturing = True
            self.camera_status.config(text="Camera: Active", fg="green")
            return True
        except Exception as e:
            messagebox.showerror("Camera Error", f"Error starting camera: {e}")
            self.is_capturing = False
            self.camera_status.config(text="Camera: Error", fg="red")
            return False
            
    def stop_capture(self):
        """Stop video capture"""
        try:
            self.is_capturing = False
            # Wait for thread to finish if it exists
            if self.capture_thread and self.capture_thread.is_alive():
                self.capture_thread.join(timeout=1.0)
                
            # Release the camera
            if self.cam is not None:
                self.cam.release()
                self.cam = None
                
            self.camera_status.config(text="Camera: Inactive", fg="black")
            
            # Clear the video frame and show message
            self.clear_video_frame()
            
        except Exception as e:
            print(f"Error stopping capture: {e}")
    
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


def main():
    """Main entry point of the application"""
    root = tk.Tk()
    app = FaceAttendanceApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()