"""
Authentication System for the Face Detection Attendance System

This module provides the authentication system for the application,
handling user login, permissions, and session management.
"""
import os
import time
import logging
import hashlib
import json
import secrets
import datetime
from typing import Dict, Any, Optional, List, Union

from ..database.db_manager import DatabaseManager
from ..utils.app_config import AppConfig
from ..utils.exceptions import AuthenticationError, AuthorizationError, DatabaseError

# Configure logger
logger = logging.getLogger(__name__)

class AuthSystem:
    """
    Authentication System class for managing user authentication and authorization
    
    Attributes:
        db: Database connection
        config: Application configuration
        current_user: Currently authenticated user
        is_authenticated_flag: Whether a user is currently authenticated
        session_start_time: Time when the current session started
    """
    
    def __init__(self, db_connection=None, require_login: bool = False):
        """
        Initialize authentication system
        
        Args:
            db_connection: Database connection to use
            require_login: Whether authentication is required to use the application
        """
        self.db = db_connection if db_connection else DatabaseManager()
        self.config = AppConfig()
        self.current_user = None
        self.is_authenticated_flag = False
        self.session_start_time = None
        self.require_login = require_login
        
        # Initialize authentication system
        self._initialize()
    
    def _initialize(self):
        """Initialize the authentication system"""
        try:
            # Create users table if it doesn't exist
            self._ensure_tables_exist()
            
            # Create default admin user if no users exist
            self._create_default_users()
            
            logger.info("Authentication system initialized")
        except Exception as e:
            logger.error(f"Error initializing authentication system: {e}")
            raise
    
    def _ensure_tables_exist(self):
        """Ensure the necessary tables exist in the database"""
        try:
            # Create users table
            self.db.execute_query('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                full_name TEXT,
                email TEXT,
                role TEXT NOT NULL DEFAULT 'user',
                last_login TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
            ''', commit=True)
            
            # Create user_sessions table
            self.db.execute_query('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_token TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                ip_address TEXT,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            ''', commit=True)
            
            # Create login_attempts table for tracking failed logins
            self.db.execute_query('''
            CREATE TABLE IF NOT EXISTS login_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                ip_address TEXT,
                attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                success INTEGER DEFAULT 0
            )
            ''', commit=True)
            
            logger.debug("Authentication tables created")
        except Exception as e:
            logger.error(f"Error creating authentication tables: {e}")
            raise DatabaseError(f"Failed to create authentication tables: {e}")
    
    def _create_default_users(self):
        """Create default users if no users exist"""
        try:
            # Check if any users exist
            result = self.db.execute_query(
                "SELECT COUNT(*) FROM users", 
                fetch_one=True
            )
            
            if result and result.get('COUNT(*)', 0) == 0:
                # Create default admin user
                admin_username = self.config.get_secret("security.default_admin_username", "admin")
                admin_password = self.config.get_secret("security.default_admin_password", "admin123")
                
                # Hash the password
                salt = secrets.token_hex(16)  # Generate random salt
                password_hash = self._hash_password(admin_password, salt)
                
                # Insert admin user
                self.db.execute_query(
                    "INSERT INTO users (username, password_hash, salt, full_name, role) VALUES (?, ?, ?, ?, ?)",
                    (admin_username, password_hash, salt, "Administrator", "admin"),
                    commit=True
                )
                
                # Create default user
                user_username = self.config.get_secret("security.default_user_username", "user")
                user_password = self.config.get_secret("security.default_user_password", "user123")
                
                # Hash the password
                salt = secrets.token_hex(16)  # Generate random salt
                password_hash = self._hash_password(user_password, salt)
                
                # Insert default user
                self.db.execute_query(
                    "INSERT INTO users (username, password_hash, salt, full_name, role) VALUES (?, ?, ?, ?, ?)",
                    (user_username, password_hash, salt, "Default User", "user"),
                    commit=True
                )
                
                logger.info("Default users created")
            else:
                logger.debug("Users already exist in the database")
                
        except Exception as e:
            logger.error(f"Error creating default users: {e}")
            raise
    
    def login(self, username: str, password: str, ip_address: str = None) -> bool:
        """
        Log in a user
        
        Args:
            username: Username
            password: Password
            ip_address: IP address of the client
            
        Returns:
            bool: True if login successful, False otherwise
        """
        try:
            # Check if account is locked due to too many failed attempts
            if self._is_account_locked(username):
                logger.warning(f"Account locked due to too many failed login attempts: {username}")
                raise AuthenticationError("Account locked due to too many failed login attempts")
            
            # Query user data
            user_data = self.db.execute_query(
                "SELECT id, username, password_hash, salt, full_name, email, role, is_active FROM users WHERE username = ?",
                (username,),
                fetch_one=True
            )
            
            # Check if user exists
            if not user_data:
                # Record failed login attempt
                self._record_login_attempt(username, ip_address, False)
                logger.warning(f"Login failed: User not found: {username}")
                raise AuthenticationError("Invalid username or password")
            
            # Check if user is active
            if not user_data.get("is_active", 0):
                logger.warning(f"Login failed: Account disabled: {username}")
                raise AuthenticationError("Account is disabled")
            
            # Validate password
            stored_hash = user_data.get("password_hash", "")
            salt = user_data.get("salt", "")
            
            if not self._verify_password(password, stored_hash, salt):
                # Record failed login attempt
                self._record_login_attempt(username, ip_address, False)
                logger.warning(f"Login failed: Invalid password for user: {username}")
                raise AuthenticationError("Invalid username or password")
            
            # Authentication successful
            self.current_user = {
                "id": user_data.get("id"),
                "username": user_data.get("username"),
                "full_name": user_data.get("full_name"),
                "email": user_data.get("email"),
                "role": user_data.get("role"),
                "is_active": bool(user_data.get("is_active"))
            }
            
            # Create a new session
            self._create_session(user_data.get("id"), ip_address)
            
            # Record successful login attempt
            self._record_login_attempt(username, ip_address, True)
            
            # Update last login time
            self.db.execute_query(
                "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
                (user_data.get("id"),),
                commit=True
            )
            
            logger.info(f"User logged in: {username}")
            return True
            
        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Error during login: {e}")
            raise AuthenticationError(f"Login failed: {str(e)}")
    
    def logout(self):
        """
        Log out the current user
        
        Returns:
            bool: True if logout successful, False otherwise
        """
        try:
            if not self.is_authenticated():
                logger.warning("Logout attempt, but no user is authenticated")
                return False
            
            # Invalidate session
            if hasattr(self, 'session_token') and self.session_token:
                self.db.execute_query(
                    "UPDATE user_sessions SET is_active = 0 WHERE session_token = ?",
                    (self.session_token,),
                    commit=True
                )
            
            # Clear user data
            username = self.current_user.get("username") if self.current_user else "Unknown"
            self.current_user = None
            self.is_authenticated_flag = False
            self.session_start_time = None
            self.session_token = None
            
            logger.info(f"User logged out: {username}")
            return True
            
        except Exception as e:
            logger.error(f"Error during logout: {e}")
            return False
    
    def is_authenticated(self) -> bool:
        """
        Check if a user is currently authenticated
        
        Returns:
            bool: True if a user is authenticated, False otherwise
        """
        # Check if session has expired
        if self.is_authenticated_flag and self.session_start_time:
            session_timeout = self.config.get_int("security.session_timeout_minutes", 30)
            elapsed_minutes = (time.time() - self.session_start_time) / 60
            
            if elapsed_minutes > session_timeout:
                logger.info("Session expired, logging out")
                self.logout()
                return False
        
        return self.is_authenticated_flag
    
    def get_current_user(self) -> Dict[str, Any]:
        """
        Get the currently authenticated user
        
        Returns:
            Dict containing user information or None if no user is authenticated
        """
        if not self.is_authenticated():
            return {
                "id": None,
                "username": "Guest",
                "full_name": "Guest User",
                "role": "guest"
            }
            
        return self.current_user
    
    def has_permission(self, permission: str) -> bool:
        """
        Check if the current user has a specific permission
        
        Args:
            permission: Permission to check
            
        Returns:
            bool: True if the user has the permission, False otherwise
        """
        if not self.is_authenticated():
            return False
            
        # Get user role
        role = self.current_user.get("role", "guest")
        
        # Define role-based permissions
        role_permissions = {
            "admin": ["view_students", "add_student", "edit_student", "delete_student",
                     "view_attendance", "mark_attendance", "edit_attendance", "delete_attendance",
                     "export_data", "import_data", "view_analytics", "manage_subjects",
                     "system_settings", "manage_users", "view_logs"],
            "teacher": ["view_students", "add_student", 
                       "view_attendance", "mark_attendance", "edit_attendance",
                       "export_data", "view_analytics", "manage_subjects"],
            "user": ["view_students", "view_attendance", "mark_attendance", "view_analytics"],
            "guest": ["view_login"]
        }
        
        # Get permissions for the user's role
        allowed_permissions = role_permissions.get(role, [])
        
        # Check if the permission is allowed for the role
        return permission in allowed_permissions
    
    def _hash_password(self, password: str, salt: str) -> str:
        """
        Hash a password with salt
        
        Args:
            password: Plain text password
            salt: Salt value
            
        Returns:
            str: Hashed password
        """
        # Combine password and salt
        salted = password + salt
        
        # Hash password using SHA-256
        return hashlib.sha256(salted.encode()).hexdigest()
    
    def _verify_password(self, password: str, stored_hash: str, salt: str) -> bool:
        """
        Verify a password against a stored hash
        
        Args:
            password: Plain text password
            stored_hash: Stored hash
            salt: Salt value
            
        Returns:
            bool: True if password is valid, False otherwise
        """
        # Hash the provided password with the same salt
        hashed = self._hash_password(password, salt)
        
        # Compare hashes
        return hashed == stored_hash
    
    def _create_session(self, user_id: int, ip_address: str = None):
        """
        Create a new session for a user
        
        Args:
            user_id: User ID
            ip_address: IP address of the client
        """
        # Generate session token
        self.session_token = secrets.token_hex(32)
        
        # Set session start time
        self.session_start_time = time.time()
        
        # Set authenticated flag
        self.is_authenticated_flag = True
        
        # Get session expiry from config
        expiry_days = self.config.get_int("security.jwt_expiry_days", 7)
        expires_at = datetime.datetime.now() + datetime.timedelta(days=expiry_days)
        
        # Store session in database
        self.db.execute_query(
            "INSERT INTO user_sessions (user_id, session_token, expires_at, ip_address) VALUES (?, ?, ?, ?)",
            (user_id, self.session_token, expires_at.isoformat(), ip_address),
            commit=True
        )
    
    def _is_account_locked(self, username: str) -> bool:
        """
        Check if an account is locked due to too many failed login attempts
        
        Args:
            username: Username to check
            
        Returns:
            bool: True if account is locked, False otherwise
        """
        try:
            # Get max login attempts from config
            max_attempts = self.config.get_int("security.max_login_attempts", 5)
            
            # Calculate the timeframe for failed attempts (last 30 minutes)
            timeframe_minutes = 30
            cutoff_time = datetime.datetime.now() - datetime.timedelta(minutes=timeframe_minutes)
            
            # Count failed login attempts
            result = self.db.execute_query(
                """
                SELECT COUNT(*) FROM login_attempts 
                WHERE username = ? AND success = 0 AND attempted_at > ?
                """,
                (username, cutoff_time.isoformat()),
                fetch_one=True
            )
            
            return result and result.get('COUNT(*)', 0) >= max_attempts
            
        except Exception as e:
            logger.error(f"Error checking account lock status: {e}")
            return False
    
    def _record_login_attempt(self, username: str, ip_address: str, success: bool):
        """
        Record a login attempt
        
        Args:
            username: Username
            ip_address: IP address of the client
            success: Whether the login attempt was successful
        """
        try:
            self.db.execute_query(
                "INSERT INTO login_attempts (username, ip_address, success) VALUES (?, ?, ?)",
                (username, ip_address, 1 if success else 0),
                commit=True
            )
        except Exception as e:
            logger.error(f"Error recording login attempt: {e}")
    
    def change_password(self, user_id: int, current_password: str, new_password: str) -> bool:
        """
        Change a user's password
        
        Args:
            user_id: User ID
            current_password: Current password
            new_password: New password
            
        Returns:
            bool: True if password changed successfully, False otherwise
        """
        try:
            # Get user data
            user_data = self.db.execute_query(
                "SELECT password_hash, salt FROM users WHERE id = ?",
                (user_id,),
                fetch_one=True
            )
            
            if not user_data:
                logger.warning(f"Password change failed: User not found: {user_id}")
                raise AuthenticationError("User not found")
            
            # Verify current password
            stored_hash = user_data.get("password_hash", "")
            salt = user_data.get("salt", "")
            
            if not self._verify_password(current_password, stored_hash, salt):
                logger.warning(f"Password change failed: Invalid current password for user: {user_id}")
                raise AuthenticationError("Invalid current password")
            
            # Generate new salt and hash new password
            new_salt = secrets.token_hex(16)
            new_hash = self._hash_password(new_password, new_salt)
            
            # Update user password
            self.db.execute_query(
                "UPDATE users SET password_hash = ?, salt = ? WHERE id = ?",
                (new_hash, new_salt, user_id),
                commit=True
            )
            
            logger.info(f"Password changed for user: {user_id}")
            return True
            
        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Error changing password: {e}")
            raise AuthenticationError(f"Password change failed: {str(e)}")
    
    def create_user(self, username: str, password: str, full_name: str, email: str = None, 
                   role: str = "user", created_by: str = None) -> Dict[str, Any]:
        """
        Create a new user
        
        Args:
            username: Username
            password: Password
            full_name: Full name
            email: Email address
            role: Role (admin, teacher, user)
            created_by: Username of the creator
            
        Returns:
            Dict containing user information
        """
        try:
            # Check if username already exists
            exists = self.db.execute_query(
                "SELECT COUNT(*) FROM users WHERE username = ?",
                (username,),
                fetch_one=True
            )
            
            if exists and exists.get('COUNT(*)', 0) > 0:
                logger.warning(f"User creation failed: Username already exists: {username}")
                raise AuthenticationError("Username already exists")
            
            # Generate salt and hash password
            salt = secrets.token_hex(16)
            password_hash = self._hash_password(password, salt)
            
            # Insert user
            user_id = self.db.execute_query(
                """
                INSERT INTO users 
                (username, password_hash, salt, full_name, email, role) 
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (username, password_hash, salt, full_name, email, role),
                commit=True
            )
            
            # Log action
            self.db.log_audit(
                action="create_user",
                entity="user",
                entity_id=username,
                user=created_by,
                details=f"Created user {username} with role {role}"
            )
            
            logger.info(f"User created: {username} with role {role}")
            
            return {
                "id": user_id,
                "username": username,
                "full_name": full_name,
                "email": email,
                "role": role,
                "is_active": True
            }
            
        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            raise AuthenticationError(f"User creation failed: {str(e)}")
    
    def get_user(self, user_id: int) -> Dict[str, Any]:
        """
        Get user information
        
        Args:
            user_id: User ID
            
        Returns:
            Dict containing user information
        """
        try:
            user_data = self.db.execute_query(
                """
                SELECT id, username, full_name, email, role, last_login, created_at, is_active 
                FROM users WHERE id = ?
                """,
                (user_id,),
                fetch_one=True
            )
            
            if not user_data:
                logger.warning(f"Get user failed: User not found: {user_id}")
                raise AuthenticationError("User not found")
                
            return {
                "id": user_data.get("id"),
                "username": user_data.get("username"),
                "full_name": user_data.get("full_name"),
                "email": user_data.get("email"),
                "role": user_data.get("role"),
                "last_login": user_data.get("last_login"),
                "created_at": user_data.get("created_at"),
                "is_active": bool(user_data.get("is_active"))
            }
            
        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            raise AuthenticationError(f"Failed to get user: {str(e)}")
    
    def login_as_default_user(self) -> bool:
        """
        Log in as the default user for non-authentication mode
        
        Returns:
            bool: True if login successful, False otherwise
        """
        try:
            # Get default user
            user_data = self.db.execute_query(
                """
                SELECT id, username, full_name, email, role, is_active 
                FROM users WHERE role = 'user' LIMIT 1
                """,
                fetch_one=True
            )
            
            if not user_data:
                logger.warning("Auto-login failed: No default user found")
                return False
            
            # Set user data
            self.current_user = {
                "id": user_data.get("id"),
                "username": user_data.get("username"),
                "full_name": user_data.get("full_name") or "Default User",
                "email": user_data.get("email"),
                "role": user_data.get("role"),
                "is_active": bool(user_data.get("is_active"))
            }
            
            # Create a new session
            self._create_session(user_data.get("id"), "127.0.0.1")
            
            # Update last login time
            self.db.execute_query(
                "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
                (user_data.get("id"),),
                commit=True
            )
            
            logger.info(f"Auto-login as default user: {user_data.get('username')}")
            return True
            
        except Exception as e:
            logger.error(f"Error auto-logging in as default user: {e}")
            return False