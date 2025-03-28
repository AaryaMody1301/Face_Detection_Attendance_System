"""
Authentication Manager for the Face Detection Attendance System
"""
import os
import re
import uuid
import logging
import hashlib
import secrets
import datetime
from typing import Dict, Optional, Any, List, Tuple

from ..utils.exceptions import AuthenticationError, ValidationError
from ..utils.app_config import AppConfig
from ..utils.env_manager import env_manager
from ..database.db_manager import DatabaseManager

# Configure logging
logger = logging.getLogger(__name__)

class AuthManager:
    """
    Authentication Manager handles user authentication, authorization, and session management
    
    Attributes:
        db: Database manager
        config: Security configuration
        active_sessions: Dictionary of active user sessions
    """
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        Initialize authentication manager
        
        Args:
            db_manager: Optional database manager instance
        """
        # Initialize database
        self.db = db_manager if db_manager else DatabaseManager()
        
        # Load security configuration
        self.config = AppConfig().get_security_config()
        
        # Active user sessions
        self.active_sessions = {}
        
        # Session timeout in minutes
        self.session_timeout = self.config.get("session_timeout", 30)
        
        # Maximum login attempts
        self.max_login_attempts = self.config.get("max_login_attempts", 5)
        
        # Failed login attempts
        self.failed_attempts = {}
    
    def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Authenticate a user
        
        Args:
            username: Username
            password: Password
            
        Returns:
            User info dictionary or None if authentication failed
            
        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            # Check if user is locked out due to too many failed attempts
            if self._is_user_locked_out(username):
                raise AuthenticationError("Account temporarily locked due to too many failed login attempts")
            
            # Get user from database
            user = self._get_user(username)
            if not user:
                # Track failed attempt
                self._track_failed_attempt(username)
                raise AuthenticationError("Invalid username or password")
            
            # Check if user is active
            if not user.get("is_active", 1):
                raise AuthenticationError("User account is inactive")
            
            # Verify password
            if not self._verify_password(password, user["password_hash"]):
                # Track failed attempt
                self._track_failed_attempt(username)
                raise AuthenticationError("Invalid username or password")
            
            # Clear failed attempts on successful login
            if username in self.failed_attempts:
                del self.failed_attempts[username]
            
            # Create session
            session_id = self._create_session(user)
            
            # Return user info (without sensitive data)
            return {
                "id": user["id"],
                "username": user["username"],
                "full_name": user["full_name"],
                "email": user["email"],
                "role": user["role"],
                "session_id": session_id
            }
            
        except Exception as e:
            if not isinstance(e, AuthenticationError):
                logger.error(f"Authentication error: {e}")
                raise AuthenticationError("Authentication failed")
            raise
    
    def _get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Get user from database
        
        Args:
            username: Username
            
        Returns:
            User data or None if not found
        """
        query = "SELECT * FROM users WHERE username = ?"
        return self.db.execute_query(query, (username,), fetch_one=True)
    
    def _is_user_locked_out(self, username: str) -> bool:
        """
        Check if a user is locked out due to too many failed login attempts
        
        Args:
            username: Username
            
        Returns:
            True if user is locked out, False otherwise
        """
        if username not in self.failed_attempts:
            return False
            
        attempts, last_attempt_time = self.failed_attempts[username]
        if attempts < self.max_login_attempts:
            return False
            
        # Check if lockout period has expired (default: 30 minutes)
        lockout_minutes = 30
        lockout_seconds = lockout_minutes * 60
        current_time = datetime.datetime.now()
        time_diff = (current_time - last_attempt_time).total_seconds()
        
        if time_diff > lockout_seconds:
            # Reset failed attempts if lockout period has expired
            del self.failed_attempts[username]
            return False
            
        return True
    
    def _track_failed_attempt(self, username: str) -> None:
        """
        Track failed login attempt
        
        Args:
            username: Username
        """
        current_time = datetime.datetime.now()
        if username in self.failed_attempts:
            attempts, _ = self.failed_attempts[username]
            self.failed_attempts[username] = (attempts + 1, current_time)
        else:
            self.failed_attempts[username] = (1, current_time)
            
        attempts, _ = self.failed_attempts[username]
        if attempts >= self.max_login_attempts:
            logger.warning(f"User {username} locked out due to too many failed login attempts")
    
    def _verify_password(self, password: str, stored_hash: str) -> bool:
        """
        Verify a password against its stored hash
        
        If the stored hash is in the legacy format (plain text), upgrade it
        to the new secure format.
        
        Args:
            password: Plain text password
            stored_hash: Stored password hash
            
        Returns:
            True if password matches, False otherwise
        """
        # Check if stored hash is in the new secure format
        if stored_hash.startswith("$argon2") or stored_hash.startswith("$pbkdf2"):
            # Use the password_verify library function
            try:
                import passlib.hash
                if stored_hash.startswith("$argon2"):
                    return passlib.hash.argon2.verify(password, stored_hash)
                else:
                    return passlib.hash.pbkdf2_sha256.verify(password, stored_hash)
            except ImportError:
                # Fallback if passlib is not available
                salt, hash_value = stored_hash.split("$")
                password_hash = self._legacy_hash_password(password, salt)
                return password_hash == hash_value
        
        # Legacy plain text comparison (insecure)
        # This should be removed in production environments
        if stored_hash == password: