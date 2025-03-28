"""
Environment Manager for the Face Detection Attendance System

This module provides a centralized way to manage environment variables
and dotenv files for the application.
"""
import os
import logging
from typing import Dict, Any, Optional, Union
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

class EnvManager:
    """
    Environment Manager for handling environment variables and .env files
    
    Attributes:
        env_file: Path to the environment file
        _env_vars: Dictionary of environment variables loaded from .env file
    """
    
    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize environment manager
        
        Args:
            env_file: Path to the environment file (default: .env in project root)
        """
        # Set default .env file path if not provided
        self.env_file = env_file or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
        
        # Dictionary to store environment variables loaded from .env
        self._env_vars = {}
        
        # Load environment variables from .env file
        self._load_env_file()
        
    def _load_env_file(self):
        """Load environment variables from .env file"""
        if not os.path.exists(self.env_file):
            logger.debug(f"Environment file not found: {self.env_file}")
            return
            
        try:
            with open(self.env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse key-value pair
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        
                        # Store in environment dictionary
                        self._env_vars[key] = value
                        
                        # Set environment variable if not already set
                        if key not in os.environ:
                            os.environ[key] = value
            
            logger.debug(f"Loaded environment variables from {self.env_file}")
            
        except Exception as e:
            logger.error(f"Error loading environment file: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get environment variable
        
        Args:
            key: Environment variable name
            default: Default value if not found
            
        Returns:
            Environment variable value or default
        """
        # Check OS environment first
        value = os.environ.get(key)
        
        # Fall back to .env file
        if value is None:
            value = self._env_vars.get(key)
        
        # Return value or default
        return value if value is not None else default
    
    def set(self, key: str, value: str, persist: bool = False):
        """
        Set environment variable
        
        Args:
            key: Environment variable name
            value: Environment variable value
            persist: Whether to save to .env file
        """
        # Set in OS environment
        os.environ[key] = value
        
        # Set in internal dictionary
        self._env_vars[key] = value
        
        # Save to .env file if requested
        if persist:
            self._save_to_env_file()
    
    def _save_to_env_file(self):
        """Save environment variables to .env file"""
        try:
            # Read existing file if it exists
            lines = []
            existing_keys = set()
            
            if os.path.exists(self.env_file):
                with open(self.env_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        
                        # Keep comments and empty lines
                        if not line or line.startswith('#'):
                            lines.append(line)
                            continue
                        
                        # Parse key for existing variables
                        if '=' in line:
                            key = line.split('=', 1)[0].strip()
                            existing_keys.add(key)
                            
                            # Replace line if key is in our dictionary
                            if key in self._env_vars:
                                lines.append(f"{key}={self._env_vars[key]}")
                                continue
                        
                        # Keep line as is
                        lines.append(line)
            
            # Add new variables that weren't in the file
            for key, value in self._env_vars.items():
                if key not in existing_keys:
                    lines.append(f"{key}={value}")
            
            # Write back to file
            os.makedirs(os.path.dirname(self.env_file), exist_ok=True)
            with open(self.env_file, 'w') as f:
                f.write('\n'.join(lines))
            
            logger.debug(f"Saved environment variables to {self.env_file}")
            
        except Exception as e:
            logger.error(f"Error saving environment file: {e}")
    
    def delete(self, key: str, persist: bool = False):
        """
        Delete environment variable
        
        Args:
            key: Environment variable name
            persist: Whether to remove from .env file
        """
        # Remove from OS environment
        if key in os.environ:
            del os.environ[key]
        
        # Remove from internal dictionary
        if key in self._env_vars:
            del self._env_vars[key]
        
        # Remove from .env file if requested
        if persist:
            self._save_to_env_file()
    
    def get_all(self) -> Dict[str, str]:
        """
        Get all environment variables from .env file
        
        Returns:
            Dictionary of all environment variables from .env file
        """
        return self._env_vars.copy()
    
    def get_credential(self, key: str, default: Any = None) -> str:
        """
        Get credential from secure source
        
        Currently just uses environment variables, but could be extended
        to use a more secure credential store.
        
        Args:
            key: Credential key
            default: Default value if not found
            
        Returns:
            Credential value or default
        """
        # Prefix credential keys
        prefixed_key = f"FACE_APP_CRED_{key.upper()}"
        
        # Try to get credential
        return self.get(prefixed_key, default)
    
    def set_credential(self, key: str, value: str, persist: bool = False):
        """
        Set credential in secure source
        
        Args:
            key: Credential key
            value: Credential value
            persist: Whether to save to .env file
        """
        # Prefix credential keys
        prefixed_key = f"FACE_APP_CRED_{key.upper()}"
        
        # Set credential
        self.set(prefixed_key, value, persist)


# Create a singleton instance
env_manager = EnvManager()