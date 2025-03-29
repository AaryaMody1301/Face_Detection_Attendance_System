"""
Login View for Face Detection Attendance System
"""
import os
import json
import logging
import hashlib
import customtkinter as ctk
from PIL import Image

# Set up logging
logger = logging.getLogger(__name__)

class LoginView(ctk.CTkFrame):
    """Login view for user authentication"""
    
    def __init__(self, master, on_login_success):
        """
        Initialize the login view
        
        Args:
            master: Parent widget
            on_login_success: Callback function for successful login
        """
        super().__init__(master)
        
        # Save callback
        self.on_login_success = on_login_success
        
        # Load users
        self.users = self._load_users()
        
        # Create UI elements
        self._setup_ui()
        
        logger.info("Login view initialized")
    
    def _setup_ui(self):
        """Set up the login UI"""
        # Configure grid layout (3 rows, 1 column)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=1)
        
        # Load and display logo if available
        self.logo_image = None
        logo_path = os.path.join("assets", "icons", "app_icon.png")
        
        if os.path.exists(logo_path):
            try:
                logo_img = Image.open(logo_path)
                logo_size = (150, 150)
                self.logo_image = ctk.CTkImage(light_image=logo_img, 
                                              dark_image=logo_img, 
                                              size=logo_size)
            except Exception as e:
                logger.warning(f"Failed to load logo: {e}")
        
        # Create login frame
        self.login_frame = ctk.CTkFrame(self, corner_radius=10)
        self.login_frame.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")
        self.login_frame.grid_columnconfigure(0, weight=1)
        self.login_frame.grid_columnconfigure(1, weight=3)
        
        # Add logo image or title
        if self.logo_image:
            self.logo_label = ctk.CTkLabel(self.login_frame, image=self.logo_image, text="")
            self.logo_label.grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 10))
        
        # Title
        self.title_label = ctk.CTkLabel(
            self.login_frame, 
            text="Face Detection Attendance System",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.title_label.grid(row=1, column=0, columnspan=2, padx=20, pady=(10, 20))
        
        # Username
        self.username_label = ctk.CTkLabel(
            self.login_frame,
            text="Username:",
            anchor="w",
            font=ctk.CTkFont(size=14)
        )
        self.username_label.grid(row=2, column=0, padx=(20, 5), pady=(10, 10), sticky="w")
        
        self.username_entry = ctk.CTkEntry(
            self.login_frame,
            placeholder_text="Enter your username",
            font=ctk.CTkFont(size=14)
        )
        self.username_entry.grid(row=2, column=1, padx=(5, 20), pady=(10, 10), sticky="ew")
        
        # Password
        self.password_label = ctk.CTkLabel(
            self.login_frame,
            text="Password:",
            anchor="w",
            font=ctk.CTkFont(size=14)
        )
        self.password_label.grid(row=3, column=0, padx=(20, 5), pady=(10, 10), sticky="w")
        
        self.password_entry = ctk.CTkEntry(
            self.login_frame,
            placeholder_text="Enter your password",
            show="•",
            font=ctk.CTkFont(size=14)
        )
        self.password_entry.grid(row=3, column=1, padx=(5, 20), pady=(10, 10), sticky="ew")
        
        # Login button
        self.login_button = ctk.CTkButton(
            self.login_frame,
            text="Login",
            command=self._on_login,
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40
        )
        self.login_button.grid(row=4, column=0, columnspan=2, padx=20, pady=(20, 10), sticky="ew")
        
        # Status message
        self.status_label = ctk.CTkLabel(
            self.login_frame,
            text="",
            text_color="red",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.grid(row=5, column=0, columnspan=2, padx=20, pady=(5, 20), sticky="ew")
        
        # Create default admin if no users exist
        if not self.users:
            self._create_default_admin()
        
        # Bind Enter key to login
        self.username_entry.bind("<Return>", lambda event: self._on_login())
        self.password_entry.bind("<Return>", lambda event: self._on_login())
        
        # Focus username entry
        self.username_entry.focus_set()
    
    def _load_users(self):
        """
        Load users from credentials file
        
        Returns:
            dict: Users dictionary
        """
        cred_path = os.path.join("config", "credentials.json")
        
        if os.path.exists(cred_path):
            try:
                with open(cred_path, 'r') as f:
                    users = json.load(f)
                logger.info("Loaded user credentials")
                return users
            except Exception as e:
                logger.error(f"Error loading credentials: {e}")
        
        # Return empty dict if file doesn't exist or error occurred
        return {}
    
    def _save_users(self, users=None):
        """
        Save users to credentials file
        
        Args:
            users: Users dictionary to save (default: self.users)
        """
        if users is None:
            users = self.users
            
        cred_path = os.path.join("config", "credentials.json")
        
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(cred_path), exist_ok=True)
            
            # Write to file
            with open(cred_path, 'w') as f:
                json.dump(users, f, indent=4)
            
            logger.info("Saved user credentials")
        except Exception as e:
            logger.error(f"Error saving credentials: {e}")
    
    def _create_default_admin(self):
        """Create default admin account if no users exist"""
        admin = {
            "username": "admin",
            "password": self._hash_password("admin"),
            "name": "Administrator",
            "role": "Admin"
        }
        
        self.users = {"admin": admin}
        self._save_users()
        
        logger.info("Created default admin account")
        self.status_label.configure(
            text="Default admin account created (Username: admin, Password: admin)",
            text_color="blue"
        )
    
    def _hash_password(self, password):
        """
        Hash password using SHA-256
        
        Args:
            password: Plain text password
            
        Returns:
            str: Hashed password
        """
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _on_login(self):
        """Handle login button click"""
        # Get entered username and password
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        # Validate inputs
        if not username or not password:
            self.status_label.configure(text="Please enter both username and password")
            return
        
        # Check if user exists
        if username not in self.users:
            self.status_label.configure(text="Invalid username or password")
            return
        
        # Verify password
        user = self.users[username]
        hashed_password = self._hash_password(password)
        
        if hashed_password != user["password"]:
            self.status_label.configure(text="Invalid username or password")
            return
        
        # Login successful
        logger.info(f"User {username} logged in successfully")
        
        # Prepare user data for callback
        user_data = {
            "username": username,
            "name": user["name"],
            "role": user["role"]
        }
        
        # Call success callback
        self.on_login_success(user_data)