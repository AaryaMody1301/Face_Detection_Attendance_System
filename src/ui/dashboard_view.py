"""
Dashboard view for the attendance system
"""
import os
import tkinter as tk
import customtkinter as ctk
import datetime
import logging
import threading
from PIL import Image, ImageTk

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
        
        # Create UI elements
        self.create_widgets()
        
        # Load data
        self.load_data()
    
    def create_widgets(self):
        """Create UI widgets for the dashboard view"""
        # Main layout
        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_rowconfigure(0, weight=0)  # Header
        self.grid_rowconfigure(1, weight=1)  # Content
        
        # Header
        self.header_frame = ctk.CTkFrame(self)
        self.header_frame.grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 10), sticky="ew")
        
        # Configure header layout
        self.header_frame.grid_columnconfigure(0, weight=1)
        
        # Welcome message
        welcome_text = f"Welcome, {self.current_user.get('full_name', self.current_user.get('username', 'User'))}!"
        welcome_label = ctk.CTkLabel(
            self.header_frame,
            text=welcome_text,
            font=ctk.CTkFont(size=22, weight="bold")
        )
        welcome_label.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        
        # Date
        date_text = f"Today: {datetime.datetime.now().strftime('%A, %d %B %Y')}"
        date_label = ctk.CTkLabel(
            self.header_frame,
            text=date_text,
            font=ctk.CTkFont(size=14)
        )
        date_label.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="w")
        
        # Stats cards container
        self.stats_frame = ctk.CTkFrame(self)
        self.stats_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        
        # Configure stats frame layout
        self.stats_frame.grid_columnconfigure((0, 1), weight=1)
        self.stats_frame.grid_rowconfigure((0, 1), weight=1)
        
        # Create stats cards
        self.create_stats_cards()
        
        # Activity feed
        self.activity_frame = ctk.CTkFrame(self)
        self.activity_frame.grid(row=1, column=1, padx=20, pady=10, sticky="nsew")
        
        # Configure activity frame layout
        self.activity_frame.grid_columnconfigure(0, weight=1)
        self.activity_frame.grid_rowconfigure(0, weight=0)  # Title
        self.activity_frame.grid_rowconfigure(1, weight=1)  # Content
        
        # Activity title
        activity_title = ctk.CTkLabel(
            self.activity_frame,
            text="Recent Activity",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        activity_title.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        # Activity list
        self.activity_list = ctk.CTkScrollableFrame(self.activity_frame)
        self.activity_list.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        
        # Configure activity list layout
        self.activity_list.grid_columnconfigure(0, weight=1)
    
    def create_stats_cards(self):
        """Create statistics cards for the dashboard"""
        # Card 1: Total Attendance
        self.total_attendance_card = self.create_stat_card(
            self.stats_frame, 
            "Total Attendance", 
            "Loading...",
            "Last 30 days",
            row=0, 
            column=0
        )
        
        # Card 2: Unique Students
        self.unique_students_card = self.create_stat_card(
            self.stats_frame, 
            "Unique Students", 
            "Loading...",
            "Last 30 days",
            row=0, 
            column=1
        )
        
        # Card 3: Today's Attendance
        self.today_attendance_card = self.create_stat_card(
            self.stats_frame, 
            "Today's Attendance", 
            "Loading...",
            f"{datetime.datetime.now().strftime('%d %b %Y')}",
            row=1, 
            column=0
        )
        
        # Card 4: Avg. Daily Attendance
        self.avg_attendance_card = self.create_stat_card(
            self.stats_frame, 
            "Avg. Daily Attendance", 
            "Loading...",
            "Last 30 days",
            row=1, 
            column=1
        )
    
    def create_stat_card(self, parent, title, value, subtitle, row, column):
        """Create a statistics card"""
        card = ctk.CTkFrame(parent, corner_radius=10)
        card.grid(row=row, column=column, padx=10, pady=10, sticky="nsew")
        
        # Configure card layout
        card.grid_columnconfigure(0, weight=1)
        
        # Title
        title_label = ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        
        # Value
        value_label = ctk.CTkLabel(
            card,
            text=value,
            font=ctk.CTkFont(size=28, weight="bold")
        )
        value_label.grid(row=1, column=0, padx=20, pady=(5, 5), sticky="w")
        
        # Subtitle
        subtitle_label = ctk.CTkLabel(
            card,
            text=subtitle,
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        subtitle_label.grid(row=2, column=0, padx=20, pady=(5, 20), sticky="w")
        
        return {
            "card": card,
            "title": title_label,
            "value": value_label,
            "subtitle": subtitle_label
        }
    
    def add_activity_item(self, title, description, time_str):
        """Add an item to the activity feed"""
        item_frame = ctk.CTkFrame(self.activity_list, corner_radius=5, fg_color="transparent")
        item_frame.pack(fill="x", padx=5, pady=5)
        
        # Configure item layout
        item_frame.grid_columnconfigure(1, weight=1)
        
        # Time indicator
        time_label = ctk.CTkLabel(
            item_frame,
            text=time_str,
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        time_label.grid(row=0, column=0, padx=(5, 10), pady=(5, 0), sticky="ne")
        
        # Activity dot
        dot_frame = ctk.CTkFrame(item_frame, width=10, height=10, corner_radius=5, fg_color="#3498db")
        dot_frame.grid(row=1, column=0, padx=(5, 10), pady=5)
        
        # Title
        title_label = ctk.CTkLabel(
            item_frame,
            text=title,
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        )
        title_label.grid(row=0, column=1, padx=5, pady=(5, 0), sticky="w")
        
        # Description
        desc_label = ctk.CTkLabel(
            item_frame,
            text=description,
            font=ctk.CTkFont(size=12),
            anchor="w",
            justify="left"
        )
        desc_label.grid(row=1, column=1, padx=5, pady=(0, 5), sticky="w")
        
        # Separator
        separator = ctk.CTkFrame(item_frame, height=1, fg_color="gray")
        separator.grid(row=2, column=0, columnspan=2, padx=5, pady=(0, 5), sticky="ew")
    
    def load_data(self):
        """Load dashboard data in a separate thread"""
        loading_thread = threading.Thread(target=self._load_data_task, daemon=True)
        loading_thread.start()
    
    def _load_data_task(self):
        """Background task to load dashboard data"""
        try:
            # Get attendance overview
            overview = self.db.get_attendance_statistics()
            
            # Get today's attendance
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            today_count = overview.get("attendance_by_date", {}).get(today, 0)
            
            # Calculate average daily attendance
            attendance_by_date = overview.get("attendance_by_date", {})
            days_with_attendance = len(attendance_by_date)
            avg_attendance = overview.get("total_attendance", 0) / max(1, days_with_attendance)
            
            # Update UI in main thread
            self.after(0, lambda: self._update_stats(
                total=overview.get("total_attendance", 0),
                unique=overview.get("unique_students", 0),
                today=today_count,
                average=avg_attendance
            ))
            
            # Get recent attendance records for activity feed
            records = self.db.get_attendance_records()
            
            # Limit to 20 most recent records
            recent_records = records[:20] if records else []
            
            # Update activity feed in main thread
            self.after(0, lambda: self._update_activity_feed(recent_records))
            
        except Exception as e:
            logger.error(f"Error loading dashboard data: {e}")
            # Update UI with error message
            self.after(0, lambda: self._update_stats_error())
    
    def _update_stats(self, total, unique, today, average):
        """Update statistics on the dashboard"""
        self.total_attendance_card["value"].configure(text=str(total))
        self.unique_students_card["value"].configure(text=str(unique))
        self.today_attendance_card["value"].configure(text=str(today))
        self.avg_attendance_card["value"].configure(text=f"{average:.1f}")
    
    def _update_stats_error(self):
        """Update statistics with error message"""
        self.total_attendance_card["value"].configure(text="Error")
        self.unique_students_card["value"].configure(text="Error")
        self.today_attendance_card["value"].configure(text="Error")
        self.avg_attendance_card["value"].configure(text="Error")
    
    def _update_activity_feed(self, records):
        """Update activity feed with attendance records"""
        # Clear existing items
        for widget in self.activity_list.winfo_children():
            widget.destroy()
        
        if not records:
            # No records, show message
            no_data_label = ctk.CTkLabel(
                self.activity_list,
                text="No recent activity",
                font=ctk.CTkFont(size=14),
                text_color="gray"
            )
            no_data_label.pack(pady=20)
            return
        
        # Group records by date
        date_groups = {}
        for record in records:
            date = record.get("date", "Unknown")
            if date not in date_groups:
                date_groups[date] = []
            date_groups[date].append(record)
        
        # Add record groups to activity feed
        for date, group in sorted(date_groups.items(), reverse=True):
            # Format date
            try:
                date_obj = datetime.datetime.strptime(date, "%Y-%m-%d")
                date_str = date_obj.strftime("%d %B %Y")
            except:
                date_str = date
            
            # Date header
            date_header = ctk.CTkLabel(
                self.activity_list,
                text=date_str,
                font=ctk.CTkFont(size=16, weight="bold")
            )
            date_header.pack(fill="x", padx=5, pady=(15, 5), anchor="w")
            
            # Add activities for this date
            for record in group:
                name = record.get("name", "Unknown")
                subject = record.get("subject", "Unknown")
                time = record.get("time", "00:00:00")
                
                title = f"{name} - {subject}"
                description = f"Attendance marked for {subject}"
                
                self.add_activity_item(title, description, time)