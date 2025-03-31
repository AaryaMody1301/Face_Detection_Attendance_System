"""
Modern Attendance Application using CustomTkinter
"""
import os
import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox
from PIL import Image, ImageTk, ImageDraw, ImageFont
import threading
import logging
import gc

# Import from core modules
from src.core.database.db_handler import DatabaseHandler
from src.core.utils.config_manager import ConfigManager
from .attendance_view import AttendanceView
from ..ui.dashboard_view import DashboardView
from src.ui.student_registration import StudentRegistrationView
from src.ui.training_view import TrainingView

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModernAttendanceApp(ctk.CTk):
    """
    Modern Attendance Application class using CustomTkinter
    """
    
    def __init__(self, auth_system):
        """Initialize the main application"""
        super().__init__()
        
        # Store authentication system
        self.auth_system = auth_system
        self.current_user = auth_system.get_current_user()
        
        # Track after IDs for cleanup
        self.after_ids = []
        
        # Set up theme constants
        self.button_highlight_color = "#3498db"  # Default highlight color for buttons
        
        # Load configuration
        self.config = ConfigManager()
        
        # Initialize UI theme based on configuration
        ui_config = self.config.get("ui", {})
        theme = ui_config.get("theme", "system") if isinstance(ui_config, dict) else "system"
        ctk.set_appearance_mode(theme)
        
        # Configure window
        self.title(f"Face Detection Attendance System - {self.current_user.get('role', 'User').capitalize()}")
        self.geometry("1280x720")
        self.minsize(1000, 600)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Set default font and colors for better appearance
        default_font = ctk.CTkFont(family="Segoe UI", size=12)
        ctk.set_default_color_theme("blue")  # Set a consistent color theme
        
        # Track window state
        self.is_sidebar_collapsed = False
        self.is_fullscreen = False
        self.sidebar_width = 240  # Default width
        self.sidebar_collapsed_width = 60
        
        # Load application icon safely
        try:
            icon_path = os.path.join("assets", "icons", "app_icon.png")
            if os.path.exists(icon_path):
                # Handle the icon properly for Tkinter
                self.icon_image = ctk.CTkImage(
                    light_image=Image.open(icon_path),
                    dark_image=Image.open(icon_path),
                    size=(64, 64)
                )
                # Use CTkLabel to display the icon instead of wm_iconphoto
                logger.info("Main application icon set successfully")
            else:
                logger.warning(f"Icon file not found at {icon_path}")
        except Exception as e:
            logger.warning(f"Failed to set application icon: {e}")
            # Continue without the icon rather than failing
        
        # Initialize database
        self.db = DatabaseHandler()
        
        # Track the current viewport size
        self.bind("<Configure>", self._on_window_resize)
        
        # Create UI elements
        self.create_user_interface()
        
        # Start periodic garbage collection to prevent memory leaks
        self.schedule_gc()
    
    def _on_window_resize(self, event):
        """Handle window resize events"""
        # Disable window resize handling to prevent callback exceptions
        return
        
        # Original code below - commented out
        # Don't process if width/height are zero (which can happen during initialization)
        # if event.width == 0 or event.height == 0:
        #     return
            
        # Get new dimensions
        # width, height = event.width, event.height
        
        # Store current dimensions
        # self.current_width = width
        # self.current_height = height
        
        # Adjust layout based on window size
        # self._adjust_content_layout(width, height)
        
        # Force update now rather than waiting for idle
        # self.update_idletasks()
    
    def _adjust_content_layout(self, width, height):
        """Adjust layout based on window size"""
        try:
            # Only adjust if width is valid
            if not width or width <= 0:
                return
                
            # Calculate content width
            effective_content_width = width - (self.sidebar.winfo_width() + 20)  # 20 for padding
            
            # Ensure minimum width
            if effective_content_width < 500:
                effective_content_width = 500
                
            # Update content container width
            self.content_container.configure(width=effective_content_width)
            
            # Update title bar width instead of header
            if hasattr(self, 'title_bar') and self.title_bar.winfo_exists():
                self.title_bar.configure(width=effective_content_width)
                
            logger.debug(f"Layout adjusted for window size: {width}x{height}")
        except Exception as e:
            logger.error(f"Error adjusting layout: {e}")
    
    def create_user_interface(self):
        """Create the main user interface elements"""
        # Create main frame
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Create a 1x2 grid layout
        self.main_frame.columnconfigure(0, weight=0)  # Sidebar (fixed width)
        self.main_frame.columnconfigure(1, weight=1)  # Content area (expands)
        self.main_frame.rowconfigure(0, weight=1)
        
        # Create sidebar with rounded corners and shadow effect
        self.sidebar = ctk.CTkFrame(self.main_frame, corner_radius=15, width=self.sidebar_width,
                                     fg_color=("gray90", "gray17"))
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.sidebar.grid_propagate(False)  # Prevent resizing based on content
        
        # Store images as instance variables to prevent garbage collection
        self.toggle_icon_image = self._create_hamburger_icon((20, 20))
        
        # Create toggle button for sidebar
        self.toggle_btn = ctk.CTkButton(
            self.sidebar, 
            text="", 
            width=36, 
            height=36, 
            command=self.toggle_sidebar,
            corner_radius=10,
            fg_color=("#3498db", "#2980b9"),
            hover_color=("#2980b9", "#1c6ea4"),
            image=self.toggle_icon_image
        )
        self.toggle_btn.place(x=self.sidebar_width-40, y=10)
        
        # Add a container for the sidebar content
        self.sidebar_content = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.sidebar_content.pack(fill="both", expand=True, padx=0, pady=(50, 0))
        
        # Add divider line after user info
        self.divider = ctk.CTkFrame(self.sidebar, height=2, fg_color=("gray80", "gray30"))
        
        # Add user info to sidebar
        self.create_user_info()
        
        # Add the divider after user info
        self.divider.pack(fill="x", padx=15, pady=(10, 5))
        
        # Create sidebar buttons
        self.create_sidebar_buttons()
        
        # Add version label at bottom of sidebar
        self.version_label = ctk.CTkLabel(
            self.sidebar,
            text="v2.1.0",
            font=ctk.CTkFont(size=10),
            text_color=("gray50", "gray70")
        )
        self.version_label.pack(side="bottom", pady=(0, 15))
        
        # Create content area with rounded corners and shadow effect
        self.content_area = ctk.CTkFrame(self.main_frame, corner_radius=15, 
                                         fg_color=("gray95", "gray17"))
        self.content_area.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        
        # Add title bar with window controls
        self.title_bar = ctk.CTkFrame(self.content_area, height=50, 
                                     fg_color=("gray90", "gray20"))
        self.title_bar.pack(fill="x", side="top", padx=0, pady=0)
        
        # Add title for the current view
        self.content_title = ctk.CTkLabel(
            self.title_bar,
            text="Dashboard",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.content_title.pack(side="left", padx=20, pady=10)
        
        # Add window controls
        self.window_controls = ctk.CTkFrame(self.title_bar, fg_color="transparent")
        self.window_controls.pack(side="right", padx=20, pady=10)
        
        # Fullscreen toggle
        self.fullscreen_btn = ctk.CTkButton(
            self.window_controls,
            text="",
            width=30,
            height=30,
            command=self.toggle_fullscreen,
            corner_radius=15,
            fg_color="transparent",
            hover_color=("gray80", "gray30")
        )
        self.fullscreen_btn.pack(side="right", padx=5)
        self.fullscreen_icon = self._load_icon("fullscreen.png", size=(16, 16))
        self.fullscreen_btn.configure(image=self.fullscreen_icon)
        
        # Theme toggle
        self.theme_btn = ctk.CTkButton(
            self.window_controls,
            text="",
            width=30,
            height=30,
            command=self.toggle_theme,
            corner_radius=15,
            fg_color="transparent",
            hover_color=("gray80", "gray30")
        )
        self.theme_btn.pack(side="right", padx=5)
        self.theme_icon = self._load_icon("theme.png", size=(16, 16))
        self.theme_btn.configure(image=self.theme_icon)
        
        # Create content container with extra padding
        self.content_container = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.content_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Initialize views
        self.views = {}
        self.current_view = None
        
        # Show dashboard by default
        self.show_dashboard()
    
    def toggle_sidebar(self):
        """Toggle sidebar between expanded and collapsed states"""
        # Toggle state
        self.is_sidebar_collapsed = not self.is_sidebar_collapsed
        
        # Set the new width directly without animation to avoid recursion
        new_width = 70 if self.is_sidebar_collapsed else 220
        self.sidebar.configure(width=new_width)
        
        # Update toggle button position
        self.toggle_btn.place(x=new_width-35, y=10)
        
        # Update text visibility in buttons
        for button in self.buttons:
            if hasattr(button, '_orig_text'):
                button.configure(text="" if self.is_sidebar_collapsed else button._orig_text)
        
        # Update logout button text
        if hasattr(self, 'logout_button'):
            self.logout_button.configure(text="" if self.is_sidebar_collapsed else "Logout")
        
        # Update menu label and version
        if hasattr(self, 'menu_label'):
            self.menu_label.configure(text="" if self.is_sidebar_collapsed else "MAIN MENU")
        
        if hasattr(self, 'version_label'):
            self.version_label.configure(text="" if self.is_sidebar_collapsed else "v2.1.0")
        
        # Update user info
        self.update_user_info_for_toggle()
    
    def update_user_info_for_toggle(self):
        """Update user info display based on sidebar state"""
        try:
            # Update avatar size
            avatar_size = 40 if self.is_sidebar_collapsed else 60
            self.avatar_frame.configure(width=avatar_size, height=avatar_size, corner_radius=avatar_size//2)
            
            # Update visibility of elements
            if self.is_sidebar_collapsed:
                if hasattr(self, 'username_label'):
                    self.username_label.pack_forget()
                if hasattr(self, 'role_badge'):
                    self.role_badge.pack_forget()
            else:
                if hasattr(self, 'username_label'):
                    self.username_label.pack(anchor="center")
                if hasattr(self, 'role_badge'):
                    self.role_badge.pack(anchor="center", pady=(2, 0))
        except Exception as e:
            logger.error(f"Error updating user info: {e}")
    
    def update_button_states(self, selected_button):
        """Update the visual state of buttons to indicate selection"""
        # Reset all buttons
        for button in self.buttons:
            button.configure(
                fg_color="transparent",
                font=ctk.CTkFont(size=13)
            )
        
        # Highlight selected button with a special style
        if selected_button in self.buttons:
            selected_button.configure(
                fg_color=("#3498db", "#2980b9"),
                font=ctk.CTkFont(size=13, weight="bold")
            )
        
        # Also update the logout button (always reset to default)
        if hasattr(self, 'logout_button'):
            self.logout_button.configure(
                fg_color=("gray80", "gray28"),
                text_color=("gray10", "gray90")
            )
    
    def create_user_info(self):
        """Create user info display in sidebar"""
        # Create user info container
        self.user_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.user_frame.pack(fill="x", padx=15, pady=(15, 10))
        
        # Get user info
        self.role_text = self.current_user.get('role', 'User').capitalize()
        self.username_text = self.current_user.get('username', 'Guest')
        
        try:
            # Try to create user avatar
            avatar_size = 60 if not self.is_sidebar_collapsed else 40
            
            # Create avatar placeholder
            self.avatar_frame = ctk.CTkFrame(
                self.user_frame, 
                width=avatar_size, 
                height=avatar_size, 
                corner_radius=avatar_size//2,
                fg_color=("#3498db", "#2980b9")
            )
            self.avatar_frame.pack(pady=(5, 12), anchor="center")
            self.avatar_frame.pack_propagate(False)
            
            # Get first letter of username
            first_letter = self.username_text[0].upper() if self.username_text else "G"
            
            # Add letter label
            self.avatar_label = ctk.CTkLabel(
                self.avatar_frame,
                text=first_letter,
                font=ctk.CTkFont(size=24, weight="bold"),
                text_color="white"
            )
            self.avatar_label.place(relx=0.5, rely=0.5, anchor="center")
            
        except Exception as e:
            # Handle errors
            logger.error(f"Error creating user avatar: {e}")
        
        # Add username label
        self.username_label = ctk.CTkLabel(
            self.user_frame,
            text=self.username_text,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.username_label.pack(anchor="center")
        
        # Role badge - create a pill shaped badge for role
        self.role_badge = ctk.CTkFrame(
            self.user_frame,
            corner_radius=12,
            fg_color=("#e67e22", "#d35400"),
            height=24
        )
        self.role_badge.pack(anchor="center", pady=(2, 0))
        self.role_badge.pack_propagate(False)
        
        # Role label
        self.role_label = ctk.CTkLabel(
            self.role_badge,
            text=self.role_text,
            font=ctk.CTkFont(size=11),
            text_color="white"
        )
        self.role_label.pack(padx=12, pady=(0, 1))
    
    def create_sidebar_buttons(self):
        """Create buttons in the sidebar"""
        # Create empty list for buttons
        self.buttons = []
        
        # Create a container for menu items with some padding
        self.menu_container = ctk.CTkFrame(self.sidebar_content, fg_color="transparent")
        self.menu_container.pack(fill="both", expand=True, padx=10, pady=(15, 10))
        
        # Add menu section label
        self.menu_label = ctk.CTkLabel(
            self.menu_container,
            text="MAIN MENU",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=("gray60", "gray70")
        )
        self.menu_label.pack(anchor="w", padx=10, pady=(0, 10))
        
        # Define menu items (no icons)
        menu_items = [
            {
                "text": "Dashboard",
                "command": self.show_dashboard,
                "position": 0
            },
            {
                "text": "Mark Attendance",
                "command": self.show_mark_attendance,
                "position": 1
            },
            {
                "text": "Analytics",
                "command": self.show_analytics,
                "position": 2
            },
            {
                "text": "Registration",
                "command": self.register_student,
                "position": 3
            },
            {
                "text": "Training",
                "command": self.train_model,
                "position": 4
            },
            {
                "text": "Settings",
                "command": self.show_settings,
                "position": 5
            }
        ]
        
        # Create buttons for each menu item
        for item in menu_items:
            # Store original text for toggling sidebar
            orig_text = item["text"]
            
            # Create the button with modern styling and proper padding (no icon)
            button = ctk.CTkButton(
                self.menu_container,
                text=orig_text if not self.is_sidebar_collapsed else "",
                command=item["command"],
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray80", "gray28"),
                anchor="w",
                height=42,
                corner_radius=8,
                border_spacing=10,
                font=ctk.CTkFont(size=13)
            )
            # Store original text as an attribute
            button._orig_text = orig_text
            
            button.pack(fill="x", pady=(0, 5))
            self.buttons.append(button)
        
        # Add a separator before the logout button
        self.separator = ctk.CTkFrame(self.menu_container, height=1, fg_color=("gray80", "gray30"))
        self.separator.pack(fill="x", padx=10, pady=(15, 15))
        
        # Add logout button at the bottom (no icon)
        self.logout_button = ctk.CTkButton(
            self.menu_container,
            text="Logout" if not self.is_sidebar_collapsed else "",
            command=self.logout,
            fg_color=("gray80", "gray28"),
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray35"),
            anchor="w",
            height=42,
            corner_radius=8,
            border_spacing=10,
            font=ctk.CTkFont(size=13)
        )
        self.logout_button.pack(fill="x", pady=(0, 5))
        
        # Set initial selection
        self.update_button_states(self.buttons[0])
    
    def _load_icon(self, icon_name, size=(24, 24)):
        """Load an icon from the assets folder"""
        try:
            # Try multiple paths to find the icon
            possible_paths = [
                # Absolute path based on module location
                os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "icons", icon_name),
                # Relative path from working directory
                os.path.join("assets", "icons", icon_name),
                # Just the filename in the icons directory
                os.path.join("icons", icon_name),
            ]
            
            # Try each path
            for icon_path in possible_paths:
                if os.path.isfile(icon_path):
                    img = Image.open(icon_path)
                    ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=size)
                    return ctk_img
            
            # If no icon found, create a placeholder
            logger.warning(f"Icon not found: {icon_name}")
            return self._create_placeholder_icon(icon_name, size)
                
        except Exception as e:
            logger.warning(f"Failed to load icon {icon_name}: {e}")
            return self._create_placeholder_icon(icon_name, size)
            
    def _create_placeholder_icon(self, icon_name, size=(24, 24)):
        """Create a placeholder for missing icons"""
        # Create blank image
        img = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Determine color based on appearance mode
        is_dark = ctk.get_appearance_mode().lower() == "dark"
        
        # Choose color based on icon name to create visual variety
        colors = {
            "home": "#3498db",     # Blue
            "check": "#2ecc71",    # Green
            "analytics": "#9b59b6", # Purple
            "user": "#e67e22",     # Orange
            "train": "#f1c40f",    # Yellow
            "settings": "#34495e", # Dark blue
            "logout": "#e74c3c",   # Red
            "fullscreen": "#1abc9c", # Teal
            "theme": "#8e44ad",    # Violet
            "bell": "#3498db",     # Blue
            "error": "#e74c3c",    # Red
        }
        
        # Get base name without extension and use it to determine color
        base_name = os.path.splitext(icon_name)[0]
        color = colors.get(base_name, "#7f8c8d")  # Default to gray if not found
        
        # Draw rounded rectangle for better appearance
        padding = 2
        radius = size[0] // 5  # Rounded corners
        draw.rounded_rectangle([padding, padding, size[0]-padding, size[1]-padding], 
                              radius=radius, fill=color)
        
        # Get first letter of icon name (without extension)
        icon_letter = base_name[0].upper() if base_name else "?"
        
        # Try to use a specific font, fall back to default
        try:
            font = ImageFont.truetype("arial.ttf", size[0]//3)
        except IOError:
            font = ImageFont.load_default()
            
        # Calculate text position to center it
        text_bbox = draw.textbbox((0, 0), icon_letter, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        position = ((size[0] - text_width) // 2, (size[1] - text_height) // 2)
        
        # Draw the letter in white
        draw.text(position, icon_letter, fill="white", font=font)
        
        return ctk.CTkImage(light_image=img, dark_image=img, size=size)
    
    def show_dashboard(self):
        """Show the dashboard view"""
        self.content_title.configure(text="Dashboard")
        
        # Reuse existing view if available
        if "dashboard" in self.views and self.views["dashboard"].winfo_exists():
            self.clear_content_area()
            self.views["dashboard"].pack(fill="both", expand=True)
            self.current_view = "dashboard"
            self.update_button_states(self.buttons[0] if self.buttons else None)
            return
        
        # Create new dashboard view
        try:
            self.clear_content_area()
            dashboard = DashboardView(self.content_container, self.auth_system, self.db)
            dashboard.pack(fill="both", expand=True)
            
            # Save reference
            self.views["dashboard"] = dashboard
            self.current_view = "dashboard"
            self.update_button_states(self.buttons[0] if self.buttons else None)
            
        except Exception as e:
            logger.error(f"Error showing dashboard: {e}")
            self._show_error_view("Dashboard Error", str(e))
    
    def show_mark_attendance(self):
        """Show the attendance view"""
        self.content_title.configure(text="Mark Attendance")
        
        # Check if the view already exists and use it
        if "attendance" in self.views and self.views["attendance"].winfo_exists():
            self.clear_content_area()
            self.views["attendance"].pack(fill="both", expand=True)
            self.current_view = "attendance"
            self.update_button_states(self.buttons[1] if len(self.buttons) > 1 else None)
            return
        
        # Create new attendance view
        try:
            # Clear the content area first
            self.clear_content_area()
            
            from .attendance_view import AttendanceView
            attendance_view = AttendanceView(self.content_container, config=self.config)
            attendance_view.pack(fill="both", expand=True)
            
            # Save reference
            self.views["attendance"] = attendance_view
            self.current_view = "attendance"
            self.update_button_states(self.buttons[1] if len(self.buttons) > 1 else None)
            
        except Exception as e:
            logger.error(f"Error showing attendance view: {e}")
            self._show_error_view("Attendance View Error", str(e))
    
    def _show_error_view(self, title, message):
        """Show error view when a component fails to load"""
        self.clear_content_area()
        
        # Create error frame
        error_frame = ctk.CTkFrame(self.content_container)
        error_frame.pack(fill="both", expand=True)
        
        # Configure layout
        error_frame.grid_rowconfigure(0, weight=1)
        error_frame.grid_rowconfigure(1, weight=0)
        error_frame.grid_rowconfigure(2, weight=1)
        error_frame.grid_columnconfigure(0, weight=1)
        
        # Error icon
        try:
            icon_path = os.path.join("assets", "icons", "error.png")
            if os.path.exists(icon_path):
                error_icon = ctk.CTkImage(
                    light_image=Image.open(icon_path),
                    dark_image=Image.open(icon_path),
                    size=(64, 64)
                )
                icon_label = ctk.CTkLabel(error_frame, image=error_icon, text="")
                icon_label.grid(row=0, column=0, pady=(20, 0))
        except Exception:
            pass
        
        # Error title
        title_label = ctk.CTkLabel(
            error_frame,
            text=title,
            font=ctk.CTkFont(size=22, weight="bold")
        )
        title_label.grid(row=1, column=0, pady=(20, 10))
        
        # Error message
        msg_label = ctk.CTkLabel(
            error_frame,
            text=message,
            font=ctk.CTkFont(size=14),
            wraplength=500
        )
        msg_label.grid(row=2, column=0, pady=(0, 20))
    
    def show_analytics(self):
        """Show the analytics view"""
        from src.ui.analytics_dashboard import AnalyticsDashboard
        
        self.content_title.configure(text="Analytics")
        
        # Reuse existing view if available
        if "analytics" in self.views and self.views["analytics"].winfo_exists():
            self.clear_content_area()
            self.views["analytics"].pack(fill="both", expand=True)
            self.current_view = "analytics"
            self.update_button_states(self.buttons[2] if self.buttons else None)
            return
        
        # Create new analytics view
        try:
            self.clear_content_area()
            analytics_view = AnalyticsDashboard(self.content_container, db_handler=self.db)
            analytics_view.pack(fill="both", expand=True)
            
            # Save reference
            self.views["analytics"] = analytics_view
            self.current_view = "analytics"
            self.update_button_states(self.buttons[2] if self.buttons else None)
            
        except Exception as e:
            logger.error(f"Error showing analytics: {e}")
            self._show_error_view("Analytics Error", str(e))
    
    def show_settings(self):
        """Show the settings view"""
        from src.ui.settings import SettingsPage
        
        self.content_title.configure(text="Settings")
        
        # Reuse existing view if available
        if "settings" in self.views and self.views["settings"].winfo_exists():
            self.clear_content_area()
            self.views["settings"].pack(fill="both", expand=True)
            self.current_view = "settings"
            self.update_button_states(self.buttons[5] if self.buttons else None)
            return
        
        # Create new settings view
        try:
            self.clear_content_area()
            settings_view = SettingsPage(self.content_container)
            settings_view.pack(fill="both", expand=True)
            
            # Save reference
            self.views["settings"] = settings_view
            self.current_view = "settings"
            self.update_button_states(self.buttons[5] if self.buttons else None)
            
        except Exception as e:
            logger.error(f"Error showing settings: {e}")
            self._show_error_view("Settings Error", str(e))
    
    def clear_content_area(self):
        """Clear the content area but don't destroy views"""
        # Hide all views (preserving them for reuse)
        for view_name, view in self.views.items():
            if view.winfo_exists():
                view.pack_forget()
    
    def logout(self):
        """Logout the current user"""
        # Ask for confirmation
        result = messagebox.askyesno("Logout", "Are you sure you want to logout?")
        if not result:
            return
            
        # Clean up resources
        try:
            self.cleanup_resources()
        except Exception as e:
            logger.error(f"Error during resource cleanup: {e}")
        
        # Logout the current user
        if self.auth_system:
            self.auth_system.logout()
        
        # Show message before closing
        messagebox.showinfo("Logged Out", "You have been logged out successfully. Please restart the application to log in again.")
        
        # Destroy the window and exit
        self.destroy()
        
        # Exit the application cleanly
        import sys
        sys.exit(0)
    
    def on_closing(self):
        """Handle application close event"""
        try:
            # Clean up resources
            self.cleanup_resources()
            
            # Log out the user
            if hasattr(self, 'auth_system') and self.auth_system:
                try:
                    self.auth_system.logout()
                except Exception as e:
                    logger.error(f"Error during logout: {e}")
            
            # Destroy all widgets
            for widget in self.winfo_children():
                try:
                    if widget.winfo_exists():
                        widget.destroy()
                except Exception:
                    pass
            
            # Destroy the root window
            self.destroy()
            
            # Force cleanup
            gc.collect()
            
            logger.info("Application closed normally")
        except Exception as e:
            logger.error(f"Error during application close: {e}")
            # Just destroy the window
            self.destroy()
    
    def cleanup_resources(self):
        """Clean up resources before closing"""
        try:
            # Cancel all scheduled after callbacks
            if hasattr(self, 'after_ids') and self.after_ids:
                logger.info(f"Starting cleanup with {len(self.after_ids)} after callbacks")
                
                # Cancel all scheduled after callbacks
                for after_id in list(self.after_ids):
                    try:
                        self.after_cancel(after_id)
                    except Exception as e:
                        logger.error(f"Error canceling after ID {after_id}: {e}")
                # Clear the list
                self.after_ids = []
            else:
                logger.info("No after callbacks to clean up")
            
            # Clean up views
            if hasattr(self, 'views'):
                for view_name, view in list(self.views.items()):
                    if view and hasattr(view, 'cleanup') and callable(view.cleanup):
                        try:
                            view.cleanup()
                        except Exception as e:
                            logger.error(f"Error cleaning up view {view_name}: {e}")
                
                # Explicitly destroy views to prevent invalid command errors
                for view_name in list(self.views.keys()):
                    if view_name in self.views and self.views[view_name] and hasattr(self.views[view_name], 'winfo_exists'):
                        try:
                            if self.views[view_name].winfo_exists():
                                self.views[view_name].destroy()
                        except Exception as e:
                            logger.error(f"Error destroying view {view_name}: {e}")
                
                # Clear views dictionary
                self.views.clear()
            
            # Force garbage collection
            gc.collect()
            
            logger.info("Application resources cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            # Continue with the logout process regardless of cleanup errors
    
    def schedule_gc(self):
        """Schedule periodic garbage collection"""
        gc.collect()
        # Schedule next collection after 5 minutes if app still exists
        if self.winfo_exists():
            self.after(300000, self.schedule_gc)
    
    def register_student(self):
        """Show the student registration view"""
        self.content_title.configure(text="Student Registration")
        
        # Reuse existing view if available
        if "registration" in self.views and self.views["registration"].winfo_exists():
            self.clear_content_area()
            self.views["registration"].pack(fill="both", expand=True)
            self.current_view = "registration"
            self.update_button_states(self.buttons[3] if self.buttons else None)
            return
        
        # Create new registration view
        try:
            self.clear_content_area()
            
            # Create registration view
            registration_view = StudentRegistrationView(self.content_container)
            registration_view.pack(fill="both", expand=True)
            
            # Save reference
            self.views["registration"] = registration_view
            self.current_view = "registration"
            self.update_button_states(self.buttons[3] if self.buttons else None)
            
        except Exception as e:
            logger.error(f"Error showing student registration: {e}")
            self._show_error_view("Registration Error", str(e))
    
    def train_model(self):
        """Show the training view"""
        self.content_title.configure(text="Train Recognition Model")
        
        # Reuse existing view if available
        if "training" in self.views and self.views["training"].winfo_exists():
            self.clear_content_area()
            self.views["training"].pack(fill="both", expand=True)
            self.current_view = "training"
            self.update_button_states(self.buttons[4] if self.buttons else None)
            return
        
        # Create new training view
        try:
            self.clear_content_area()
            
            # Create training view
            training_view = TrainingView(self.content_container)
            training_view.pack(fill="both", expand=True)
            
            # Save reference
            self.views["training"] = training_view
            self.current_view = "training"
            self.update_button_states(self.buttons[4] if self.buttons else None)
            
        except Exception as e:
            logger.error(f"Error showing training view: {e}")
            self._show_error_view("Training Error", str(e))
    
    def show_error_view(self, error_message):
        """Show error view in content area"""
        # Clear current content
        self.clear_content_area()
        
        # Create error container
        error_container = ctk.CTkFrame(self.content_container)
        error_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Configure grid layout
        error_container.grid_rowconfigure(0, weight=0)
        error_container.grid_rowconfigure(1, weight=0)
        error_container.grid_rowconfigure(2, weight=1)
        error_container.grid_columnconfigure(0, weight=1)
        
        # Error icon
        try:
            error_icon_path = os.path.join("assets", "icons", "error.png")
            if os.path.exists(error_icon_path):
                error_icon = ctk.CTkImage(
                    light_image=Image.open(error_icon_path),
                    dark_image=Image.open(error_icon_path),
                    size=(64, 64)
                )
                icon_label = ctk.CTkLabel(error_container, image=error_icon, text="")
                icon_label.grid(row=0, column=0, pady=(30, 10))
        except Exception as e:
            logger.warning(f"Failed to load error icon: {e}")
        
        # Error title
        title_label = ctk.CTkLabel(
            error_container,
            text="An Error Occurred",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.grid(row=1, column=0, pady=(10, 20))
        
        # Error message
        message_label = ctk.CTkLabel(
            error_container,
            text=error_message,
            font=ctk.CTkFont(size=16),
            wraplength=500
        )
        message_label.grid(row=2, column=0, pady=(0, 30))

    def after(self, ms, func=None, *args):
        """Override after to track IDs for cleanup"""
        if func is not None:
            # Make sure after_ids exists
            if not hasattr(self, 'after_ids'):
                self.after_ids = []
                
            # Create a wrapper that removes the after_id from our list when it's done
            def wrapper(*wargs):
                try:
                    # Call the original function
                    if func:
                        result = func(*wargs)
                    else:
                        result = None
                        
                    # Return the result
                    return result
                except Exception as e:
                    logger.error(f"Error in after callback: {e}")
                finally:
                    # Remove from our tracking list when done
                    if after_id in self.after_ids:
                        self.after_ids.remove(after_id)
                    
            # Call parent's after method with our wrapper
            after_id = super().after(ms, wrapper, *args)
            self.after_ids.append(after_id)
            return after_id
        return super().after(ms)

    def _create_hamburger_icon(self, size=(20, 20)):
        """Create a hamburger menu icon for the sidebar toggle with better design"""
        # Create a blank PIL image
        img = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Get dimensions
        width, height = size
        
        # Use white color regardless of mode to contrast with button background
        line_color = "white"
        
        # Draw three lines for hamburger menu - more refined
        line_width = max(1, height // 10)
        line_length = width - 6
        y_offset = (height - (3 * line_width + 4)) // 2
        
        # Draw each line with rounded edges
        for i in range(3):
            y = y_offset + i * (line_width + 2)
            draw.rounded_rectangle(
                [(3, y), (3 + line_length, y + line_width)],
                radius=line_width//2,
                fill=line_color
            )
        
        # Convert to CTkImage
        return ctk.CTkImage(light_image=img, dark_image=img, size=size)
    
    def toggle_fullscreen(self):
        """Toggle fullscreen mode"""
        self.is_fullscreen = not self.is_fullscreen
        self.attributes("-fullscreen", self.is_fullscreen)
        
        # Update button icon based on state
        icon_name = "exit_fullscreen" if self.is_fullscreen else "fullscreen"
        icon = self._load_icon(icon_name, size=(16, 16))
        if icon:
            self.fullscreen_btn.configure(image=icon)

    def toggle_theme(self):
        """Toggle between light and dark theme"""
        current_theme = ctk.get_appearance_mode()
        new_theme = "Dark" if current_theme == "Light" else "Light"
        ctk.set_appearance_mode(new_theme)
        
        # Save theme preference
        self.config.set("ui.theme", new_theme.lower())
        
        # Update button icon based on state
        icon_name = "light_mode" if new_theme == "Dark" else "dark_mode"
        icon = self._load_icon(icon_name, size=(16, 16))
        if icon:
            self.theme_btn.configure(image=icon)

def main():
    """Main function to launch the modern UI"""
    try:
        # Import the authentication module
        from src.auth.simple_auth import SimpleAuth
        
        # Initialize authentication system
        auth_system = SimpleAuth()
        
        # If not logged in, show login screen first
        if not auth_system.is_authenticated():
            from src.ui.login_window import LoginWindow
            login_window = LoginWindow()
            login_window.mainloop()
            
            # Check if login was successful
            if not auth_system.is_authenticated():
                return
        
        # Create and start the main application
        app = ModernAttendanceApp(auth_system)
        app.mainloop()
        
    except Exception as e:
        logging.error(f"Error in ModernUI launcher: {e}")
        traceback.print_exc()
        
        # Show error dialog
        messagebox.showerror("Startup Error", 
                            f"Failed to start the application: {str(e)}\n\n"
                            "Please check the logs for more information.")
        
if __name__ == "__main__":
    main()