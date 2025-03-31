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
        
        # Create header frame with gradient effect
        self.header_frame = ctk.CTkFrame(self, corner_radius=0, fg_color=("#0078D7", "#2D5F9A"))
        self.header_frame.grid(row=0, column=0, sticky="ew")
        self.header_frame.grid_columnconfigure(1, weight=1)
        
        # App title with better typography
        self.title_label = ctk.CTkLabel(
            self.header_frame, 
            text="Face Detection Attendance System",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=("white", "white")
        )
        self.title_label.grid(row=0, column=0, padx=20, pady=(15, 15), sticky="w")
        
        # Current date and time with improved styling
        current_datetime = datetime.now().strftime("%A, %d %B %Y")
        self.date_label = ctk.CTkLabel(
            self.header_frame,
            text=current_datetime,
            font=ctk.CTkFont(size=13),
            text_color=("white", "white")
        )
        self.date_label.grid(row=0, column=1, padx=20, pady=(15, 15), sticky="e")
        
        # User info and logout button with enhanced visual treatment
        self.user_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.user_frame.grid(row=0, column=2, padx=20, pady=(15, 15), sticky="e")
        
        # User avatar with circle shape
        self.avatar_label = ctk.CTkLabel(self.user_frame, text="👤", font=ctk.CTkFont(size=22), text_color=("white", "white"))
        self.avatar_label.grid(row=0, column=0, padx=(0, 8))
        
        # Username with role
        self.user_label = ctk.CTkLabel(
            self.user_frame,
            text=f"{self.username} ({self.role})",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=("white", "white")
        )
        self.user_label.grid(row=0, column=1, padx=(0, 15))
        
        # Logout button with hover effect
        self.logout_button = ctk.CTkButton(
            self.user_frame,
            text="Logout",
            command=self.logout_callback,
            width=90,
            height=32,
            font=ctk.CTkFont(size=13),
            fg_color=("#0063B1", "#1D4F8A"),
            hover_color=("#004E8C", "#15406F"),
            corner_radius=6
        )
        self.logout_button.grid(row=0, column=2)
        
        # Create tabview for main content with enhanced style
        self.tab_view = ctk.CTkTabview(
            self,
            fg_color=("gray95", "gray15"),
            segmented_button_fg_color=("#e0e0e0", "#2d2d2d"),
            segmented_button_selected_color=("#0078D7", "#2D5F9A"),
            segmented_button_unselected_color=("#f0f0f0", "#333333"),
            segmented_button_selected_hover_color=("#0063B1", "#1D4F8A"),
            segmented_button_unselected_hover_color=("#e0e0e0", "#3d3d3d")
        )
        self.tab_view.grid(row=1, column=0, sticky="nsew", padx=15, pady=15)
        
        # Add tabs with better padding and sizing
        self.attendance_tab = self.tab_view.add("Attendance")
        self.student_tab = self.tab_view.add("Student Registration")
        self.analytics_tab = self.tab_view.add("Analytics")
        self.settings_tab = self.tab_view.add("Settings")
        
        # Configure tab content frames with better spacing
        for tab in [self.attendance_tab, self.student_tab, self.analytics_tab, self.settings_tab]:
            tab.grid_rowconfigure(0, weight=1)
            tab.grid_columnconfigure(0, weight=1)
            tab.configure(corner_radius=10)
        
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
        self.attendance_view.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
    
    def _init_student_registration_tab(self):
        """Initialize the student registration tab"""
        self.student_registration = StudentRegistrationView(self.student_tab)
        self.student_registration.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
    
    def _init_analytics_tab(self):
        """Initialize the analytics tab"""
        self.analytics_dashboard = AnalyticsDashboard(self.analytics_tab)
        self.analytics_dashboard.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
    
    def _init_settings_tab(self):
        """Initialize the settings tab"""
        self.settings_page = SettingsPage(self.settings_tab)
        self.settings_page.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
    
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