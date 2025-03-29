"""
Attendance View for Face Detection Attendance System
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
import csv

from src.utils.config_manager import ConfigManager
from src.face_recognition.face_detector import FaceDetector

# Set up logging
logger = logging.getLogger(__name__)

class AttendanceView(ctk.CTkFrame):
    """Attendance View with face detection for marking attendance"""
    
    def __init__(self, master, user_data):
        """
        Initialize the attendance view
        
        Args:
            master: Parent widget
            user_data: User data dictionary
        """
        super().__init__(master)
        
        # Save references
        self.user_data = user_data
        
        # Get configuration
        config_manager = ConfigManager()
        self.config = config_manager.get_config()
        
        # Initialize variables
        self.camera_feed = None
        self.camera_thread = None
        self.is_capturing = False
        self.camera_id = self.config.get("camera", {}).get("id", 0)
        self.recognition_method = self.config.get("face_recognition", {}).get("method", "hybrid")
        self.confidence_threshold = self.config.get("face_recognition", {}).get("threshold", 0.60)
        
        # Initialize face detector
        self.face_detector = FaceDetector(
            method=self.recognition_method,
            threshold=self.confidence_threshold
        )
        
        # Load subject data
        self.subjects = self._get_subjects()
        
        # Initialize attendance list
        self.attendance_list = []
        self.detected_faces = set()  # To avoid duplicate entries
        
        # Create UI elements
        self._setup_ui()
        
        logger.info("Attendance View initialized")
    
    def _setup_ui(self):
        """Set up the attendance UI"""
        # Configure grid layout (2x2)
        self.grid_rowconfigure((0, 1), weight=1)
        self.grid_columnconfigure((0, 1), weight=1)
        
        # Top left: Camera Feed Panel
        self.camera_panel = ctk.CTkFrame(self)
        self.camera_panel.grid(row=0, column=0, padx=(20, 10), pady=(20, 10), sticky="nsew")
        self.camera_panel.grid_rowconfigure(1, weight=1)
        self.camera_panel.grid_columnconfigure(0, weight=1)
        
        # Camera panel title
        self.camera_title = ctk.CTkLabel(
            self.camera_panel,
            text="Camera Feed",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.camera_title.grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")
        
        # Camera feed
        self.camera_frame = ctk.CTkFrame(self.camera_panel)
        self.camera_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.camera_frame.grid_rowconfigure(0, weight=1)
        self.camera_frame.grid_columnconfigure(0, weight=1)
        
        # Camera view
        self.camera_view = ctk.CTkLabel(
            self.camera_frame,
            text="Camera feed will appear here",
            font=ctk.CTkFont(size=14)
        )
        self.camera_view.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
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
        
        # Subject selection
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
        self.subject_dropdown.grid(row=0, column=1, padx=(10, 20), pady=10, sticky="ew")
        
        # Attendance mode (auto/manual)
        self.mode_frame = ctk.CTkFrame(self.controls_panel)
        self.mode_frame.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.mode_frame.grid_columnconfigure(0, weight=1)
        
        self.mode_label = ctk.CTkLabel(
            self.mode_frame,
            text="Attendance Mode:",
            anchor="w"
        )
        self.mode_label.grid(row=0, column=0, padx=20, pady=(10, 5), sticky="w")
        
        self.mode_var = ctk.StringVar(value="Auto")
        
        self.auto_radio = ctk.CTkRadioButton(
            self.mode_frame,
            text="Automatic (Face Detection)",
            variable=self.mode_var,
            value="Auto"
        )
        self.auto_radio.grid(row=1, column=0, padx=(40, 0), pady=(5, 5), sticky="w")
        
        self.manual_radio = ctk.CTkRadioButton(
            self.mode_frame,
            text="Manual Entry",
            variable=self.mode_var,
            value="Manual",
            command=self._toggle_mode
        )
        self.manual_radio.grid(row=2, column=0, padx=(40, 0), pady=(5, 10), sticky="w")
        
        # Manual entry fields (initially hidden)
        self.manual_entry_frame = ctk.CTkFrame(self.controls_panel)
        self.manual_entry_frame.grid(row=3, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.manual_entry_frame.grid_columnconfigure(1, weight=1)
        
        # Student ID
        self.id_label = ctk.CTkLabel(
            self.manual_entry_frame,
            text="Student ID:",
            anchor="w",
            width=100
        )
        self.id_label.grid(row=0, column=0, padx=(20, 10), pady=(10, 5), sticky="w")
        
        self.id_entry = ctk.CTkEntry(
            self.manual_entry_frame,
            placeholder_text="Enter student ID"
        )
        self.id_entry.grid(row=0, column=1, padx=(0, 20), pady=(10, 5), sticky="ew")
        
        # Student name
        self.name_label = ctk.CTkLabel(
            self.manual_entry_frame,
            text="Name:",
            anchor="w",
            width=100
        )
        self.name_label.grid(row=1, column=0, padx=(20, 10), pady=(5, 10), sticky="w")
        
        self.name_entry = ctk.CTkEntry(
            self.manual_entry_frame,
            placeholder_text="Enter student name"
        )
        self.name_entry.grid(row=1, column=1, padx=(0, 20), pady=(5, 10), sticky="ew")
        
        # Add student button
        self.add_student_button = ctk.CTkButton(
            self.manual_entry_frame,
            text="Add Student",
            command=self._add_manual_attendance
        )
        self.add_student_button.grid(row=2, column=0, columnspan=2, padx=20, pady=(5, 10), sticky="ew")
        
        # Hide manual entry fields initially
        self.manual_entry_frame.grid_remove()
        
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
        
        self.save_button = ctk.CTkButton(
            self.action_frame,
            text="Save Attendance",
            command=self._save_attendance,
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            state="disabled"
        )
        self.save_button.grid(row=0, column=1, padx=(5, 5), pady=10, sticky="ew")
        
        # Status message
        self.status_label = ctk.CTkLabel(
            self.controls_panel,
            text="",
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
        
        # Use native Tkinter Treeview
        columns = ("id", "name", "time")
        self.tree = tk.ttk.Treeview(self.tree_frame, columns=columns, show="headings")
        
        # Define headings
        self.tree.heading("id", text="Student ID")
        self.tree.heading("name", text="Name")
        self.tree.heading("time", text="Time")
        
        # Define columns
        self.tree.column("id", width=100)
        self.tree.column("name", width=250)
        self.tree.column("time", width=150)
        
        # Add scrollbars
        vsb = tk.ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        hsb = tk.ttk.Scrollbar(self.tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Pack treeview and scrollbars
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        # Configure style for treeview
        style = tk.ttk.Style()
        bg_color = self._get_bg_color()
        text_color = self._get_text_color()
        
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
        """Get list of subjects from attendance files and student details"""
        subjects = set()
        
        # Check attendance files
        attendance_dir = "Attendance"
        if os.path.exists(attendance_dir):
            for file in os.listdir(attendance_dir):
                if file.endswith(".csv"):
                    # Extract subject from filename
                    parts = file.split('_')
                    if len(parts) > 0:
                        subjects.add(parts[0])
        
        # Check backup files
        backup_dir = os.path.join("backups", "attendance_backup")
        if os.path.exists(backup_dir):
            for file in os.listdir(backup_dir):
                if file.endswith(".csv"):
                    parts = file.split('_')
                    if len(parts) > 0:
                        subjects.add(parts[0])
        
        # Check student details
        students_file = os.path.join("StudentDetails", "StudentDetails.csv")
        if os.path.exists(students_file):
            try:
                df = pd.read_csv(students_file)
                if 'Course' in df.columns:
                    subjects.update(df['Course'].unique())
            except Exception as e:
                logger.warning(f"Failed to read student details: {e}")
        
        # Default subjects if none found
        if not subjects:
            subjects = {"Python", "Maths", "Physics", "Chemistry"}
        
        return sorted(list(subjects))
    
    def _toggle_mode(self):
        """Toggle between auto and manual attendance modes"""
        mode = self.mode_var.get()
        
        if mode == "Auto":
            self.manual_entry_frame.grid_remove()
            self.start_button.configure(state="normal")
            self.show_status("Auto attendance mode selected. Start camera to begin.", color="blue")
        else:
            self.manual_entry_frame.grid()
            # If camera is running, stop it
            if self.is_capturing:
                self._stop_camera()
            self.start_button.configure(state="disabled")
            self.show_status("Manual attendance mode selected. Enter student details.", color="blue")
    
    def _start_camera(self):
        """Start or stop camera feed"""
        if self.is_capturing:
            self._stop_camera()
            return
        
        try:
            # Initialize the camera
            self.camera_feed = cv2.VideoCapture(self.camera_id)
            
            if not self.camera_feed.isOpened():
                self.show_status("Failed to open camera. Please check your camera connection.", color="red")
                logger.error(f"Failed to open camera with ID: {self.camera_id}")
                return
            
            # Update UI
            self.is_capturing = True
            self.start_button.configure(text="Stop Camera")
            self.save_button.configure(state="normal")
            
            # Start camera thread
            self.camera_thread = threading.Thread(target=self._camera_loop)
            self.camera_thread.daemon = True
            self.camera_thread.start()
            
            self.show_status("Camera started. Face detection active.", color="green")
            logger.info("Camera started for attendance")
        
        except Exception as e:
            self.show_status(f"Error starting camera: {str(e)}", color="red")
            logger.error(f"Error starting camera: {e}")
    
    def _stop_camera(self):
        """Stop the camera feed"""
        self.is_capturing = False
        
        if self.camera_feed is not None:
            self.camera_feed.release()
            self.camera_feed = None
        
        # Update UI
        self.start_button.configure(text="Start Camera")
        
        # Clear the camera view
        self.camera_view.configure(text="Camera feed will appear here", image=None)
        
        logger.info("Camera stopped for attendance")
    
    def _camera_loop(self):
        """Camera feed loop with face detection"""
        while self.is_capturing:
            try:
                # Read frame
                ret, frame = self.camera_feed.read()
                if not ret:
                    logger.warning("Failed to read frame from camera")
                    time.sleep(0.1)
                    continue
                
                # Process frame for face detection
                processed_frame, detected_faces = self.face_detector.detect_and_recognize(frame)
                
                # If faces were detected, update attendance list
                if detected_faces:
                    self._update_attendance_list(detected_faces)
                
                # Convert to RGB for PIL
                rgb_frame = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
                
                # Convert to PIL Image
                pil_img = Image.fromarray(rgb_frame)
                
                # Resize to fit in the label
                pil_img = self._resize_image_to_fit(pil_img, 500, 400)
                
                # Convert to PhotoImage
                tk_img = ImageTk.PhotoImage(pil_img)
                
                # Update label with new image
                self.camera_view.configure(image=tk_img, text="")
                self.camera_view.image = tk_img  # Keep a reference
            
            except Exception as e:
                logger.error(f"Error in camera loop: {e}")
                time.sleep(0.1)
        
        logger.info("Camera loop ended")
    
    def _update_attendance_list(self, detected_faces):
        """Update attendance list with newly detected faces"""
        current_time = datetime.now().strftime("%H:%M:%S")
        
        for student_id, name, confidence in detected_faces:
            # Skip if already in attendance list
            if student_id in self.detected_faces:
                continue
            
            # Add to detected faces set
            self.detected_faces.add(student_id)
            
            # Add to attendance list
            self.attendance_list.append({
                "id": student_id,
                "name": name,
                "time": current_time
            })
            
            # Add to treeview
            self.tree.insert("", "end", values=(student_id, name, current_time))
            
            # Log the detection
            logger.info(f"Detected student: {name} (ID: {student_id}) with confidence: {confidence:.2f}")
            self.show_status(f"Detected: {name} (ID: {student_id})", color="green")
    
    def _add_manual_attendance(self):
        """Add attendance entry manually"""
        student_id = self.id_entry.get().strip()
        name = self.name_entry.get().strip()
        
        if not student_id or not name:
            self.show_status("Please enter both student ID and name", color="red")
            return
        
        # Skip if already in attendance list
        if student_id in self.detected_faces:
            self.show_status(f"Student ID {student_id} is already in the attendance list", color="orange")
            return
        
        # Add to attendance list
        current_time = datetime.now().strftime("%H:%M:%S")
        self.attendance_list.append({
            "id": student_id,
            "name": name,
            "time": current_time
        })
        
        # Add to detected faces set
        self.detected_faces.add(student_id)
        
        # Add to treeview
        self.tree.insert("", "end", values=(student_id, name, current_time))
        
        # Clear entry fields
        self.id_entry.delete(0, 'end')
        self.name_entry.delete(0, 'end')
        
        # Focus ID field
        self.id_entry.focus()
        
        # Update status
        self.show_status(f"Added student: {name} (ID: {student_id})", color="green")
        logger.info(f"Manually added student: {name} (ID: {student_id})")
        
        # Enable save button if this is the first entry
        if len(self.attendance_list) == 1:
            self.save_button.configure(state="normal")
    
    def _save_attendance(self):
        """Save attendance to CSV file"""
        if not self.attendance_list:
            self.show_status("No attendance entries to save", color="orange")
            return
        
        try:
            # Get current subject
            subject = self.subject_var.get()
            if not subject:
                self.show_status("Please select a subject", color="red")
                return
            
            # Get current date and time
            now = datetime.now()
            date_str = now.strftime("%Y-%m-%d")
            time_str = now.strftime("%H-%M-%S")
            
            # Determine filename
            attendance_dir = "Attendance"
            os.makedirs(attendance_dir, exist_ok=True)
            
            # Try both automatic and manual filenames
            mode = self.mode_var.get()
            if mode == "Manual":
                filename = os.path.join(attendance_dir, f"Manually Attendance{subject}_{date_str.replace('-', '_')}_Time_{time_str.replace('-', '_')}.csv")
            else:
                filename = os.path.join(attendance_dir, f"{subject}_{date_str}_{time_str}.csv")
            
            # Create CSV file
            with open(filename, "w", newline="") as csvfile:
                fieldnames = ["ID", "Name", "Date", "Time"]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                # Write entries
                for entry in self.attendance_list:
                    writer.writerow({
                        "ID": entry["id"],
                        "Name": entry["name"],
                        "Date": date_str,
                        "Time": entry["time"]
                    })
            
            # Save backup copy
            backup_dir = os.path.join("backups", "attendance_backup")
            os.makedirs(backup_dir, exist_ok=True)
            backup_filename = os.path.join(backup_dir, os.path.basename(filename))
            
            with open(backup_filename, "w", newline="") as csvfile:
                fieldnames = ["ID", "Name", "Date", "Time"]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                # Write entries
                for entry in self.attendance_list:
                    writer.writerow({
                        "ID": entry["id"],
                        "Name": entry["name"],
                        "Date": date_str,
                        "Time": entry["time"]
                    })
            
            # Update status
            self.show_status(f"Attendance saved successfully: {os.path.basename(filename)}", color="green")
            logger.info(f"Attendance saved: {filename} with {len(self.attendance_list)} entries")
            
            # Reset attendance list
            self.reset_attendance()
            
        except Exception as e:
            self.show_status(f"Error saving attendance: {str(e)}", color="red")
            logger.error(f"Error saving attendance: {e}")
    
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
    
    def _resize_image_to_fit(self, pil_img, width, height):
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
    
    def show_status(self, message, color="green"):
        """Show status message with specified color"""
        self.status_label.configure(text=message, text_color=color)
        
        # Reset message after 5 seconds if it's a success message
        if color == "green":
            self.after(5000, lambda: self.status_label.configure(text=""))
    
    def cleanup(self):
        """Clean up resources before destroying the widget"""
        # Stop the camera if it's running
        if self.is_capturing:
            self._stop_camera()