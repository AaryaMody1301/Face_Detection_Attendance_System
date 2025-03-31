"""
Classic Attendance Application
"""
import os
import tkinter as tk
from tkinter import ttk, messagebox
import logging
import threading
from datetime import datetime

# Import from core modules
from src.core.database.db_handler import DatabaseHandler
from src.core.face_recognition.face_detector import FaceDetector
from src.core.utils.config_manager import ConfigManager
from src.ui.student_registration import StudentRegistrationView
from src.ui.training_view import TrainingView

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ClassicAttendanceApp(tk.Tk):
    """
    Classic Attendance Application class
    """
    
    def __init__(self, auth_system):
        """Initialize the main application"""
        super().__init__()
        
        # Store authentication system
        self.auth_system = auth_system
        self.current_user = auth_system.get_current_user()
        
        # Set up theme constants - for compatibility with modern UI
        self.button_highlight_color = "#3498db"  # Default highlight color for buttons
        
        # Load configuration
        self.config = ConfigManager()
        
        # Configure window
        self.title(f"Face Detection Attendance System - {self.current_user.get('role', 'User').capitalize()}")
        self.geometry("1100x700")
        self.minsize(800, 600)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Initialize database
        self.db = DatabaseHandler()
        
        # Create menu
        self.create_menu()
        
        # Create main frame
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create status bar
        self.status_bar = ttk.Frame(self)
        self.status_bar.pack(fill="x", side="bottom")
        
        self.status_label = ttk.Label(
            self.status_bar,
            text="Ready",
            anchor="w",
            padding=(10, 5)
        )
        self.status_label.pack(side="left", fill="x", expand=True)
        
        # Show dashboard by default
        self.show_dashboard()
    
    def create_menu(self):
        """Create the main menu bar"""
        self.menubar = tk.Menu(self)
        
        # Create File menu
        self.file_menu = tk.Menu(self.menubar, tearoff=0)
        self.file_menu.add_command(label="Dashboard", command=self.show_dashboard)
        self.file_menu.add_command(label="Register Student", command=self.show_student_registration)
        self.file_menu.add_command(label="Mark Attendance", command=self.show_attendance)
        self.file_menu.add_command(label="Train Model", command=self.show_face_training)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Settings", command=self.show_settings)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Logout", command=self.logout)
        self.file_menu.add_command(label="Exit", command=self.exit_app)
        self.menubar.add_cascade(label="File", menu=self.file_menu)
        
        # Create Help menu
        self.help_menu = tk.Menu(self.menubar, tearoff=0)
        self.help_menu.add_command(label="Help", command=self.show_help)
        self.help_menu.add_command(label="About", command=self.show_about)
        self.menubar.add_cascade(label="Help", menu=self.help_menu)
        
        # Set the menu
        self.config(menu=self.menubar)
    
    def show_dashboard(self):
        """Show the dashboard"""
        # Clear current content
        self.clear_main_frame()
        
        # Set window title
        self.title("Face Detection Attendance System - Dashboard")
        
        # Create dashboard elements
        dashboard_header = ttk.Label(
            self.main_frame,
            text="Face Detection Attendance System",
            font=("Helvetica", 16, "bold")
        )
        dashboard_header.pack(pady=20)
        
        # User info
        user_frame = ttk.LabelFrame(self.main_frame, text="User Information")
        user_frame.pack(fill="x", padx=20, pady=10)
        
        ttk.Label(
            user_frame,
            text=f"Welcome, {self.current_user.get('full_name', self.current_user.get('username', 'User'))}",
            font=("Helvetica", 12)
        ).pack(padx=10, pady=5, anchor="w")
        
        ttk.Label(
            user_frame,
            text=f"Role: {self.current_user.get('role', 'User').capitalize()}",
            font=("Helvetica", 10)
        ).pack(padx=10, pady=5, anchor="w")
        
        # Quick actions
        actions_frame = ttk.LabelFrame(self.main_frame, text="Quick Actions")
        actions_frame.pack(fill="x", padx=20, pady=10)
        
        # Create buttons for quick actions
        register_btn = ttk.Button(
            actions_frame,
            text="Register New Student",
            command=self.show_student_registration
        )
        register_btn.pack(side="left", padx=10, pady=10)
        
        attendance_btn = ttk.Button(
            actions_frame,
            text="Mark Attendance",
            command=self.show_attendance
        )
        attendance_btn.pack(side="left", padx=10, pady=10)
        
        train_btn = ttk.Button(
            actions_frame,
            text="Train Face Recognition",
            command=self.show_face_training
        )
        train_btn.pack(side="left", padx=10, pady=10)
        
        # Update status
        self.status_label.config(text="Dashboard loaded successfully")
    
    def show_student_registration(self):
        """Show the student registration interface"""
        # Clear current content
        self.clear_main_frame()
        
        # Set window title
        self.title("Face Detection Attendance System - Student Registration")
        
        try:
            # Create registration view
            self.registration_view = StudentRegistrationView(self.main_frame)
            self.registration_view.pack(fill="both", expand=True)
            
            # Update status
            self.status_label.config(text="Ready to register new student")
        
        except Exception as e:
            logger.error(f"Error showing student registration: {e}")
            # Show error message
            error_label = ttk.Label(
                self.main_frame,
                text="Error: Could not load student registration view",
                font=("Helvetica", 12, "bold"),
                foreground="red"
            )
            error_label.pack(pady=50)
    
    def show_attendance(self):
        """Show the attendance interface"""
        # Clear current content
        self.clear_main_frame()
        
        # Set window title
        self.title("Face Detection Attendance System - Mark Attendance")
        
        # Create attendance marking form
        attendance_header = ttk.Label(
            self.main_frame,
            text="Mark Attendance",
            font=("Helvetica", 16, "bold")
        )
        attendance_header.pack(pady=20)
        
        # Form for attendance
        form_frame = ttk.Frame(self.main_frame)
        form_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Will be replaced with actual attendance view later
        ttk.Label(
            form_frame,
            text="Attendance marking functionality will be implemented here",
            font=("Helvetica", 12)
        ).pack(pady=50)
        
        # Update status
        self.status_label.config(text="Ready to mark attendance")
    
    def show_face_training(self):
        """Show the face training interface"""
        # Clear current content
        self.clear_main_frame()
        
        # Set window title
        self.title("Face Detection Attendance System - Face Training")
        
        try:
            # Create training view
            self.training_view = TrainingView(self.main_frame)
            self.training_view.pack(fill="both", expand=True)
            
            # Update status
            self.status_label.config(text="Ready to train face recognition model")
            
        except Exception as e:
            logger.error(f"Error showing face training: {e}")
            # Show error message
            error_label = ttk.Label(
                self.main_frame,
                text="Error: Could not load face training view",
                font=("Helvetica", 12, "bold"),
                foreground="red"
            )
            error_label.pack(pady=50)
    
    def show_settings(self):
        """Show the settings dialog"""
        # Clear current content
        self.clear_main_frame()
        
        # Set window title
        self.title("Face Detection Attendance System - Settings")
        
        # Create settings elements
        settings_header = ttk.Label(
            self.main_frame,
            text="Settings",
            font=("Helvetica", 16, "bold")
        )
        settings_header.pack(pady=20)
        
        # Will be replaced with actual settings view later
        ttk.Label(
            self.main_frame,
            text="Settings functionality will be implemented here",
            font=("Helvetica", 12)
        ).pack(pady=50)
        
        # Update status
        self.status_label.config(text="Settings loaded")
    
    def show_help(self):
        """Show help dialog"""
        messagebox.showinfo(
            "Help",
            "Face Detection Attendance System Help\n\n"
            "1. Register students using the Student Registration\n"
            "2. Train the face recognition model\n"
            "3. Mark attendance using face detection\n\n"
            "For more information, please refer to the documentation."
        )
    
    def show_about(self):
        """Show about dialog"""
        messagebox.showinfo(
            "About",
            "Face Detection Attendance System\n"
            "Version 1.0\n\n"
            "© 2023 All Rights Reserved"
        )
    
    def clear_main_frame(self):
        """Clear all widgets from the main frame"""
        for widget in self.main_frame.winfo_children():
            widget.destroy()
    
    def logout(self):
        """Log out the current user"""
        confirm = messagebox.askyesno("Logout", "Are you sure you want to logout?")
        if confirm:
            # Clean up resources
            self.cleanup_resources()
            
            # Log out user
            self.auth_system.logout()
            
            # Close application
            self.destroy()
    
    def exit_app(self):
        """Exit the application"""
        self.on_closing()
    
    def on_closing(self):
        """Handle window closing event"""
        confirm = messagebox.askyesno("Exit", "Are you sure you want to exit?")
        if confirm:
            # Clean up resources
            self.cleanup_resources()
            
            # Log out user
            self.auth_system.logout()
            
            # Close application
            self.destroy()
    
    def cleanup_resources(self):
        """Clean up resources before closing"""
        # Close database connection
        if hasattr(self, 'db'):
            try:
                self.db.close()
            except Exception as e:
                logger.error(f"Error closing database connection: {e}")
        
        # Close any active view
        if hasattr(self, 'registration_view') and hasattr(self.registration_view, 'on_close'):
            try:
                self.registration_view.on_close()
            except Exception as e:
                logger.error(f"Error closing registration view: {e}")
        
        if hasattr(self, 'training_view') and hasattr(self.training_view, 'on_close'):
            try:
                self.training_view.on_close()
            except Exception as e:
                logger.error(f"Error closing training view: {e}")

def main():
    """Main entry point for the classic attendance application"""
    from src.core.auth.auth_system import AuthSystem
    
    # Initialize auth system
    auth_system = AuthSystem()
    
    # Check if user is logged in
    if not auth_system.is_logged_in():
        # TODO: Show login screen
        # For now, just use a test user
        auth_system.login("admin", "admin")
    
    # Create and run app
    app = ClassicAttendanceApp(auth_system)
    app.mainloop()

if __name__ == "__main__":
    main() 