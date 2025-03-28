"""
Environment variable manager for secure credential handling
"""
import os
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional
import dotenv

from .exceptions import ConfigurationError

# Configure logging
logger = logging.getLogger(__name__)

class EnvManager:
    """
    Manages environment variables and secure configuration settings
    
    This class handles loading configuration from environment variables,
    with fallback to a .env file and default values.
    """
    
    def __init__(self, env_file: str = ".env"):
        """
        Initialize the environment manager
        
        Args:
            env_file: Path to the .env file
        """
        self.env_file = env_file
        self._config_cache = {}
        
        # Load environment variables from .env file if it exists
        env_path = Path(env_file)
        if env_path.exists():
            dotenv.load_dotenv(env_file)
            logger.info(f"Loaded environment variables from {env_file}")
        else:
            logger.warning(f"Environment file {env_file} not found, using system environment variables")
    
    def get(self, key: str, default: Any = None, required: bool = False) -> Any:
        """
        Get a configuration value from environment variables
        
        Args:
            key: The configuration key
            default: Default value if not found
            required: Whether the configuration is required
            
        Returns:
            The configuration value
            
        Raises:
            ConfigurationError: If required configuration is missing
        """
        # Check cache first
        if key in self._config_cache:
            return self._config_cache[key]
        
        # Try to get from environment
        value = os.environ.get(key)
        
        # Handle missing required value
        if value is None and required and default is None:
            error_msg = f"Required configuration '{key}' is missing"
            logger.error(error_msg)
            raise ConfigurationError(error_msg)
        
        # Use default if not found
        if value is None:
            value = default
        
        # Parse JSON values
        if isinstance(value, str) and value.startswith('{') and value.endswith('}'):
            try:
                value = json.loads(value)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON value for key '{key}': {e}")
        
        # Cache for future use
        self._config_cache[key] = value
        
        return value
    
    def get_int(self, key: str, default: Optional[int] = None, 
               required: bool = False) -> Optional[int]:
        """
        Get an integer configuration value
        
        Args:
            key: The configuration key
            default: Default value if not found
            required: Whether the configuration is required
            
        Returns:
            The configuration value as an integer
            
        Raises:
            ConfigurationError: If required configuration is missing or not an integer
        """
        value = self.get(key, default, required)
        
        if value is None:
            return None
            
        try:
            return int(value)
        except (ValueError, TypeError) as e:
            error_msg = f"Configuration '{key}' value '{value}' is not a valid integer"
            logger.error(error_msg)
            raise ConfigurationError(error_msg) from e
    
    def get_float(self, key: str, default: Optional[float] = None, 
                required: bool = False) -> Optional[float]:
        """
        Get a float configuration value
        
        Args:
            key: The configuration key
            default: Default value if not found
            required: Whether the configuration is required
            
        Returns:
            The configuration value as a float
            
        Raises:
            ConfigurationError: If required configuration is missing or not a float
        """
        value = self.get(key, default, required)
        
        if value is None:
            return None
            
        try:
            return float(value)
        except (ValueError, TypeError) as e:
            error_msg = f"Configuration '{key}' value '{value}' is not a valid float"
            logger.error(error_msg)
            raise ConfigurationError(error_msg) from e
    
    def get_bool(self, key: str, default: Optional[bool] = None, 
               required: bool = False) -> Optional[bool]:
        """
        Get a boolean configuration value
        
        Args:
            key: The configuration key
            default: Default value if not found
            required: Whether the configuration is required
            
        Returns:
            The configuration value as a boolean
            
        Raises:
            ConfigurationError: If required configuration is missing
        """
        value = self.get(key, default, required)
        
        if value is None:
            return None
            
        if isinstance(value, bool):
            return value
            
        if isinstance(value, (int, float)):
            return bool(value)
            
        if isinstance(value, str):
            value = value.lower()
            if value in ('true', 'yes', '1', 'y'):
                return True
            if value in ('false', 'no', '0', 'n'):
                return False
        
        error_msg = f"Configuration '{key}' value '{value}' is not a valid boolean"
        logger.error(error_msg)
        raise ConfigurationError(error_msg)
    
    def get_list(self, key: str, default: Optional[list] = None, 
               required: bool = False, delimiter: str = ',') -> Optional[list]:
        """
        Get a list configuration value
        
        Args:
            key: The configuration key
            default: Default value if not found
            required: Whether the configuration is required
            delimiter: Delimiter for string values
            
        Returns:
            The configuration value as a list
            
        Raises:
            ConfigurationError: If required configuration is missing
        """
        value = self.get(key, default, required)
        
        if value is None:
            return None
            
        if isinstance(value, list):
            return value
            
        if isinstance(value, str):
            return [item.strip() for item in value.split(delimiter)]
            
        error_msg = f"Configuration '{key}' value '{value}' is not a valid list"
        logger.error(error_msg)
        raise ConfigurationError(error_msg)
    
    def set(self, key: str, value: Any) -> None:
        """
        Set an environment variable
        
        Args:
            key: The configuration key
            value: The configuration value
        """
        if value is None:
            # Unset the variable
            if key in os.environ:
                del os.environ[key]
            if key in self._config_cache:
                del self._config_cache[key]
            return
            
        # Convert to string if needed
        if not isinstance(value, str):
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            else:
                value = str(value)
        
        # Set in environment and cache
        os.environ[key] = value
        self._config_cache[key] = value
        
    def save_to_env_file(self) -> bool:
        """
        Save current environment variables to .env file
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create directory if it doesn't exist
            env_path = Path(self.env_file)
            env_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Load existing content
            existing_env = {}
            if env_path.exists():
                with open(env_path, 'r') as file:
                    for line in file:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            existing_env[key.strip()] = value.strip()
            
            # Update with cache values
            for key, value in self._config_cache.items():
                if value is not None:
                    if isinstance(value, (dict, list)):
                        existing_env[key] = json.dumps(value)
                    else:
                        existing_env[key] = str(value)
            
            # Write back to file
            with open(env_path, 'w') as file:
                for key, value in existing_env.items():
                    file.write(f"{key}={value}\n")
            
            logger.info(f"Environment variables saved to {self.env_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save environment variables to {self.env_file}: {e}")
            return False


# Create a singleton instance
env_manager = EnvManager()