"""
Modern Attendance Application using CustomTkinter
"""
import os
import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox
from PIL import Image, ImageTk
import threading
import logging
import gc

from ..database.enhanced_db import EnhancedDB
from ..utils.analytics_dashboard import AttendanceAnalyticsDashboard
from ..utils.app_config import AppConfig
from .attendance_view import AttendanceView
from ..ui.dashboard_view import DashboardView

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
        
        # Load configuration
        self.config = AppConfig()
        
        # Initialize UI theme based on configuration
        ui_config = self.config.get("ui", {})
        theme = ui_config.get("theme", "system") if isinstance(ui_config, dict) else "system"
        ctk.set_appearance_mode(theme)
        
        # Configure window
        self.title(f"Face Detection Attendance System - {self.current_user.get('role', 'User').capitalize()}")
        self.geometry("1280x720")
        self.minsize(1000, 600)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
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
        self.db = EnhancedDB()
        
        # Initialize analytics dashboard
        self.analytics_dashboard = AttendanceAnalyticsDashboard(self.db)
        
        # Create main frame
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Create a 1x2 grid layout
        self.main_frame.columnconfigure(0, weight=1)  # Sidebar
        self.main_frame.columnconfigure(1, weight=5)  # Content area
        self.main_frame.rowconfigure(0, weight=1)
        
        # Create sidebar
        self.sidebar = ctk.CTkFrame(self.main_frame, corner_radius=15)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # Add user info to sidebar
        self.create_user_info()
        
        # Create sidebar buttons
        self.create_sidebar_buttons()
        
        # Create content area
        self.content_area = ctk.CTkFrame(self.main_frame, corner_radius=15)
        self.content_area.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        
        # Initialize views
        self.views = {}
        self.current_view = None
        
        # Show dashboard by default
        self.show_dashboard()
        
        # Schedule garbage collection to free memory
        if self.config.get("memory.auto_gc", True):
            self.schedule_gc()
    
    def create_user_info(self):
        """Create user info section in sidebar"""
        # User info frame
        self.user_frame = ctk.CTkFrame(self.sidebar, corner_radius=10, fg_color="transparent")
        self.user_frame.pack(fill="x", padx=10, pady=(20, 30))
        
        # User avatar
        try:
            avatar_path = os.path.join("assets", "icons", "user_avatar.png")
            if os.path.exists(avatar_path):
                avatar_image = ctk.CTkImage(
                    light_image=Image.open(avatar_path),
                    dark_image=Image.open(avatar_path),
                    size=(64, 64)
                )
                avatar_label = ctk.CTkLabel(
                    self.user_frame,
                    image=avatar_image,
                    text=""
                )
                avatar_label.pack(pady=(10, 5))
            else:
                # Use initials if no avatar
                initials = "".join([name[0].upper() for name in self.current_user.get('full_name', 'User').split() if name])
                if not initials:
                    initials = self.current_user.get('username', 'U')[0].upper()
                
                avatar_label = ctk.CTkLabel(
                    self.user_frame,
                    text=initials,
                    font=ctk.CTkFont(size=24, weight="bold"),
                    width=64,
                    height=64,
                    fg_color=("#5E81AC", "#5E81AC"),
                    text_color="white",
                    corner_radius=32
                )
                avatar_label.pack(pady=(10, 5))
        except Exception as e:
            logger.error(f"Error displaying user avatar: {e}")
        
        # User name
        name_label = ctk.CTkLabel(
            self.user_frame,
            text=self.current_user.get('full_name', self.current_user.get('username', 'User')),
            font=ctk.CTkFont(size=16, weight="bold")
        )
        name_label.pack(pady=(5, 0))
        
        # User role
        role_label = ctk.CTkLabel(
            self.user_frame,
            text=self.current_user.get('role', 'User').capitalize(),
            font=ctk.CTkFont(size=12)
        )
        role_label.pack(pady=(0, 5))
    
    def create_sidebar_buttons(self):
        """Create sidebar navigation buttons"""
        # Button container
        self.button_frame = ctk.CTkFrame(self.sidebar, corner_radius=0, fg_color="transparent")
        self.button_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Dashboard button
        self.dashboard_button = ctk.CTkButton(
            self.button_frame,
            text="Dashboard",
            command=self.show_dashboard,
            height=40,
            corner_radius=10,
            font=ctk.CTkFont(size=14)
        )
        self.dashboard_button.pack(fill="x", pady=5)
        
        # Mark Attendance button
        self.attendance_button = ctk.CTkButton(
            self.button_frame,
            text="Mark Attendance",
            command=self.mark_attendance,
            height=40,
            corner_radius=10,
            font=ctk.CTkFont(size=14)
        )
        self.attendance_button.pack(fill="x", pady=5)
        
        # Analytics button
        self.analytics_button = ctk.CTkButton(
            self.button_frame,
            text="Analytics",
            command=self.show_analytics,
            height=40,
            corner_radius=10,
            font=ctk.CTkFont(size=14)
        )
        self.analytics_button.pack(fill="x", pady=5)
        
        # Settings button
        self.settings_button = ctk.CTkButton(
            self.button_frame,
            text="Settings",
            command=self.show_settings,
            height=40,
            corner_radius=10,
            font=ctk.CTkFont(size=14)
        )
        self.settings_button.pack(fill="x", pady=5)
        
        # Add spacer
        self.spacer = ctk.CTkFrame(self.button_frame, height=20, fg_color="transparent")
        self.spacer.pack(fill="x", pady=10)
        
        # Logout button at bottom
        self.logout_frame = ctk.CTkFrame(self.sidebar, corner_radius=0, fg_color="transparent")
        self.logout_frame.pack(fill="x", side="bottom", padx=10, pady=20)
        
        self.logout_button = ctk.CTkButton(
            self.logout_frame,
            text="Logout",
            command=self.logout,
            height=40,
            corner_radius=10,
            fg_color="#E74C3C",
            hover_color="#C0392B",
            font=ctk.CTkFont(size=14)
        )
        self.logout_button.pack(fill="x")
    
    def show_dashboard(self):
        """Show the dashboard view"""
        self.clear_content_area()
        
        try:
            # Create a new dashboard view each time to avoid stale UI elements
            self.views['dashboard'] = DashboardView(self.content_area, self.auth_system, self.db)
            
            # Show view
            self.views['dashboard'].pack(fill="both", expand=True)
            self.current_view = 'dashboard'
            
            # Update button state
            self.update_button_states(selected='dashboard')
        except Exception as e:
            logger.error(f"Error showing dashboard view: {e}")
            # Fallback to a simple view if there's an error
            self._show_error_view("Dashboard", "Could not load dashboard view.")
    
    def mark_attendance(self):
        """Show the mark attendance view"""
        self.clear_content_area()
        
        try:
            # Create a new attendance view each time to avoid stale UI elements
            self.views['attendance'] = AttendanceView(self.content_area, self.auth_system)
            
            # Show view
            self.views['attendance'].pack(fill="both", expand=True)
            self.current_view = 'attendance'
            
            # Update button state
            self.update_button_states(selected='attendance')
        except Exception as e:
            logger.error(f"Error showing attendance view: {e}")
            # Fallback to a simple view if there's an error
            self._show_error_view("Attendance", "Could not load attendance tracking view.")
    
    def _show_error_view(self, title, message):
        """Show an error view when a view fails to load"""
        error_frame = ctk.CTkFrame(self.content_area)
        error_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        error_title = ctk.CTkLabel(
            error_frame,
            text=f"{title} - Error",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        error_title.pack(pady=(20, 10))
        
        error_message = ctk.CTkLabel(
            error_frame,
            text=message,
            font=ctk.CTkFont(size=16)
        )
        error_message.pack(pady=10)
        
        # Add a retry button
        retry_button = ctk.CTkButton(
            error_frame,
            text="Retry",
            command=lambda: self.show_dashboard(),
            height=40,
            corner_radius=10,
            font=ctk.CTkFont(size=14)
        )
        retry_button.pack(pady=20)
    
    def show_analytics(self):
        """Show the analytics view"""
        self.clear_content_area()
        
        # Create analytics view (recreate each time to ensure fresh data)
        analytics_label = ctk.CTkLabel(
            self.content_area,
            text="Analytics Dashboard",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        analytics_label.pack(pady=20)
        
        # Add charts and graphs here using analytics_dashboard
        
        self.current_view = 'analytics'
        
        # Update button state
        self.update_button_states(selected='analytics')
    
    def show_settings(self):
        """Show the settings dialog"""
        try:
            # Import the settings dialog
            from src.ui.settings import SettingsDialog, AppConfig
            
            # Create a new config instance if needed
            if not hasattr(self, 'app_config'):
                self.app_config = AppConfig()
                
            # Create and show the settings dialog
            settings_dialog = SettingsDialog(self, self.app_config)
            
            # Wait for the dialog to close
            self.wait_window(settings_dialog.dialog)
            
            # Apply any changes that require immediate effect
            self._apply_settings_changes()
            
            # Update button state
            self.update_button_states(selected='settings')
        except Exception as e:
            logger.error(f"Error showing settings dialog: {e}")
            messagebox.showerror("Settings", f"Error opening settings: {str(e)}")
    
    def _apply_settings_changes(self):
        """Apply settings changes that need immediate effect"""
        try:
            # Reload config in case it was updated
            if hasattr(self, 'app_config'):
                self.app_config.load_config()
                
                # Apply theme changes
                theme = self.app_config.get("theme", "system")
                ctk.set_appearance_mode(theme)
                
                # Apply window size changes if not in fullscreen
                if not self.app_config.get("ui.fullscreen", False):
                    width = self.app_config.get("ui.window_width", 1280)
                    height = self.app_config.get("ui.window_height", 720)
                    self.geometry(f"{width}x{height}")
                else:
                    # Set fullscreen
                    self.attributes('-fullscreen', True)
                    
                # Apply camera settings if attendance view is active
                if 'attendance' in self.views and hasattr(self.views['attendance'], 'update_camera_settings'):
                    camera_id = self.app_config.get("camera.id", 0)
                    resolution = self.app_config.get("camera.resolution", [640, 480])
                    fps = self.app_config.get("camera.fps", 30)
                    flip_image = self.app_config.get("camera.flip_image", False)
                    
                    # Update camera settings in the attendance view
                    self.views['attendance'].update_camera_settings(
                        camera_id=camera_id,
                        resolution=resolution,
                        fps=fps,
                        flip=flip_image
                    )
        except Exception as e:
            logger.error(f"Error applying settings changes: {e}")
            # Don't show an error message here to avoid disrupting the user experience
    
    def clear_content_area(self):
        """Clear the content area"""
        try:
            # First, try to properly clean up existing views
            if self.current_view and self.current_view in self.views:
                # Call on_close if available (cleanup resources)
                if hasattr(self.views[self.current_view], 'on_close'):
                    try:
                        self.views[self.current_view].on_close()
                    except Exception as e:
                        logger.error(f"Error closing view {self.current_view}: {e}")
                
                # Hide the view
                try:
                    self.views[self.current_view].pack_forget()
                except Exception as e:
                    logger.error(f"Error hiding view {self.current_view}: {e}")
            
            # Then destroy all child widgets to ensure a clean state
            for widget in self.content_area.winfo_children():
                try:
                    widget.destroy()
                except Exception as e:
                    logger.error(f"Error destroying widget: {e}")
        except Exception as e:
            logger.error(f"Error clearing content area: {e}")
            # Last resort - recreate the content area
            try:
                self.content_area.destroy()
                self.content_area = ctk.CTkFrame(self.main_frame, corner_radius=15)
                self.content_area.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
            except Exception as e2:
                logger.error(f"Failed to recreate content area: {e2}")
    
    def update_button_states(self, selected):
        """Update the state of sidebar buttons"""
        # Reset all buttons
        self.dashboard_button.configure(
            fg_color=("gray75", "gray25") if selected != 'dashboard' else ("#3498db", "#2980b9")
        )
        self.attendance_button.configure(
            fg_color=("gray75", "gray25") if selected != 'attendance' else ("#3498db", "#2980b9")
        )
        self.analytics_button.configure(
            fg_color=("gray75", "gray25") if selected != 'analytics' else ("#3498db", "#2980b9")
        )
        self.settings_button.configure(
            fg_color=("gray75", "gray25") if selected != 'settings' else ("#3498db", "#2980b9")
        )
    
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
        # Close active views
        if 'attendance' in self.views:
            try:
                self.views['attendance'].on_app_close()
            except Exception as e:
                logger.error(f"Error closing attendance view: {e}")
        
        # Close database connection
        if hasattr(self, 'db'):
            try:
                self.db.close()
            except Exception as e:
                logger.error(f"Error closing database connection: {e}")
    
    def schedule_gc(self):
        """Schedule periodic garbage collection"""
        # Run garbage collection
        gc.collect()
        
        # Schedule next run (every 60 seconds)
        self.after(60000, self.schedule_gc)

def main():
    """Main entry point for the modern attendance application"""
    app = ModernAttendanceApp()
    app.mainloop()

if __name__ == "__main__":
    main()