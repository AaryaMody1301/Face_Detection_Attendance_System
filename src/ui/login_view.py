"""
Login View for the Face Detection Attendance System
"""
import os
import logging
import tkinter as tk
from tkinter import StringVar
import customtkinter as ctk
from PIL import Image, ImageTk

from .base_view import BaseView
from ..utils.exceptions import AuthenticationError, ValidationError
from ..auth.auth_manager import AuthManager

class LoginView(BaseView):
    """
    Login view for user authentication
    
    Attributes:
        auth: Authentication manager
        on_login_success: Callback function for successful login
        username_var: StringVar for username input
        password_var: StringVar for password input
        status_var: StringVar for status messages
    """
    
    def __init__(self, master, auth_manager, on_login_success, **kwargs):
        """
        Initialize login view
        
        Args:
            master: Parent widget
            auth_manager: Authentication manager
            on_login_success: Callback function for successful login
            **kwargs: Additional arguments for BaseView
        """
        # Initialize base view
        super().__init__(master, **kwargs)
        
        # Store references
        self.auth = auth_manager
        self.on_login_success = on_login_success
        
        # Initialize variables
        self.username_var = StringVar()
        self.password_var = StringVar()
        self.status_var = StringVar()
        
        # Set up UI
        self.setup_ui()
    
    def setup_ui(self):
        """Set up login UI"""
        # Configure grid
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        
        # Main frame
        main_frame = ctk.CTkFrame(self)
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        # Configure main frame grid - two columns
        main_frame.columnconfigure(0, weight=1)  # Left column (logo)
        main_frame.columnconfigure(1, weight=1)  # Right column (form)
        main_frame.rowconfigure(0, weight=1)
        
        # Create left panel with logo
        left_panel = self.create_logo_panel(main_frame)
        left_panel.grid(row=0, column=0, sticky="nsew")
        
        # Create right panel with login form
        right_panel = self.create_login_panel(main_frame)
        right_panel.grid(row=0, column=1, sticky="nsew")
    
    def create_logo_panel(self, parent):
        """
        Create logo panel
        
        Args:
            parent: Parent widget
            
        Returns:
            Logo panel frame
        """
        # Create frame
        logo_frame = ctk.CTkFrame(parent, corner_radius=0)
        logo_frame.columnconfigure(0, weight=1)
        logo_frame.rowconfigure(0, weight=1)
        
        # Create inner frame for logo and content
        content_frame = ctk.CTkFrame(logo_frame, fg_color="transparent")
        content_frame.grid(row=0, column=0)
        
        # Try to load logo image
        try:
            # Logo image (with fallback text if image not found)
            logo_path = os.path.join("assets", "icons", "app_icon.png")
            
            if os.path.exists(logo_path):
                logo_image = ctk.CTkImage(
                    light_image=Image.open(logo_path),
                    dark_image=Image.open(logo_path),
                    size=(200, 200)
                )
                logo_label = ctk.CTkLabel(content_frame, image=logo_image, text="")
                logo_label.pack(pady=(40, 20))
            else:
                logo_label = ctk.CTkLabel(
                    content_frame,
                    text="FACE RECOGNITION\nATTENDANCE SYSTEM",
                    font=ctk.CTkFont(size=24, weight="bold"),
                    text_color=("gray10", "gray90")
                )
                logo_label.pack(pady=(40, 20))
        except Exception as e:
            # Fallback if image loading fails
            self.logger.error(f"Failed to load logo: {e}")
            logo_label = ctk.CTkLabel(
                content_frame,
                text="FACE RECOGNITION\nATTENDANCE SYSTEM",
                font=ctk.CTkFont(size=24, weight="bold"),
                text_color=("gray10", "gray90")
            )
            logo_label.pack(pady=(40, 20))
        
        # App name 
        app_name = ctk.CTkLabel(
            content_frame,
            text="Face Recognition\nAttendance System",
            font=ctk.CTkFont(size=32, weight="bold")
        )
        app_name.pack(pady=10)
        
        # Tagline
        tagline = ctk.CTkLabel(
            content_frame,
            text="Modern, Secure, Efficient",
            font=ctk.CTkFont(size=16)
        )
        tagline.pack(pady=5)
        
        return logo_frame
    
    def create_login_panel(self, parent):
        """
        Create login form panel
        
        Args:
            parent: Parent widget
            
        Returns:
            Login panel frame
        """
        # Create frame
        login_frame = ctk.CTkFrame(parent)
        
        # Configure grid
        login_frame.columnconfigure(0, weight=1)
        login_frame.rowconfigure(0, weight=1)
        login_frame.rowconfigure(1, weight=0)
        
        # Create content frame
        content_frame = ctk.CTkFrame(login_frame, fg_color="transparent")
        content_frame.grid(row=0, column=0, padx=40, pady=(80, 20), sticky="n")
        
        # Login header
        header_label = ctk.CTkLabel(
            content_frame,
            text="Login to Your Account",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        header_label.pack(pady=(0, 20))
        
        # Username field
        username_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        username_frame.pack(fill="x", pady=10)
        
        username_label = ctk.CTkLabel(
            username_frame,
            text="Username",
            font=ctk.CTkFont(size=14)
        )
        username_label.pack(anchor="w")
        
        username_entry = ctk.CTkEntry(
            username_frame,
            textvariable=self.username_var,
            placeholder_text="Enter your username",
            width=300,
            height=40,
            font=ctk.CTkFont(size=14)
        )
        username_entry.pack(fill="x", pady=(5, 0))
        
        # Password field
        password_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        password_frame.pack(fill="x", pady=10)
        
        password_label = ctk.CTkLabel(
            password_frame,
            text="Password",
            font=ctk.CTkFont(size=14)
        )
        password_label.pack(anchor="w")
        
        password_entry = ctk.CTkEntry(
            password_frame,
            textvariable=self.password_var,
            placeholder_text="Enter your password",
            width=300,
            height=40,
            font=ctk.CTkFont(size=14),
            show="•"
        )
        password_entry.pack(fill="x", pady=(5, 0))
        
        # Login button
        login_button = ctk.CTkButton(
            content_frame,
            text="Login",
            command=self.handle_login,
            font=ctk.CTkFont(size=16),
            height=40,
            width=300
        )
        login_button.pack(pady=20)
        
        # Bind Enter key to login button
        username_entry.bind("<Return>", lambda event: self.handle_login())
        password_entry.bind("<Return>", lambda event: self.handle_login())
        
        # Status message
        status_label = ctk.CTkLabel(
            content_frame,
            textvariable=self.status_var,
            text_color=("red", "red"),
            font=ctk.CTkFont(size=12)
        )
        status_label.pack(pady=10)
        
        # Footer with additional info
        footer_frame = ctk.CTkFrame(login_frame, fg_color="transparent")
        footer_frame.grid(row=1, column=0, padx=40, pady=20, sticky="ew")
        
        footer_text = ctk.CTkLabel(
            footer_frame,
            text="Use admin/admin for administrator account",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray60")
        )
        footer_text.pack()
        
        return login_frame
    
    def handle_login(self):
        """Handle login button press"""
        # Clear status
        self.status_var.set("")
        
        # Get username and password
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()
        
        # Validate inputs
        if not username:
            self.status_var.set("Please enter a username")
            return
        
        if not password:
            self.status_var.set("Please enter a password")
            return
        
        # Show loading animation
        self.show_loading("Authenticating...")
        
        try:
            # Perform authentication in a separate thread to keep UI responsive
            self.after(100, lambda: self._perform_authentication(username, password))
            
        except Exception as e:
            self.hide_loading()
            self.status_var.set(f"Authentication error: {str(e)}")
            self.logger.error(f"Login error: {e}")
    
    def _perform_authentication(self, username, password):
        """
        Perform authentication
        
        Args:
            username: Username
            password: Password
        """
        try:
            # Authenticate user
            user = self.auth.authenticate(username, password)
            
            # Hide loading animation
            self.hide_loading()
            
            if user:
                # Authentication successful
                self.logger.info(f"User {username} authenticated successfully")
                
                # Call success callback
                self.on_login_success(user)
            else:
                # Authentication failed
                self.status_var.set("Invalid username or password")
                
        except AuthenticationError as e:
            self.hide_loading()
            self.status_var.set(str(e))
            self.logger.warning(f"Authentication failed: {e}")
            
        except Exception as e:
            self.hide_loading()
            self.status_var.set("Authentication error")
            self.logger.error(f"Login error: {e}")
    
    def on_close(self):
        """Clean up resources when view is closed"""
        super().on_close()
        # Additional cleanup if needed