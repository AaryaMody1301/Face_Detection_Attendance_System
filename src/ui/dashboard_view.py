"""
Dashboard view for the attendance system
"""
import os
import tkinter as tk
import customtkinter as ctk
import datetime
import logging
import threading
from PIL import Image, ImageTk, ImageDraw
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from src.core.database.db_handler import DatabaseHandler
import gc
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DashboardView(ctk.CTkFrame):
    """Dashboard view showing attendance overview and statistics"""
    
    def __init__(self, master, auth_system, db_handler, **kwargs):
        super().__init__(master, **kwargs)
        
        self.master = master
        self.auth_system = auth_system
        self.db = db_handler
        self.current_user = auth_system.get_current_user()
        
        # Performance metrics data
        self.performance_data = None
        self.notification_count = 0
        
        # Create UI elements
        self.create_widgets()
        
        # Load data
        self.load_data()
    
    def create_widgets(self):
        """Create enhanced dashboard widgets"""
        try:
            # Use a grid layout for better organization
            self.grid_rowconfigure((0, 1, 2), weight=0)  # Header, stats, charts
            self.grid_rowconfigure(3, weight=1)  # Activity feed
            self.grid_columnconfigure(0, weight=1)
            
            # Set default background color
            self.configure(fg_color=("gray95", "gray17"))
            
            # ===== HEADER SECTION =====
            # Create header with welcome message and date
            self.header_frame = ctk.CTkFrame(self, corner_radius=12, fg_color=("#ffffff", "#1e1e1e"))
            self.header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
            self.header_frame.grid_columnconfigure(0, weight=1)
            
            # Welcome message with user name
            welcome_text = f"Welcome back, {self.current_user.get('username', 'User')}"
            self.welcome_label = ctk.CTkLabel(
                self.header_frame,
                text=welcome_text,
                font=ctk.CTkFont(size=24, weight="bold")
            )
            self.welcome_label.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
            
            # Current date with nice format
            date_str = datetime.datetime.now().strftime("%A, %B %d, %Y")
            self.date_label = ctk.CTkLabel(
                self.header_frame,
                text=date_str,
                font=ctk.CTkFont(size=14),
                text_color=("gray50", "gray70")
            )
            self.date_label.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="w")
            
            # ===== STATS SECTION =====
            # Create stats cards in a grid layout
            self.stats_frame = ctk.CTkFrame(self, corner_radius=12, fg_color="transparent")
            self.stats_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
            self.stats_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
            
            # Create four stat cards with consistent styling
            self.total_attendance_card = self._create_stat_card(
                self.stats_frame, 
                "Total Attendance", 
                "0", 
                "↑ 0%", 
                0, 
                0
            )
            
            self.unique_students_card = self._create_stat_card(
                self.stats_frame, 
                "Unique Students", 
                "0", 
                "Today", 
                0, 
                1
            )
            
            self.today_attendance_card = self._create_stat_card(
                self.stats_frame, 
                "Today's Attendance", 
                "0", 
                "Records", 
                0, 
                2
            )
            
            self.avg_attendance_card = self._create_stat_card(
                self.stats_frame, 
                "Average Attendance", 
                "0%", 
                "This week", 
                0, 
                3
            )
            
            # ===== CHARTS SECTION =====
            # Create charts container with two charts side by side
            self.charts_frame = ctk.CTkFrame(self, corner_radius=12, fg_color="transparent")
            self.charts_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=10)
            self.charts_frame.grid_columnconfigure((0, 1), weight=1)
            
            # Left chart: Attendance trends
            self.trend_chart_frame = ctk.CTkFrame(self.charts_frame, corner_radius=10, fg_color=("#ffffff", "#1e1e1e"))
            self.trend_chart_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=0)
            
            self.trend_chart_title = ctk.CTkLabel(
                self.trend_chart_frame,
                text="Attendance Trends",
                font=ctk.CTkFont(size=16, weight="bold")
            )
            self.trend_chart_title.pack(anchor="w", padx=15, pady=(15, 5))
            
            # Period selector for trend chart
            self.period_frame = ctk.CTkFrame(self.trend_chart_frame, fg_color="transparent")
            self.period_frame.pack(fill="x", padx=15, pady=(0, 5))
            
            self.period_var = ctk.StringVar(value="week")
            periods = ["week", "month", "semester"]
            
            for i, period in enumerate(periods):
                period_btn = ctk.CTkButton(
                    self.period_frame,
                    text=period.capitalize(),
                    width=80,
                    height=25,
                    corner_radius=15,
                    fg_color=("#0078D7", "#2D5F9A") if period == "week" else ("gray85", "gray25"),
                    hover_color=("#0063B1", "#1D4F8A"),
                    command=lambda p=period: self._on_period_change(p),
                    font=ctk.CTkFont(size=12)
                )
                period_btn.pack(side="left", padx=(0 if i == 0 else 5, 0))
            
            # Chart placeholder
            self.trend_chart_placeholder = ctk.CTkFrame(self.trend_chart_frame, fg_color="transparent")
            self.trend_chart_placeholder.pack(fill="both", expand=True, padx=15, pady=(5, 15))
            
            # Right chart: Course distribution
            self.course_chart_frame = ctk.CTkFrame(self.charts_frame, corner_radius=10, fg_color=("#ffffff", "#1e1e1e"))
            self.course_chart_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=0)
            
            self.course_chart_title = ctk.CTkLabel(
                self.course_chart_frame,
                text="Attendance by Course",
                font=ctk.CTkFont(size=16, weight="bold")
            )
            self.course_chart_title.pack(anchor="w", padx=15, pady=(15, 10))
            
            # Chart placeholder
            self.course_chart_placeholder = ctk.CTkFrame(self.course_chart_frame, fg_color="transparent")
            self.course_chart_placeholder.pack(fill="both", expand=True, padx=15, pady=(5, 15))
            
            # ===== ACTIVITY FEED SECTION =====
            # Activity feed with recent attendance
            self.activity_frame = ctk.CTkFrame(self, corner_radius=12, fg_color=("#ffffff", "#1e1e1e"))
            self.activity_frame.grid(row=3, column=0, sticky="nsew", padx=20, pady=(10, 20))
            
            # Activity header with title and notification badges
            self.activity_header = ctk.CTkFrame(self.activity_frame, fg_color="transparent")
            self.activity_header.pack(fill="x", padx=15, pady=(15, 10))
            
            self.activity_title = ctk.CTkLabel(
                self.activity_header,
                text="Recent Activity",
                font=ctk.CTkFont(size=16, weight="bold")
            )
            self.activity_title.pack(side="left")
            
            self.notification_badge = ctk.CTkButton(
                self.activity_header,
                text="0 New",
                width=60,
                height=25,
                corner_radius=12,
                fg_color=("#0078D7", "#2D5F9A"),
                hover_color=("#0063B1", "#1D4F8A"),
                command=self.show_notifications
            )
            self.notification_badge.pack(side="right")
            
            # Activity list with scrollable container
            self.activity_container = ctk.CTkScrollableFrame(
                self.activity_frame,
                fg_color="transparent",
                corner_radius=0
            )
            self.activity_container.pack(fill="both", expand=True, padx=15, pady=(0, 15))
            
            # Initialize activity list
            self.activity_list = ctk.CTkFrame(self.activity_container, fg_color="transparent")
            self.activity_list.pack(fill="both", expand=True)
            
            # Empty state for activity feed
            self.activity_empty_label = ctk.CTkLabel(
                self.activity_list,
                text="No recent activity to display",
                font=ctk.CTkFont(size=14),
                text_color=("gray50", "gray70")
            )
            self.activity_empty_label.pack(pady=30)
            
            # Create example activity items for demonstration
            self._add_sample_activities()
            
            logger.info("Enhanced dashboard widgets created successfully")
            
        except Exception as e:
            logger.error(f"Error creating dashboard: {e}")
            self._create_error_message(str(e))
    
    def _create_stat_card(self, parent, title, value, subtitle, row, col):
        """Create a styled stat card"""
        card = ctk.CTkFrame(parent, corner_radius=10, fg_color=("#ffffff", "#1e1e1e"))
        card.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)
        
        # Card title
        title_label = ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(size=14),
            text_color=("gray50", "gray70")
        )
        title_label.pack(anchor="w", padx=15, pady=(15, 5))
        
        # Value with large font
        value_label = ctk.CTkLabel(
            card,
            text=value,
            font=ctk.CTkFont(size=28, weight="bold")
        )
        value_label.pack(anchor="w", padx=15, pady=(0, 5))
        
        # Subtitle (could be trend indicator)
        subtitle_label = ctk.CTkLabel(
            card,
            text=subtitle,
            font=ctk.CTkFont(size=12),
            text_color=("gray50", "gray70")
        )
        subtitle_label.pack(anchor="w", padx=15, pady=(0, 15))
        
        # Return components for later updates
        return {"card": card, "title": title_label, "value": value_label, "subtitle": subtitle_label}
    
    def _add_sample_activities(self):
        """Add sample activities for UI demonstration"""
        # Clear empty state
        self.activity_empty_label.pack_forget()
        
        # Add some sample activities
        self.add_activity_item(
            "John Smith",
            "Marked present in Computer Science class",
            "10 minutes ago"
        )
        
        self.add_activity_item(
            "Emily Johnson",
            "Marked present in Mathematics class",
            "25 minutes ago"
        )
        
        self.add_activity_item(
            "Michael Brown",
            "Marked absent in Physics class",
            "1 hour ago"
        )
    
    def add_activity_item(self, title, description, time):
        """Add an activity item to the feed"""
        # Create item container
        item = ctk.CTkFrame(self.activity_list, corner_radius=8, fg_color=("gray95", "gray25"))
        item.pack(fill="x", padx=5, pady=5)
        
        # Create grid layout for the item
        item.grid_columnconfigure(1, weight=1)
        
        # Activity icon (placeholder)
        icon_label = ctk.CTkLabel(
            item,
            text="👤",
            font=ctk.CTkFont(size=20)
        )
        icon_label.grid(row=0, column=0, rowspan=2, padx=(10, 5), pady=10)
        
        # Activity title
        title_label = ctk.CTkLabel(
            item,
            text=title,
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        )
        title_label.grid(row=0, column=1, sticky="w", padx=(5, 10), pady=(10, 0))
        
        # Activity description
        desc_label = ctk.CTkLabel(
            item,
            text=description,
            font=ctk.CTkFont(size=12),
            text_color=("gray50", "gray70"),
            anchor="w"
        )
        desc_label.grid(row=1, column=1, sticky="w", padx=(5, 10), pady=(0, 5))
        
        # Activity time
        time_label = ctk.CTkLabel(
            item,
            text=time,
            font=ctk.CTkFont(size=11),
            text_color=("gray50", "gray70")
        )
        time_label.grid(row=0, column=2, padx=(5, 10), pady=(10, 0))
        
        return item
    
    def _dummy_refresh(self):
        """Dummy refresh function for testing"""
        try:
            logger.info("Refresh button clicked")
        except Exception as e:
            logger.error(f"Error in refresh callback: {e}")
    
    def _dummy_navigation(self):
        """Dummy navigation function for testing"""
        try:
            logger.info("Navigation button clicked")
        except Exception as e:
            logger.error(f"Error in navigation callback: {e}")
    
    def load_data(self):
        """Load dashboard data asynchronously"""
        try:
            # Start a simple data loading thread that won't cause errors
            threading.Thread(target=self._simple_data_load, daemon=True).start()
            logger.info("Started simplified data loading")
        except Exception as e:
            logger.error(f"Error starting data load thread: {e}")
            
    def _simple_data_load(self):
        """Simple data loading that doesn't rely on complex UI elements"""
        try:
            # Sleep briefly to simulate data loading
            time.sleep(0.5)
            
            # Log success without updating UI elements that might not exist
            logger.info("Simulated data load complete")
        except Exception as e:
            logger.error(f"Error in simplified data load: {e}")
        
    def _on_period_change(self, value):
        """Handle period change in chart"""
        self.time_period = value
        logger.info(f"Changed time period to: {value}")
        # Would update charts here in a real implementation

    def show_notifications(self):
        """Show notifications popup"""
        logger.info("Show notifications clicked")
        # Would display notifications in a real implementation

    def _create_error_message(self, error_message):
        """Create a simple error message when widget creation fails"""
        try:
            # Clear all existing widgets if possible
            for widget in self.winfo_children():
                widget.destroy()
                
            # Create a centered error message
            self.error_frame = ctk.CTkFrame(self, fg_color=("gray95", "gray17"))
            self.error_frame.pack(fill="both", expand=True, padx=20, pady=20)
            
            error_label = ctk.CTkLabel(
                self.error_frame,
                text="Dashboard Error",
                font=ctk.CTkFont(size=20, weight="bold")
            )
            error_label.pack(pady=(100, 10))
            
            message_label = ctk.CTkLabel(
                self.error_frame,
                text=f"An error occurred while loading the dashboard:\n\n{error_message}",
                font=ctk.CTkFont(size=14),
                wraplength=500
            )
            message_label.pack(pady=10)
            
            # Add a retry button
            retry_button = ctk.CTkButton(
                self.error_frame,
                text="Retry",
                font=ctk.CTkFont(size=14),
                width=100,
                command=self._retry_dashboard_load
            )
            retry_button.pack(pady=20)
            
            logger.info("Created error message display")
        except Exception as e:
            logger.error(f"Error creating error message: {e}")
    
    def _retry_dashboard_load(self):
        """Retry loading the dashboard"""
        try:
            # Remove error frame
            if hasattr(self, 'error_frame') and self.error_frame.winfo_exists():
                self.error_frame.destroy()
                
            # Try creating widgets again
            self.create_widgets()
            logger.info("Dashboard reload attempted")
        except Exception as e:
            logger.error(f"Error retrying dashboard load: {e}")
            self._create_error_message(f"Retry failed: {str(e)}")