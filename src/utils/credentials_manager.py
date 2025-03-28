"""
Utility for securely storing and retrieving credentials for the Face Detection Attendance System
"""
import os
import json
import base64
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class CredentialsManager:
    """
    Handles secure storage and retrieval of user credentials
    Uses simple encoding (not encryption) - suitable for convenience only, not high security
    """
    
    def __init__(self, config_dir="config"):
        """
        Initialize credentials manager
        
        Args:
            config_dir (str): Directory to store config files
        """
        self.config_dir = config_dir
        self.credentials_file = os.path.join(config_dir, "credentials.json")
        
        # Create config directory if it doesn't exist
        os.makedirs(config_dir, exist_ok=True)
    
    def save_credentials(self, username, password, remember=True):
        """
        Save credentials if remember is True
        
        Args:
            username (str): Username to save
            password (str): Password to save
            remember (bool): Whether to save credentials
        
        Returns:
            bool: True if saved successfully, False otherwise
        """
        try:
            if remember:
                # Simple encoding - not secure encryption
                encoded_password = base64.b64encode(password.encode()).decode()
                
                credentials = {
                    "username": username,
                    "password": encoded_password
                }
                
                with open(self.credentials_file, 'w') as f:
                    json.dump(credentials, f)
                
                logger.info(f"Saved credentials for user: {username}")
            else:
                # If remember is False, delete any existing credentials
                self.clear_credentials()
                
            return True
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")
            return False
    
    def load_credentials(self):
        """
        Load saved credentials if available
        
        Returns:
            tuple: (username, password) if available, (None, None) otherwise
        """
        try:
            if os.path.exists(self.credentials_file):
                with open(self.credentials_file, 'r') as f:
                    credentials = json.load(f)
                
                username = credentials.get("username")
                encoded_password = credentials.get("password")
                
                if username and encoded_password:
                    # Decode password
                    password = base64.b64decode(encoded_password.encode()).decode()
                    logger.info(f"Loaded credentials for user: {username}")
                    return username, password
            
            return None, None
        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")
            return None, None
    
    def clear_credentials(self):
        """
        Clear saved credentials
        
        Returns:
            bool: True if cleared successfully, False otherwise
        """
        try:
            if os.path.exists(self.credentials_file):
                os.remove(self.credentials_file)
                logger.info("Cleared saved credentials")
            return True
        except Exception as e:
            logger.error(f"Failed to clear credentials: {e}")
            return False
    
    def has_saved_credentials(self):
        """
        Check if saved credentials exist
        
        Returns:
            bool: True if credentials exist, False otherwise
        """
        return os.path.exists(self.credentials_file)