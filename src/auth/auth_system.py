"""
Authentication system for the Face Detection Attendance System
"""
import os
import hashlib
import datetime
import logging
import sqlite3
import secrets
import string
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

class AuthenticationSystem:
    """
    Authentication system for user login and session management
    """
    
    def __init__(self, db_path=None):
        """
        Initialize the authentication system
        
        Args:
            db_path (str, optional): Path to SQLite database file
        """
        if db_path is None:
            # Use default path
            data_dir = os.path.join(".", "Data")
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, "attendance.db")
        
        self.db_path = db_path
        self._initialize_database()
        self.current_user = None
        self.session_token = None
    
    def _initialize_database(self):
        """Initialize user tables in the database if they don't exist"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create Users table if it doesn't exist
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS Users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE,
                password_hash TEXT,
                salt TEXT,
                role TEXT,
                full_name TEXT,
                email TEXT,
                created_date TEXT,
                last_login TEXT,
                is_active INTEGER DEFAULT 1
            )
            ''')
            
            # Create Sessions table for tracking user sessions
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS Sessions (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                token TEXT UNIQUE,
                created_at TEXT,
                expires_at TEXT,
                ip_address TEXT,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES Users(id)
            )
            ''')
            
            # Create LoginAttempts table for tracking failed login attempts
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS LoginAttempts (
                id INTEGER PRIMARY KEY,
                username TEXT,
                ip_address TEXT,
                attempt_time TEXT,
                success INTEGER
            )
            ''')
            
            # Create default admin user if no users exist
            cursor.execute("SELECT COUNT(*) FROM Users")
            if cursor.fetchone()[0] == 0:
                self.create_user(
                    username="admin",
                    password="admin",
                    role="admin",
                    full_name="System Administrator",
                    email="admin@example.com"
                )
                logger.info("Created default admin user")
            
            conn.commit()
            conn.close()
            logger.info("Authentication database initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing authentication database: {e}")
    
    def create_user(self, username, password, role="user", full_name=None, email=None):
        """
        Create a new user
        
        Args:
            username (str): Username for the new user
            password (str): Password for the new user
            role (str, optional): User role (admin, teacher, user)
            full_name (str, optional): User's full name
            email (str, optional): User's email address
            
        Returns:
            bool: True if user was created successfully
        """
        try:
            # Generate a random salt
            salt = self._generate_salt()
            
            # Hash the password with the salt
            password_hash = self._hash_password(password, salt)
            
            # Get current timestamp
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Connect to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if username already exists
            cursor.execute("SELECT id FROM Users WHERE username = ?", (username,))
            if cursor.fetchone():
                logger.warning(f"Username '{username}' already exists")
                conn.close()
                return False
            
            # Insert new user
            cursor.execute(
                """
                INSERT INTO Users 
                (username, password_hash, salt, role, full_name, email, created_date) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (username, password_hash, salt, role, full_name, email, now)
            )
            
            conn.commit()
            conn.close()
            logger.info(f"User '{username}' created successfully")
            return True
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return False
    
    def authenticate(self, username, password, ip_address=None):
        """
        Authenticate a user
        
        Args:
            username (str): Username
            password (str): Password
            ip_address (str, optional): IP address of the client
            
        Returns:
            dict: User information if authentication is successful, None otherwise
        """
        try:
            # Connect to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get user record
            cursor.execute(
                "SELECT id, username, password_hash, salt, role, full_name, email FROM Users WHERE username = ? AND is_active = 1",
                (username,)
            )
            user_record = cursor.fetchone()
            
            # Record login attempt
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            success = 0
            
            if user_record:
                user_id, db_username, db_password_hash, salt, role, full_name, email = user_record
                
                # Hash the provided password with the stored salt
                password_hash = self._hash_password(password, salt)
                
                # Compare password hashes
                if password_hash == db_password_hash:
                    # Authentication successful
                    success = 1
                    
                    # Create user session
                    session_token = self._generate_session_token()
                    expires_at = (datetime.datetime.now() + datetime.timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Store session
                    cursor.execute(
                        """
                        INSERT INTO Sessions 
                        (user_id, token, created_at, expires_at, ip_address) 
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (user_id, session_token, now, expires_at, ip_address)
                    )
                    
                    # Update last login time
                    cursor.execute(
                        "UPDATE Users SET last_login = ? WHERE id = ?",
                        (now, user_id)
                    )
                    
                    conn.commit()
                    
                    # Store current session
                    self.current_user = {
                        'id': user_id,
                        'username': db_username,
                        'role': role,
                        'full_name': full_name,
                        'email': email
                    }
                    self.session_token = session_token
                    
                    logger.info(f"User '{username}' authenticated successfully")
                    
                    # Return user info
                    user_info = self.current_user.copy()
                    conn.close()
                    return user_info
            
            # Record failed login attempt
            cursor.execute(
                """
                INSERT INTO LoginAttempts 
                (username, ip_address, attempt_time, success) 
                VALUES (?, ?, ?, ?)
                """,
                (username, ip_address, now, success)
            )
            conn.commit()
            conn.close()
            
            # Check for brute force attacks
            if ip_address:
                self._check_for_brute_force(username, ip_address)
            
            logger.warning(f"Failed authentication attempt for username '{username}'")
            return None
        except Exception as e:
            logger.error(f"Error during authentication: {e}")
            return None
    
    def validate_session(self, session_token):
        """
        Validate a session token
        
        Args:
            session_token (str): Session token to validate
            
        Returns:
            dict: User information if session is valid, None otherwise
        """
        try:
            # Connect to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get current timestamp
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Get session record
            cursor.execute(
                """
                SELECT s.id, s.user_id, s.expires_at, u.username, u.role, u.full_name, u.email
                FROM Sessions s
                JOIN Users u ON s.user_id = u.id
                WHERE s.token = ? AND s.is_active = 1 AND u.is_active = 1
                """,
                (session_token,)
            )
            session = cursor.fetchone()
            
            if not session:
                logger.warning(f"Invalid session token: {session_token}")
                conn.close()
                return None
            
            session_id, user_id, expires_at, username, role, full_name, email = session
            
            # Check if session has expired
            if expires_at < now:
                # Deactivate expired session
                cursor.execute(
                    "UPDATE Sessions SET is_active = 0 WHERE id = ?",
                    (session_id,)
                )
                conn.commit()
                conn.close()
                logger.warning(f"Session expired for user '{username}'")
                return None
            
            # Valid session, return user info
            user_info = {
                'id': user_id,
                'username': username,
                'role': role,
                'full_name': full_name,
                'email': email
            }
            
            # Store current session
            self.current_user = user_info
            self.session_token = session_token
            
            conn.close()
            return user_info
        except Exception as e:
            logger.error(f"Error validating session: {e}")
            return None
    
    def logout(self):
        """
        Logout the current user
        
        Returns:
            bool: True if logout was successful
        """
        try:
            if not self.session_token:
                logger.warning("No active session to logout")
                return False
            
            # Connect to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Deactivate the session
            cursor.execute(
                "UPDATE Sessions SET is_active = 0 WHERE token = ?",
                (self.session_token,)
            )
            
            conn.commit()
            conn.close()
            
            # Clear current session
            self.current_user = None
            self.session_token = None
            
            logger.info("User logged out successfully")
            return True
        except Exception as e:
            logger.error(f"Error during logout: {e}")
            return False
    
    def change_password(self, user_id, current_password, new_password):
        """
        Change a user's password
        
        Args:
            user_id (int): User ID
            current_password (str): Current password
            new_password (str): New password
            
        Returns:
            bool: True if password was changed successfully
        """
        try:
            # Connect to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get user record
            cursor.execute(
                "SELECT password_hash, salt FROM Users WHERE id = ? AND is_active = 1",
                (user_id,)
            )
            user_record = cursor.fetchone()
            
            if not user_record:
                logger.warning(f"User ID {user_id} not found or inactive")
                conn.close()
                return False
            
            db_password_hash, salt = user_record
            
            # Verify current password
            current_hash = self._hash_password(current_password, salt)
            if current_hash != db_password_hash:
                logger.warning(f"Current password verification failed for user ID {user_id}")
                conn.close()
                return False
            
            # Generate new salt and hash for the new password
            new_salt = self._generate_salt()
            new_hash = self._hash_password(new_password, new_salt)
            
            # Update password
            cursor.execute(
                "UPDATE Users SET password_hash = ?, salt = ? WHERE id = ?",
                (new_hash, new_salt, user_id)
            )
            
            # Invalidate all existing sessions for this user
            cursor.execute(
                "UPDATE Sessions SET is_active = 0 WHERE user_id = ?",
                (user_id,)
            )
            
            conn.commit()
            conn.close()
            
            # Clear current session if it's for this user
            if self.current_user and self.current_user['id'] == user_id:
                self.current_user = None
                self.session_token = None
            
            logger.info(f"Password changed successfully for user ID {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error changing password: {e}")
            return False
    
    def reset_password(self, username=None, user_id=None):
        """
        Reset a user's password to a random string
        
        Args:
            username (str, optional): Username
            user_id (int, optional): User ID
            
        Returns:
            str: New password if reset was successful, None otherwise
        """
        try:
            if not username and not user_id:
                logger.error("Username or user_id must be provided")
                return None
            
            # Connect to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get user record
            if username:
                cursor.execute(
                    "SELECT id FROM Users WHERE username = ? AND is_active = 1",
                    (username,)
                )
            else:
                cursor.execute(
                    "SELECT id FROM Users WHERE id = ? AND is_active = 1",
                    (user_id,)
                )
            
            user_record = cursor.fetchone()
            
            if not user_record:
                logger.warning(f"User not found or inactive")
                conn.close()
                return None
            
            user_id = user_record[0]
            
            # Generate new random password
            new_password = self._generate_random_password()
            
            # Generate new salt and hash
            new_salt = self._generate_salt()
            new_hash = self._hash_password(new_password, new_salt)
            
            # Update password
            cursor.execute(
                "UPDATE Users SET password_hash = ?, salt = ? WHERE id = ?",
                (new_hash, new_salt, user_id)
            )
            
            # Invalidate all existing sessions for this user
            cursor.execute(
                "UPDATE Sessions SET is_active = 0 WHERE user_id = ?",
                (user_id,)
            )
            
            conn.commit()
            conn.close()
            
            # Clear current session if it's for this user
            if self.current_user and self.current_user['id'] == user_id:
                self.current_user = None
                self.session_token = None
            
            logger.info(f"Password reset successfully for user ID {user_id}")
            return new_password
        except Exception as e:
            logger.error(f"Error resetting password: {e}")
            return None
    
    def update_user(self, user_id, role=None, full_name=None, email=None, is_active=None):
        """
        Update user information
        
        Args:
            user_id (int): User ID
            role (str, optional): New role
            full_name (str, optional): New full name
            email (str, optional): New email
            is_active (bool, optional): New active status
            
        Returns:
            bool: True if user was updated successfully
        """
        try:
            # Connect to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Build update query
            query_parts = []
            params = []
            
            if role is not None:
                query_parts.append("role = ?")
                params.append(role)
            
            if full_name is not None:
                query_parts.append("full_name = ?")
                params.append(full_name)
            
            if email is not None:
                query_parts.append("email = ?")
                params.append(email)
            
            if is_active is not None:
                query_parts.append("is_active = ?")
                params.append(1 if is_active else 0)
            
            if not query_parts:
                logger.warning("No fields provided for update")
                conn.close()
                return False
            
            # Add user_id to params
            params.append(user_id)
            
            # Execute update
            cursor.execute(
                f"UPDATE Users SET {', '.join(query_parts)} WHERE id = ?",
                params
            )
            
            # Check if any row was affected
            if cursor.rowcount == 0:
                logger.warning(f"User ID {user_id} not found")
                conn.close()
                return False
            
            conn.commit()
            conn.close()
            
            logger.info(f"User ID {user_id} updated successfully")
            return True
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            return False
    
    def get_users(self, active_only=True):
        """
        Get list of users
        
        Args:
            active_only (bool, optional): Only return active users
            
        Returns:
            list: List of user dictionaries
        """
        try:
            # Connect to database
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Return rows as dictionaries
            cursor = conn.cursor()
            
            # Build query
            query = """
            SELECT id, username, role, full_name, email, created_date, last_login, is_active
            FROM Users
            """
            
            if active_only:
                query += " WHERE is_active = 1"
            
            cursor.execute(query)
            rows = cursor.fetchall()
            
            # Convert to list of dictionaries
            users = [dict(row) for row in rows]
            
            conn.close()
            return users
        except Exception as e:
            logger.error(f"Error getting users: {e}")
            return []
    
    def delete_user(self, user_id):
        """
        Delete a user (soft delete by setting is_active to 0)
        
        Args:
            user_id (int): User ID
            
        Returns:
            bool: True if user was deleted successfully
        """
        try:
            # Connect to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Soft delete by setting is_active to 0
            cursor.execute(
                "UPDATE Users SET is_active = 0 WHERE id = ?",
                (user_id,)
            )
            
            # Check if any row was affected
            if cursor.rowcount == 0:
                logger.warning(f"User ID {user_id} not found")
                conn.close()
                return False
            
            # Invalidate all sessions for this user
            cursor.execute(
                "UPDATE Sessions SET is_active = 0 WHERE user_id = ?",
                (user_id,)
            )
            
            conn.commit()
            conn.close()
            
            # Clear current session if it's for this user
            if self.current_user and self.current_user['id'] == user_id:
                self.current_user = None
                self.session_token = None
            
            logger.info(f"User ID {user_id} deleted successfully")
            return True
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            return False
    
    def _hash_password(self, password, salt):
        """Hash a password with the given salt"""
        return hashlib.sha256((password + salt).encode()).hexdigest()
    
    def _generate_salt(self, length=16):
        """Generate a random salt for password hashing"""
        return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(length))
    
    def _generate_session_token(self, length=32):
        """Generate a random session token"""
        return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(length))
    
    def _generate_random_password(self, length=12):
        """Generate a random password"""
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(chars) for _ in range(length))
    
    def _check_for_brute_force(self, username, ip_address):
        """Check for potential brute force attacks"""
        try:
            # Connect to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check recent failed attempts for this username/IP
            one_hour_ago = (datetime.datetime.now() - datetime.timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
            
            # Count failed attempts by username
            cursor.execute(
                """
                SELECT COUNT(*) FROM LoginAttempts 
                WHERE username = ? AND success = 0 AND attempt_time > ?
                """,
                (username, one_hour_ago)
            )
            username_attempts = cursor.fetchone()[0]
            
            # Count failed attempts by IP
            cursor.execute(
                """
                SELECT COUNT(*) FROM LoginAttempts 
                WHERE ip_address = ? AND success = 0 AND attempt_time > ?
                """,
                (ip_address, one_hour_ago)
            )
            ip_attempts = cursor.fetchone()[0]
            
            conn.close()
            
            # Log potential brute force attacks
            if username_attempts >= 5:
                logger.warning(f"Potential brute force attack detected for username '{username}': {username_attempts} failed attempts in the last hour")
            
            if ip_attempts >= 10:
                logger.warning(f"Potential brute force attack detected from IP '{ip_address}': {ip_attempts} failed attempts in the last hour")
                
        except Exception as e:
            logger.error(f"Error checking for brute force attacks: {e}")
    
    def get_current_user(self):
        """
        Get the current authenticated user
        
        Returns:
            dict: Current user information, or None if no user is authenticated
        """
        return self.current_user