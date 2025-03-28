"""
Authentication Manager for Face Detection Attendance System

This module provides the authentication manager for the application,
with high-level authentication functionality that interfaces with
the AuthSystem for lower-level authentication operations.
"""
import os
import time
import logging
import datetime
from typing import Dict, Any, Optional, Tuple, List, Union

from ..utils.app_config import AppConfig
from ..utils.exceptions import AuthenticationError, AuthorizationError
from .auth_system import AuthSystem

# Configure logger
logger = logging.getLogger(__name__)

class AuthManager:
    """
    Authentication manager for handling user authentication and session management
    
    Attributes:
        auth_system: Lower-level authentication system
        current_user: Currently authenticated user
        config: Application configuration
    """
    
    def __init__(self, db_connection=None):
        """
        Initialize authentication manager
        
        Args:
            db_connection: Database connection to use
        """
        # Load configuration
        self.config = AppConfig()
        
        # Create authentication system
        require_login = self.config.get_bool("security.require_login", False)
        self.auth_system = AuthSystem(db_connection=db_connection, require_login=require_login)
        
        # Initialize user state
        self.current_user = None
        
        logger.info("Authentication manager initialized")
    
    def authenticate(self, username: str, password: str) -> Dict[str, Any]:
        """
        Authenticate a user
        
        Args:
            username: Username
            password: Password
            
        Returns:
            Dict containing user information if authentication successful, None otherwise
            
        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            # Try to log in using the authentication system
            success = self.auth_system.login(username, password)
            
            if success:
                # Get user from authentication system
                self.current_user = self.auth_system.get_current_user()
                return self.current_user
            else:
                raise AuthenticationError("Invalid username or password")
                
        except AuthenticationError as e:
            logger.warning(f"Authentication failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during authentication: {e}")
            raise AuthenticationError(f"Authentication error: {str(e)}")
    
    def logout(self) -> bool:
        """
        Log out the current user
        
        Returns:
            bool: True if logout successful, False otherwise
        """
        if not self.is_authenticated():
            logger.warning("Attempted logout but no user is authenticated")
            return False
            
        try:
            # Log out using the authentication system
            success = self.auth_system.logout()
            
            if success:
                # Clear current user
                old_username = self.current_user.get('username', 'Unknown')
                self.current_user = None
                logger.info(f"User logged out: {old_username}")
                return True
            else:
                logger.warning("Logout failed")
                return False
                
        except Exception as e:
            logger.error(f"Error during logout: {e}")
            return False
    
    def is_authenticated(self) -> bool:
        """
        Check if a user is currently authenticated
        
        Returns:
            bool: True if a user is authenticated, False otherwise
        """
        # Check authentication status in auth system
        return self.auth_system.is_authenticated()
    
    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """
        Get the currently authenticated user
        
        Returns:
            Dict containing user information or None if no user is authenticated
        """
        if not self.is_authenticated():
            return None
            
        # If user is cached, return it
        if self.current_user:
            return self.current_user
            
        # Otherwise get from auth system
        self.current_user = self.auth_system.get_current_user()
        return self.current_user
    
    def has_permission(self, permission: str) -> bool:
        """
        Check if the current user has a specific permission
        
        Args:
            permission: Permission to check
            
        Returns:
            bool: True if the user has the permission, False otherwise
        """
        return self.auth_system.has_permission(permission)
    
    def require_permission(self, permission: str):
        """
        Require a specific permission, raising an exception if not available
        
        Args:
            permission: Permission to require
            
        Raises:
            AuthorizationError: If the user doesn't have the required permission
        """
        if not self.has_permission(permission):
            user = self.get_current_user()
            username = user.get('username', 'Unknown') if user else 'Not authenticated'
            
            logger.warning(f"Permission denied: {username} tried to access {permission}")
            raise AuthorizationError(f"You don't have permission to perform this action")
    
    def change_password(self, current_password: str, new_password: str) -> bool:
        """
        Change password for the current user
        
        Args:
            current_password: Current password
            new_password: New password
            
        Returns:
            bool: True if password changed successfully, False otherwise
            
        Raises:
            AuthenticationError: If validation fails or user is not authenticated
        """
        if not self.is_authenticated():
            raise AuthenticationError("You must be logged in to change your password")
            
        # Get user ID from current user
        user = self.get_current_user()
        user_id = user.get('id')
        
        if not user_id:
            raise AuthenticationError("Unable to determine user ID")
        
        # Validate new password
        min_length = self.config.get_int("security.password_min_length", 6)
        
        if len(new_password) < min_length:
            raise AuthenticationError(f"Password must be at least {min_length} characters")
            
        # Check if new password is significantly different from current
        if current_password == new_password:
            raise AuthenticationError("New password must be different from current password")
            
        # Change password using auth system
        return self.auth_system.change_password(user_id, current_password, new_password)
    
    def create_user(self, username: str, password: str, full_name: str, 
                   email: str = None, role: str = "user") -> Dict[str, Any]:
        """
        Create a new user
        
        Args:
            username: Username
            password: Password
            full_name: Full name
            email: Email address
            role: Role (admin, teacher, user)
            
        Returns:
            Dict containing user information
            
        Raises:
            AuthorizationError: If the current user doesn't have permission to create users
            AuthenticationError: If validation fails
        """
        # Check permissions
        self.require_permission("manage_users")
        
        # Validate username (alphanumeric and underscores only)
        if not username.replace('_', '').isalnum():
            raise AuthenticationError("Username can only contain letters, numbers, and underscores")
            
        # Validate password
        min_length = self.config.get_int("security.password_min_length", 6)
        if len(password) < min_length:
            raise AuthenticationError(f"Password must be at least {min_length} characters")
            
        # Get current username for audit trail
        current_user = self.get_current_user()
        created_by = current_user.get('username') if current_user else None
        
        # Create user using auth system
        return self.auth_system.create_user(
            username=username,
            password=password,
            full_name=full_name,
            email=email,
            role=role,
            created_by=created_by
        )
    
    def get_user(self, user_id: int) -> Dict[str, Any]:
        """
        Get user information
        
        Args:
            user_id: User ID
            
        Returns:
            Dict containing user information
            
        Raises:
            AuthorizationError: If the current user doesn't have permission
            AuthenticationError: If user doesn't exist
        """
        # Check permissions (can view other users or is requesting own info)
        current_user = self.get_current_user()
        is_own_info = current_user and current_user.get('id') == user_id
        
        if not (is_own_info or self.has_permission("manage_users")):
            self.require_permission("manage_users")  # Will raise error
            
        # Get user info from auth system
        return self.auth_system.get_user(user_id)
    
    def login_as_guest(self) -> bool:
        """
        Log in as a guest user
        
        Returns:
            bool: True if login successful, False otherwise
        """
        # Use default user logic from auth system
        result = self.auth_system.login_as_default_user()
        
        if result:
            # Update current user
            self.current_user = self.auth_system.get_current_user()
            logger.info(f"Logged in as guest user: {self.current_user.get('username')}")
            
        return result