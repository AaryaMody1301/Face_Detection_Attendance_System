"""
Dashboard for Face Detection Attendance System
"""
import os
import logging
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk
from datetime import datetime

# Import components
from src.ui.attendance_view import AttendanceView
from src.ui.settings import SettingsPage
from src.ui.analytics_dashboard import AnalyticsDashboard
from src.ui.student_registration import StudentRegistrationView

# Set up logging
logger = logging.getLogger(__name__)

class Dashboard(ctk.CTkFrame):
    """Main dashboard widget with tabbed interface"""
    
    def __init__(self, master, user_data, logout_callback):
        """
        Initialize the dashboard
        
        Args:
            master: Parent widget
            user_data: User data dictionary
            logout_callback: Callback function for logout
        """
        super().__init__(master)
        
        # Save references
        self.user_data = user_data
        self.logout_callback = logout_callback
        self.username = user_data.get('username', 'User')
        self.role = user_data.get('role', 'user')
        
        # Initialize components
        self.attendance_view = None
        self.settings_page = None
        self.analytics_dashboard = None
        self.student_registration = None
        
        # Create UI elements
        self._setup_ui()
        
        logger.info(f"Dashboard initialized for user: {self.username} ({self.role})")
    
    def _setup_ui(self):
        """Set up the dashboard UI"""
        # Configure grid layout (1x1)
        self.grid_rowconfigure(1, weight=1)  # Content takes all available space
        self.grid_columnconfigure(0, weight=1)
        
        # Create header frame
        self.header_frame = ctk.CTkFrame(self, corner_radius=0, fg_color=("gray90", "gray16"))
        self.header_frame.grid(row=0, column=0, sticky="ew")
        self.header_frame.grid_columnconfigure(1, weight=1)
        
        # App title
        self.title_label = ctk.CTkLabel(
            self.header_frame, 
            text="Face Detection Attendance System",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.title_label.grid(row=0, column=0, padx=20, pady=(10, 10), sticky="w")
        
        # Current date and time
        current_datetime = datetime.now().strftime("%A, %d %B %Y")
        self.date_label = ctk.CTkLabel(
            self.header_frame,
            text=current_datetime,
            font=ctk.CTkFont(size=12)
        )
        self.date_label.grid(row=0, column=1, padx=20, pady=(10, 10), sticky="e")
        
        # User info and logout button
        self.user_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.user_frame.grid(row=0, column=2, padx=20, pady=(10, 10), sticky="e")
        
        # User avatar
        self.avatar_label = ctk.CTkLabel(self.user_frame, text="👤", font=ctk.CTkFont(size=20))
        self.avatar_label.grid(row=0, column=0, padx=(0, 5))
        
        # Username
        self.user_label = ctk.CTkLabel(
            self.user_frame,
            text=f"{self.username} ({self.role})",
            font=ctk.CTkFont(size=12)
        )
        self.user_label.grid(row=0, column=1, padx=(0, 10))
        
        # Logout button
        self.logout_button = ctk.CTkButton(
            self.user_frame,
            text="Logout",
            command=self.logout_callback,
            width=80,
            height=25,
            font=ctk.CTkFont(size=12)
        )
        self.logout_button.grid(row=0, column=2)
        
        # Create tabview for main content
        self.tab_view = ctk.CTkTabview(self)
        self.tab_view.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
        # Add tabs
        self.attendance_tab = self.tab_view.add("Attendance")
        self.student_tab = self.tab_view.add("Student Registration")
        self.analytics_tab = self.tab_view.add("Analytics")
        self.settings_tab = self.tab_view.add("Settings")
        
        # Configure tab content frames
        for tab in [self.attendance_tab, self.student_tab, self.analytics_tab, self.settings_tab]:
            tab.grid_rowconfigure(0, weight=1)
            tab.grid_columnconfigure(0, weight=1)
        
        # Initialize tab contents
        self._init_attendance_tab()
        self._init_student_registration_tab()
        self._init_analytics_tab()
        self._init_settings_tab()
        
        # Show Attendance tab by default
        self.tab_view.set("Attendance")
    
    def _init_attendance_tab(self):
        """Initialize the attendance tab"""
        self.attendance_view = AttendanceView(self.attendance_tab, self.user_data)
        self.attendance_view.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    
    def _init_student_registration_tab(self):
        """Initialize the student registration tab"""
        self.student_registration = StudentRegistrationView(self.student_tab)
        self.student_registration.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    
    def _init_analytics_tab(self):
        """Initialize the analytics tab"""
        self.analytics_dashboard = AnalyticsDashboard(self.analytics_tab)
        self.analytics_dashboard.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    
    def _init_settings_tab(self):
        """Initialize the settings tab"""
        self.settings_page = SettingsPage(self.settings_tab)
        self.settings_page.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    
    def cleanup(self):
        """Clean up resources before destroying the widget"""
        try:
            # Clean up attendance view
            if self.attendance_view and hasattr(self.attendance_view, 'cleanup') and callable(self.attendance_view.cleanup):
                self.attendance_view.cleanup()
            
            # Clean up other components if needed
            logger.info("Dashboard cleanup complete")
        except Exception as e:
            logger.error(f"Error during dashboard cleanup: {e}")