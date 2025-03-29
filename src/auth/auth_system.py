"""
Authentication system for Face Detection Attendance System
"""
import os
import json
import hashlib
import logging
from dataclasses import dataclass
from typing import Dict, Optional

# Set up logging
logger = logging.getLogger(__name__)

@dataclass
class AuthResult:
    """Class to represent authentication results"""
    success: bool
    message: str
    user_data: Optional[Dict] = None

class AuthSystem:
    """Authentication system for user management and login"""
    
    def __init__(self):
        """Initialize the authentication system"""
        self.users_file = os.path.join("config", "users.json")
        self.users = {}
        self._load_users()
    
    def _load_users(self):
        """Load users from the users file"""
        # Create config directory if it doesn't exist
        os.makedirs(os.path.dirname(self.users_file), exist_ok=True)
        
        # Load users if the file exists
        if os.path.exists(self.users_file):
            try:
                with open(self.users_file, 'r') as f:
                    self.users = json.load(f)
                logger.info(f"Loaded {len(self.users)} users from {self.users_file}")
            except Exception as e:
                logger.error(f"Error loading users from {self.users_file}: {e}")
                self.users = {}
        else:
            logger.info(f"Users file {self.users_file} does not exist. Starting with empty users.")
            self.users = {}
    
    def _save_users(self):
        """Save users to the users file"""
        try:
            with open(self.users_file, 'w') as f:
                json.dump(self.users, f, indent=2)
            logger.info(f"Saved {len(self.users)} users to {self.users_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving users to {self.users_file}: {e}")
            return False
    
    def _hash_password(self, password: str) -> str:
        """
        Hash a password for secure storage
        
        Args:
            password: The password to hash
            
        Returns:
            str: The hashed password
        """
        # Simple SHA-256 hash for demonstration
        # In a production environment, use a more secure method like bcrypt
        return hashlib.sha256(password.encode()).hexdigest()
    
    def authenticate(self, username: str, password: str) -> AuthResult:
        """
        Authenticate a user with username and password
        
        Args:
            username: The username
            password: The password
            
        Returns:
            AuthResult: The result of the authentication attempt
        """
        # Check if user exists
        if username not in self.users:
            logger.warning(f"Authentication failed for unknown user: {username}")
            return AuthResult(success=False, message="Invalid username or password")
        
        # Check password
        user = self.users[username]
        hashed_password = self._hash_password(password)
        
        if hashed_password != user['password']:
            logger.warning(f"Authentication failed for user: {username}")
            return AuthResult(success=False, message="Invalid username or password")
        
        # Authentication successful
        logger.info(f"Authentication successful for user: {username}")
        
        # Create a copy of user data without the password
        user_data = {k: v for k, v in user.items() if k != 'password'}
        
        return AuthResult(
            success=True,
            message="Authentication successful",
            user_data=user_data
        )
    
    def create_user(self, username: str, password: str, role: str = "user") -> AuthResult:
        """
        Create a new user
        
        Args:
            username: The username
            password: The password
            role: User role (default: "user")
            
        Returns:
            AuthResult: The result of the user creation
        """
        # Check if username already exists
        if username in self.users:
            logger.warning(f"User creation failed: username '{username}' already exists")
            return AuthResult(success=False, message=f"Username '{username}' already exists")
        
        # Create the user
        self.users[username] = {
            'password': self._hash_password(password),
            'role': role,
            'created_at': 'auto'  # Would be datetime in a real implementation
        }
        
        # Save users
        if self._save_users():
            logger.info(f"Created new user: {username} with role {role}")
            return AuthResult(
                success=True,
                message=f"User '{username}' created successfully",
                user_data={'username': username, 'role': role}
            )
        else:
            # Revert changes if save failed
            del self.users[username]
            logger.error(f"User creation failed: could not save users")
            return AuthResult(success=False, message="Could not save user data")
    
    def update_user(self, username: str, new_data: Dict) -> AuthResult:
        """
        Update user data
        
        Args:
            username: The username
            new_data: New user data
            
        Returns:
            AuthResult: The result of the user update
        """
        # Check if user exists
        if username not in self.users:
            logger.warning(f"User update failed: username '{username}' does not exist")
            return AuthResult(success=False, message=f"User '{username}' does not exist")
        
        # Update user data (except password)
        user = self.users[username]
        for key, value in new_data.items():
            if key != 'password':
                user[key] = value
        
        # Update password if provided
        if 'password' in new_data:
            user['password'] = self._hash_password(new_data['password'])
        
        # Save users
        if self._save_users():
            logger.info(f"Updated user: {username}")
            return AuthResult(success=True, message=f"User '{username}' updated successfully")
        else:
            logger.error(f"User update failed: could not save users")
            return AuthResult(success=False, message="Could not save user data")
    
    def delete_user(self, username: str) -> AuthResult:
        """
        Delete a user
        
        Args:
            username: The username
            
        Returns:
            AuthResult: The result of the user deletion
        """
        # Check if user exists
        if username not in self.users:
            logger.warning(f"User deletion failed: username '{username}' does not exist")
            return AuthResult(success=False, message=f"User '{username}' does not exist")
        
        # Delete the user
        del self.users[username]
        
        # Save users
        if self._save_users():
            logger.info(f"Deleted user: {username}")
            return AuthResult(success=True, message=f"User '{username}' deleted successfully")
        else:
            logger.error(f"User deletion failed: could not save users")
            return AuthResult(success=False, message="Could not save user data")
    
    def get_user(self, username: str) -> Optional[Dict]:
        """
        Get user data
        
        Args:
            username: The username
            
        Returns:
            Optional[Dict]: User data without password, or None if user doesn't exist
        """
        if username not in self.users:
            return None
        
        # Create a copy of user data without the password
        user = {k: v for k, v in self.users[username].items() if k != 'password'}
        return user
    
    def get_all_users(self) -> Dict:
        """
        Get all users
        
        Returns:
            Dict: All users without passwords
        """
        return {
            username: {k: v for k, v in user.items() if k != 'password'}
            for username, user in self.users.items()
        }
    
    def check_if_any_user_exists(self) -> bool:
        """
        Check if any user exists
        
        Returns:
            bool: True if at least one user exists, False otherwise
        """
        return len(self.users) > 0