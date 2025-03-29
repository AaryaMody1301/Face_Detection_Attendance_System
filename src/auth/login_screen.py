"""
Login screen for Face Detection Attendance System
"""
import os
import logging
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk
from src.auth.auth_system import AuthSystem

# Set up logging
logger = logging.getLogger(__name__)

class LoginScreen(ctk.CTkFrame):
    """Login screen widget"""
    
    def __init__(self, master, on_login_success, on_login_error):
        """
        Initialize the login screen
        
        Args:
            master: Parent widget
            on_login_success: Callback function for successful login
            on_login_error: Callback function for login error
        """
        super().__init__(master)
        
        # Save callbacks
        self.on_login_success = on_login_success
        self.on_login_error = on_login_error
        
        # Initialize authentication system
        self.auth_system = AuthSystem()
        
        # Create UI elements
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the login screen UI"""
        # Configure grid layout (2x1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Create sidebar frame with widgets
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)
        
        # App logo
        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="Face Attendance",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        # Try to load logo image if available
        logo_path = os.path.join("assets", "icons", "app_icon.png")
        if os.path.exists(logo_path):
            try:
                logo_img = Image.open(logo_path)
                logo_img = logo_img.resize((100, 100))
                self.logo_photo = ImageTk.PhotoImage(logo_img)
                self.logo_img_label = ctk.CTkLabel(
                    self.sidebar_frame,
                    image=self.logo_photo,
                    text=""
                )
                self.logo_img_label.grid(row=1, column=0, padx=20, pady=(10, 20))
            except Exception as e:
                logger.warning(f"Failed to load logo image: {e}")
        
        # Version info
        self.version_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="v1.2.0",
            font=ctk.CTkFont(size=12)
        )
        self.version_label.grid(row=5, column=0, padx=20, pady=(10, 0))
        
        # Copyright info
        self.copyright_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="© 2025 Parul University",
            font=ctk.CTkFont(size=10)
        )
        self.copyright_label.grid(row=6, column=0, padx=20, pady=(5, 20))
        
        # Create main frame
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        
        # Configure main frame grid layout (3x1)
        self.main_frame.grid_rowconfigure((0, 1, 2), weight=0)  # Title, form, buttons
        self.main_frame.grid_rowconfigure(3, weight=1)  # Empty space
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        # Title
        self.title_label = ctk.CTkLabel(
            self.main_frame,
            text="Sign In",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.title_label.grid(row=0, column=0, padx=20, pady=(40, 20))
        
        # Form frame
        self.form_frame = ctk.CTkFrame(self.main_frame)
        self.form_frame.grid(row=1, column=0, padx=20, pady=20, sticky="ew")
        self.form_frame.columnconfigure(0, weight=1)
        
        # Username entry
        self.username_label = ctk.CTkLabel(
            self.form_frame,
            text="Username:",
            anchor="w",
            font=ctk.CTkFont(size=14)
        )
        self.username_label.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        
        self.username_entry = ctk.CTkEntry(
            self.form_frame,
            width=300,
            placeholder_text="Enter your username"
        )
        self.username_entry.grid(row=1, column=0, padx=20, pady=(0, 15), sticky="ew")
        
        # Password entry
        self.password_label = ctk.CTkLabel(
            self.form_frame,
            text="Password:",
            anchor="w",
            font=ctk.CTkFont(size=14)
        )
        self.password_label.grid(row=2, column=0, padx=20, pady=(5, 5), sticky="w")
        
        self.password_entry = ctk.CTkEntry(
            self.form_frame,
            width=300,
            placeholder_text="Enter your password",
            show="•"
        )
        self.password_entry.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="ew")
        
        # Remember me checkbox
        self.remember_var = ctk.StringVar(value="off")
        self.remember_checkbox = ctk.CTkCheckBox(
            self.form_frame,
            text="Remember me",
            variable=self.remember_var,
            onvalue="on",
            offvalue="off"
        )
        self.remember_checkbox.grid(row=4, column=0, padx=20, pady=(0, 20), sticky="w")
        
        # Button frame
        self.button_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.button_frame.grid(row=2, column=0, padx=20, pady=(10, 20), sticky="ew")
        self.button_frame.columnconfigure(0, weight=1)
        
        # Login button
        self.login_button = ctk.CTkButton(
            self.button_frame,
            text="Login",
            command=self.login,
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40
        )
        self.login_button.grid(row=0, column=0, padx=20, pady=10, sticky="ew")
        
        # Guest login button
        self.guest_button = ctk.CTkButton(
            self.button_frame,
            text="Continue as Guest",
            command=self.guest_login,
            font=ctk.CTkFont(size=14),
            fg_color="transparent",
            border_width=1,
            height=40
        )
        self.guest_button.grid(row=1, column=0, padx=20, pady=(5, 10), sticky="ew")
        
        # Error message label (initially hidden)
        self.error_label = ctk.CTkLabel(
            self.main_frame,
            text="",
            text_color="red",
            font=ctk.CTkFont(size=12)
        )
        self.error_label.grid(row=3, column=0, padx=20, pady=(5, 0), sticky="n")
        
        # Bind Enter key to login
        self.username_entry.bind("<Return>", lambda event: self.password_entry.focus())
        self.password_entry.bind("<Return>", lambda event: self.login())
        
        # Set focus to username entry
        self.username_entry.focus()
        
        # Add default admin account if no users exist
        if not self.auth_system.check_if_any_user_exists():
            logger.info("No users found. Creating default admin account.")
            self.auth_system.create_user("admin", "admin123", "admin")
            self.username_entry.insert(0, "admin")
            self.password_entry.insert(0, "admin123")
    
    def login(self):
        """Attempt to log in with provided credentials"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not username or not password:
            self.show_error("Please enter both username and password")
            return
        
        # Attempt login
        result = self.auth_system.authenticate(username, password)
        
        if result.success:
            # Handle successful login
            user_role = result.user_data.get('role', 'user')
            self.on_login_success(username, user_role)
        else:
            # Handle failed login
            self.show_error(result.message)
    
    def guest_login(self):
        """Login as a guest user with limited access"""
        # Guest users have limited permissions
        self.on_login_success("Guest", "guest")
    
    def show_error(self, message):
        """Show an error message"""
        self.error_label.configure(text=message)
        
        # Reset the message after 5 seconds
        self.after(5000, lambda: self.error_label.configure(text=""))