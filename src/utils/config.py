"""
Configuration manager for the Face Detection Attendance System

This module provides a centralized configuration system for the application
with support for loading from JSON files, environment variables, and default values.
"""

import os
import json
from pathlib import Path
from typing import Any, Dict, Optional, Union, List
from .exceptions import ConfigurationError
from .logger import get_logger

# Get a logger specifically for the configuration module
logger = get_logger("config")

class ConfigManager:
    """
    Configuration manager for the Face Detection Attendance System
    
    Handles loading, validating, and providing access to application settings.
    """
    
    # Default configuration values
    DEFAULT_CONFIG = {
        "app": {
            "name": "Face Detection Attendance System",
            "version": "1.0.0",
            "debug_mode": False,
        },
        "camera": {
            "default_camera_id": 0,
            "frame_width": 640,
            "frame_height": 480,
            "face_cascade_path": "haarcascade_frontalface_default.xml",
        },
        "face_recognition": {
            "confidence_threshold": 80,
            "training_images_per_person": 100,
            "recognition_algorithm": "LBPH",  # Options: LBPH, Eigenfaces, Fisherfaces
            "use_gpu": False,
        },
        "database": {
            "type": "sqlite",
            "path": "Data/attendance.db",
        },
        "paths": {
            "training_images": "TrainingImage",
            "training_labels": "TrainingImageLabel",
            "attendance": "Attendance",
            "student_details": "StudentDetails/StudentDetails.csv",
            "backup_dir": "backups",
            "logs_dir": "logs",
        },
        "attendance": {
            "auto_backup_enabled": True,
            "auto_export_csv": True,
            "duplicate_entry_threshold_minutes": 30,
            "record_entry_exit": False,  # Record both entry and exit times
        },
        "ui": {
            "theme": "light",  # Options: light, dark, system
            "language": "en",  # ISO language code
            "font_size": "medium",  # Options: small, medium, large
            "enable_animations": True,
        },
        "security": {
            "require_login": False,
            "password_hash_algorithm": "bcrypt",
            "admin_password_hash": "",  # Should be overridden by actual config
            "session_timeout_minutes": 30,
        }
    }
    
    def __init__(self, config_file: str = "config/config.json"):
        """
        Initialize configuration manager
        
        Args:
            config_file: Path to the configuration file (relative to application root)
        """
        self.config_file = config_file
        self.config = None
        self.load_config()
    
    def load_config(self) -> None:
        """
        Load configuration from file, environment variables, and defaults
        
        Raises:
            ConfigurationError: If the configuration file cannot be loaded
        """
        try:
            # Start with default configuration
            self.config = self.DEFAULT_CONFIG.copy()
            
            # Try to load configuration file
            config_path = Path(self.config_file)
            if config_path.exists():
                with open(config_path, 'r') as f:
                    loaded_config = json.load(f)
                
                # Update default config with loaded values
                self._update_nested_dict(self.config, loaded_config)
                logger.info(f"Configuration loaded from {self.config_file}")
            else:
                logger.warning(f"Configuration file {self.config_file} not found, using defaults")
                
                # Create config directory if it doesn't exist
                config_dir = config_path.parent
                if not config_dir.exists():
                    config_dir.mkdir(parents=True, exist_ok=True)
                
                # Create default config file
                with open(config_path, 'w') as f:
                    json.dump(self.config, f, indent=4)
                
                logger.info(f"Created default configuration file at {self.config_file}")
            
            # Override with environment variables
            self._override_with_env_vars()
            
        except Exception as e:
            logger.error("Failed to load configuration", exception=e)
            raise ConfigurationError(f"Failed to load configuration: {str(e)}") from e
    
    def save_config(self) -> None:
        """
        Save current configuration to file
        
        Raises:
            ConfigurationError: If the configuration cannot be saved
        """
        try:
            config_path = Path(self.config_file)
            
            # Ensure directory exists
            config_dir = config_path.parent
            if not config_dir.exists():
                config_dir.mkdir(parents=True, exist_ok=True)
            
            with open(config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
            
            logger.info(f"Configuration saved to {self.config_file}")
        
        except Exception as e:
            logger.error("Failed to save configuration", exception=e)
            raise ConfigurationError(f"Failed to save configuration: {str(e)}") from e
    
    def get(self, section: str, key: str = None, default: Any = None) -> Any:
        """
        Get configuration value
        
        Args:
            section: Configuration section name
            key: Configuration key name (None to get entire section)
            default: Default value if key doesn't exist
            
        Returns:
            Configuration value or default
        """
        if self.config is None:
            self.load_config()
        
        try:
            if key is None:
                return self.config.get(section, default)
            return self.config.get(section, {}).get(key, default)
        except Exception as e:
            logger.error(f"Error accessing config [{section}][{key}]", exception=e)
            return default
    
    def set(self, section: str, key: str, value: Any, save: bool = True) -> None:
        """
        Set configuration value
        
        Args:
            section: Configuration section name
            key: Configuration key name
            value: New value to set
            save: Whether to save configuration to file immediately
            
        Raises:
            ConfigurationError: If the section doesn't exist
        """
        if self.config is None:
            self.load_config()
        
        # Ensure section exists
        if section not in self.config:
            raise ConfigurationError(f"Configuration section '{section}' doesn't exist")
        
        # Set value
        self.config[section][key] = value
        logger.debug(f"Set config [{section}][{key}] = {value}")
        
        # Save configuration if requested
        if save:
            self.save_config()
    
    def get_absolute_path(self, section: str, key: str, default: str = None) -> str:
        """
        Get an absolute path from a configuration value
        
        Converts relative paths to absolute paths based on the application root directory.
        
        Args:
            section: Configuration section name
            key: Configuration key name
            default: Default value if key doesn't exist
            
        Returns:
            Absolute path as a string
        """
        path_str = self.get(section, key, default)
        if not path_str:
            return None
        
        path = Path(path_str)
        if path.is_absolute():
            return str(path)
        
        # Get application root directory (parent of config directory)
        app_root = Path(self.config_file).parent.parent
        return str(app_root / path)
    
    def create_paths(self) -> None:
        """
        Create all required directories from paths configuration
        
        Creates any directories specified in the paths section that don't exist.
        """
        paths = self.get("paths", None)
        if not paths:
            return
        
        for key, path_str in paths.items():
            if not path_str:
                continue
            
            try:
                path = Path(path_str)
                if not path.is_absolute():
                    # Get application root directory
                    app_root = Path(self.config_file).parent.parent
                    path = app_root / path
                
                # Only create if it looks like a directory (not a file path)
                if not path.suffix and not path.exists():
                    path.mkdir(parents=True, exist_ok=True)
                    logger.debug(f"Created directory: {path}")
            
            except Exception as e:
                logger.error(f"Failed to create directory: {path_str}", exception=e)
    
    def _update_nested_dict(self, target: Dict, source: Dict) -> None:
        """
        Update a nested dictionary recursively
        
        Args:
            target: Target dictionary to update
            source: Source dictionary with new values
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                # If both target and source have dict at this key, recurse
                self._update_nested_dict(target[key], value)
            else:
                # Otherwise overwrite/set the value
                target[key] = value
    
    def _override_with_env_vars(self) -> None:
        """
        Override configuration with environment variables
        
        Environment variables should be named like:
        FACEATTENDANCE_SECTION_KEY=value
        """
        prefix = "FACEATTENDANCE_"
        for env_name, env_value in os.environ.items():
            if env_name.startswith(prefix):
                # Remove prefix and split by underscore
                parts = env_name[len(prefix):].split("_", 1)
                
                if len(parts) == 2:
                    section, key = parts
                    section = section.lower()
                    key = key.lower()
                    
                    # Only override if section and key exist in config
                    if section in self.config and key in self.config[section]:
                        # Try to parse value based on the existing value's type
                        existing_value = self.config[section][key]
                        
                        if isinstance(existing_value, bool):
                            value = env_value.lower() in ('true', 'yes', '1', 'y')
                        elif isinstance(existing_value, int):
                            value = int(env_value)
                        elif isinstance(existing_value, float):
                            value = float(env_value)
                        else:
                            value = env_value
                        
                        self.config[section][key] = value
                        logger.debug(f"Overrode config [{section}][{key}] with environment variable {env_name}")


# Create a global instance of the configuration manager
config_manager = ConfigManager()

# Function for easily accessing configuration
def get_config(section: str, key: str = None, default: Any = None) -> Any:
    """
    Get configuration value
    
    Args:
        section: Configuration section name
        key: Configuration key name (None to get entire section)
        default: Default value if key doesn't exist
        
    Returns:
        Configuration value or default
    """
    return config_manager.get(section, key, default)