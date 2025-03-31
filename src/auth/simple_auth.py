"""
Simple Authentication System for Face Detection Attendance System

This is a basic implementation for demonstration purposes.
"""
import logging
import os
import json
import time

# Configure logging
logger = logging.getLogger(__name__)

class SimpleAuthSystem:
    """Simple authentication system for testing purposes"""
    
    def __init__(self):
        """Initialize the simple authentication system"""
        self.current_user = None
        self.is_authenticated = False
        self.users = self._load_users()
        
    def _load_users(self):
        """Load users from a JSON file"""
        try:
            config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.abspath(__file__)))), "config")
            
            # Create config directory if it doesn't exist
            os.makedirs(config_dir, exist_ok=True)
            
            # Check if users file exists
            users_file = os.path.join(config_dir, "users.json")
            if not os.path.exists(users_file):
                # Create default users file
                default_users = {
                    "admin": {
                        "password": "admin",
                        "full_name": "Administrator",
                        "role": "admin",
                        "created_at": time.time()
                    },
                    "user": {
                        "password": "user",
                        "full_name": "Regular User",
                        "role": "user",
                        "created_at": time.time()
                    }
                }
                
                with open(users_file, 'w') as f:
                    json.dump(default_users, f, indent=4)
                    
                return default_users
            
            # Read users from file
            with open(users_file, 'r') as f:
                return json.load(f)
                
        except Exception as e:
            logger.error(f"Error loading users: {e}")
            # Return default users
            return {
                "admin": {
                    "password": "admin",
                    "full_name": "Administrator",
                    "role": "admin"
                }
            }
            
    def login(self, username, password):
        """Login a user
        
        Args:
            username (str): The username
            password (str): The password
            
        Returns:
            bool: True if login successful, False otherwise
        """
        if username in self.users and self.users[username]["password"] == password:
            self.current_user = self.users[username].copy()
            self.current_user["username"] = username
            # Remove sensitive information
            self.current_user.pop("password", None)
            
            self.is_authenticated = True
            logger.info(f"User {username} logged in successfully")
            return True
        
        logger.warning(f"Failed login attempt for user: {username}")
        return False
        
    def logout(self):
        """Logout the current user"""
        if self.is_authenticated:
            logger.info(f"User {self.get_current_user().get('username')} logged out")
            
        self.current_user = None
        self.is_authenticated = False
        
    def register(self, username, password, full_name, role="user"):
        """Register a new user
        
        Args:
            username (str): The username
            password (str): The password
            full_name (str): The user's full name
            role (str, optional): The user's role. Defaults to "user".
            
        Returns:
            bool: True if registration successful, False otherwise
        """
        if username in self.users:
            logger.warning(f"Registration failed: Username {username} already exists")
            return False
            
        self.users[username] = {
            "password": password,
            "full_name": full_name,
            "role": role,
            "created_at": time.time()
        }
        
        # Save users to file
        try:
            config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.abspath(__file__)))), "config")
                
            users_file = os.path.join(config_dir, "users.json")
            with open(users_file, 'w') as f:
                json.dump(self.users, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving users: {e}")
            
        logger.info(f"User {username} registered successfully")
        return True
        
    def is_logged_in(self):
        """Check if a user is logged in
        
        Returns:
            bool: True if a user is logged in, False otherwise
        """
        return self.is_authenticated
        
    def get_current_user(self):
        """Get the current logged in user
        
        Returns:
            dict: The current user or an empty dict if no user is logged in
        """
        return self.current_user or {}
        
    def change_password(self, username, old_password, new_password):
        """Change a user's password
        
        Args:
            username (str): The username
            old_password (str): The old password
            new_password (str): The new password
            
        Returns:
            bool: True if password change successful, False otherwise
        """
        if username in self.users and self.users[username]["password"] == old_password:
            self.users[username]["password"] = new_password
            
            # Save users to file
            try:
                config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
                    os.path.abspath(__file__)))), "config")
                    
                users_file = os.path.join(config_dir, "users.json")
                with open(users_file, 'w') as f:
                    json.dump(self.users, f, indent=4)
            except Exception as e:
                logger.error(f"Error saving users: {e}")
                
            logger.info(f"Password changed for user {username}")
            return True
            
        logger.warning(f"Failed password change attempt for user: {username}")
        return False

# Alias SimpleAuthSystem as SimpleAuth for backward compatibility
# This class is used in modern_app.py
class SimpleAuth(SimpleAuthSystem):
    """Alias for SimpleAuthSystem for backward compatibility"""
    def __init__(self):
        super().__init__()
        
    def is_authenticated(self):
        """Alias for is_logged_in for interface compatibility"""
        return self.is_logged_in()