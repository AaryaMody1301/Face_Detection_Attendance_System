"""
Login Screen for the Face Detection Attendance System

This module provides a login screen for user authentication.
"""
import os
import tkinter as tk
from tkinter import ttk, messagebox
import logging
from PIL import Image, ImageTk
from pathlib import Path
import customtkinter as ctk

from ..utils.exceptions import AuthenticationError
from ..auth.auth_system import AuthSystem

# Configure logger
logger = logging.getLogger(__name__)

class LoginScreen:
    """
    Login screen for user authentication
    
    Attributes:
        root: Root Tkinter window
        auth_system: Authentication system instance
        login_successful: Whether login was successful
    """
    
    def __init__(self, root, auth_system: AuthSystem):
        """
        Initialize login screen
        
        Args:
            root: Root Tkinter window
            auth_system: Authentication system instance
        """
        self.root = root
        self.auth_system = auth_system
        self.login_successful = False
        
        # Set theme
        ctk.set_appearance_mode("system")  # Use system theme
        ctk.set_default_color_theme("blue")  # Default theme color
        
        # Create login window
        self._create_login_window()
        
        # Fill login form with credentials if in development mode
        self._auto_fill_credentials()
    
    def _create_login_window(self):
        """Create the login window UI"""
        # Configure root window
        self.root.title("Login - Face Detection Attendance System")
        self.root.geometry("400x520")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Set window icon if available
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                               "assets", "icons", "app_icon.png")
        if os.path.exists(icon_path):
            try:
                icon = ImageTk.PhotoImage(file=icon_path)
                self.root.iconphoto(True, icon)
            except Exception as e:
                logger.warning(f"Failed to set window icon: {e}")
        
        # Create main frame
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # App logo
        self._load_logo()
        
        # Title
        title_label = ctk.CTkLabel(self.main_frame, text="Face Detection\nAttendance System", 
                                font=ctk.CTkFont(size=24, weight="bold"))
        title_label.pack(pady=(10, 20))
        
        # Login frame
        login_frame = ctk.CTkFrame(self.main_frame)
        login_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Login title
        login_label = ctk.CTkLabel(login_frame, text="User Login", 
                                font=ctk.CTkFont(size=18, weight="bold"))
        login_label.pack(pady=(15, 20))
        
        # Username
        username_label = ctk.CTkLabel(login_frame, text="Username:", 
                                    font=ctk.CTkFont(size=14))
        username_label.pack(anchor="w", padx=25, pady=(10, 0))
        
        self.username_entry = ctk.CTkEntry(login_frame, width=300)
        self.username_entry.pack(padx=25, pady=(5, 10))
        
        # Password
        password_label = ctk.CTkLabel(login_frame, text="Password:", 
                                    font=ctk.CTkFont(size=14))
        password_label.pack(anchor="w", padx=25, pady=(10, 0))
        
        self.password_entry = ctk.CTkEntry(login_frame, width=300, show="●")
        self.password_entry.pack(padx=25, pady=(5, 10))
        
        # Remember me
        remember_frame = ctk.CTkFrame(login_frame, fg_color="transparent")
        remember_frame.pack(fill="x", padx=25, pady=(5, 15))
        
        self.remember_var = tk.BooleanVar(value=False)
        remember_checkbox = ctk.CTkCheckBox(remember_frame, text="Remember me", 
                                          variable=self.remember_var)
        remember_checkbox.pack(side="left")
        
        # Forgot password
        forgot_button = ctk.CTkButton(remember_frame, text="Forgot Password?", 
                                    fg_color="transparent", text_color=["#1f538d", "#3a8ddc"], 
                                    hover=False, width=50, command=self._show_forgot_password)
        forgot_button.pack(side="right")
        
        # Login button
        self.login_button = ctk.CTkButton(login_frame, text="Login", 
                                       font=ctk.CTkFont(size=15, weight="bold"), 
                                       height=40, command=self._login)
        self.login_button.pack(padx=25, pady=(15, 0))
        
        # Skip login button (if not required)
        if not self.auth_system.require_login:
            skip_button = ctk.CTkButton(login_frame, text="Continue as Guest", 
                                     font=ctk.CTkFont(size=12), 
                                     fg_color="transparent", 
                                     text_color=["#1f538d", "#3a8ddc"],
                                     hover_color=["#e6e6e6", "#3a3a3a"],
                                     height=30, command=self._skip_login)
            skip_button.pack(padx=25, pady=(5, 0))
        
        # Status message
        self.status_label = ctk.CTkLabel(login_frame, text="", text_color="red")
        self.status_label.pack(pady=(15, 10))
        
        # Footer
        footer_label = ctk.CTkLabel(self.main_frame, text="© Face Detection Attendance System", 
                                  font=ctk.CTkFont(size=10))
        footer_label.pack(pady=(5, 0))
        
        # Bind Enter key to login
        self.root.bind("<Return>", lambda event: self._login())
        
        # Set focus on username entry
        self.username_entry.focus()
        
        # Show window
        self.root.deiconify()  # Make window visible
    
    def _load_logo(self):
        """Load and display app logo"""
        logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                             "assets", "icons", "app_icon.png")
        
        if os.path.exists(logo_path):
            try:
                # Load and resize logo image
                logo = Image.open(logo_path).resize((80, 80))
                logo_photo = ImageTk.PhotoImage(logo)
                
                # Create label to display logo
                logo_label = tk.Label(self.main_frame, image=logo_photo, bg="#ebebeb")
                logo_label.image = logo_photo  # Keep a reference to prevent garbage collection
                logo_label.pack(pady=(0, 0))
            except Exception as e:
                logger.warning(f"Failed to load logo: {e}")
    
    def _login(self):
        """Handle the login button click"""
        # Get username and password
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        
        # Validate input
        if not username or not password:
            self.status_label.configure(text="Please enter both username and password")
            return
            
        # Disable login button and show loading state
        self.login_button.configure(state="disabled", text="Logging in...")
        self.status_label.configure(text="")
        self.root.update()
        
        try:
            # Attempt to login
            success = self.auth_system.login(username, password)
            
            if success:
                # Login successful
                self.login_successful = True
                self.root.destroy()
            else:
                # Login failed
                self.status_label.configure(text="Login failed. Please try again.")
                self.login_button.configure(state="normal", text="Login")
                
        except AuthenticationError as e:
            # Authentication error
            self.status_label.configure(text=str(e))
            self.login_button.configure(state="normal", text="Login")
            
        except Exception as e:
            # Unexpected error
            logger.error(f"Login error: {e}")
            self.status_label.configure(text="An unexpected error occurred")
            self.login_button.configure(state="normal", text="Login")
    
    def _skip_login(self):
        """Skip login and continue as guest"""
        # Login as default user or guest
        success = self.auth_system.login_as_default_user()
        
        if success:
            # Login successful
            self.login_successful = True
            self.root.destroy()
        else:
            # Login failed
            self.status_label.configure(text="Failed to continue as guest")
    
    def _show_forgot_password(self):
        """Show forgot password dialog"""
        # Create dialog window
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Forgot Password")
        dialog.geometry("350x200")
        dialog.resizable(False, False)
        
        # Make dialog modal
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog on parent window
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (350 // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (200 // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Create content
        frame = ctk.CTkFrame(dialog)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title = ctk.CTkLabel(frame, text="Reset Password", font=ctk.CTkFont(size=16, weight="bold"))
        title.pack(pady=(0, 15))
        
        # Message
        message = ctk.CTkLabel(frame, text="Contact your administrator\nto reset your password.", 
                            font=ctk.CTkFont(size=14))
        message.pack(pady=(0, 15))
        
        # Close button
        close_button = ctk.CTkButton(frame, text="Close", command=dialog.destroy)
        close_button.pack(pady=(5, 0))
    
    def _on_close(self):
        """Handle window close event"""
        if messagebox.askokcancel("Quit", "Do you want to quit the application?"):
            self.root.destroy()
            
    def _auto_fill_credentials(self):
        """Auto-fill credentials if in development mode"""
        # Check if development mode is enabled
        from ..utils.app_config import AppConfig
        config = AppConfig()
        
        if config.get("environment", "").lower() == "development":
            self.username_entry.insert(0, config.get_secret("security.default_admin_username", "admin"))
            self.password_entry.insert(0, config.get_secret("security.default_admin_password", "admin123"))