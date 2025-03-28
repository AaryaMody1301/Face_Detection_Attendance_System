"""
Application configuration management with secure environment variable handling
"""
import os
import json
import logging
import datetime
from pathlib import Path
from typing import Any, Dict, Optional, List, Union

from .env_manager import env_manager
from .exceptions import ConfigurationError

# Configure logging
logger = logging.getLogger(__name__)

class AppConfig:
    """
    Application configuration manager
    
    Manages application configuration with support for environment variables,
    config files, and in-memory settings with proper security handling.
    
    Attributes:
        config_path: Path to the configuration file
        config: The loaded configuration
    """
    
    def __init__(self, config_path: str = "config/config.json"):
        """
        Initialize app configuration
        
        Args:
            config_path: Path to the configuration file
        """
        self.config_path = config_path
        self.config = {}
        self.env_prefix = "FACE_ATTENDANCE_"
        
        # Load configuration
        self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file with environment variable overrides
        
        Returns:
            The loaded configuration
        """
        try:
            # Start with default configuration
            self.config = self._get_default_config()
            
            # Load from file if exists
            config_file = Path(self.config_path)
            if config_file.exists():
                with open(config_file, 'r') as file:
                    file_config = json.load(file)
                    self._merge_config(self.config, file_config)
                    logger.info(f"Loaded configuration from {self.config_path}")
                    
            # Override with environment variables
            self._load_env_overrides()
            
            return self.config
            
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            # Return defaults if loading fails
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """
        Get default configuration
        
        Returns:
            Default configuration
        """
        return {
            "app": {
                "name": "Face Detection Attendance System",
                "version": "2.0.0"
            },
            "ui": {
                "theme": "system",  # "system", "light", "dark"
                "color_theme": "blue",
                "window_width": 1280,
                "window_height": 720,
                "fullscreen": False,
                "scaling_factor": 1.0
            },
            "database": {
                "path": "Data/attendance.db",
                "backup_dir": "backups/data_backup",
                "pool_size": 5,
                "optimize_interval": 24  # hours
            },
            "camera": {
                "id": 0,
                "resolution": [640, 480],
                "fps": 30,
                "flip_image": False,
                "face_detection_interval": 0.5  # seconds
            },
            "face_recognition": {
                "model": "default",
                "confidence_threshold": 0.65,
                "training_images_dir": "TrainingImage",
                "recognition_algorithm": "LBPH",  # "LBPH", "Eigenfaces", "Fisherfaces"
                "batch_processing": True,
                "use_gpu": False
            },
            "attendance": {
                "session_timeout": 30,  # minutes
                "same_person_cooldown": 120,  # seconds
                "backup_dir": "backups/attendance_backup",
                "backup_interval": 24  # hours
            },
            "security": {
                "password_min_length": 8,
                "require_special_chars": True,
                "session_timeout": 30,  # minutes
                "max_login_attempts": 5,
                "use_encryption": True
            },
            "logging": {
                "level": "INFO",
                "file": "logs/app.log",
                "max_size": 10485760,  # 10 MB
                "backup_count": 5
            },
            "memory": {
                "auto_gc": True,
                "gc_interval": 60  # seconds
            }
        }
    
    def _merge_config(self, base: Dict[str, Any], override: Dict[str, Any]) -> None:
        """
        Merge configuration dictionaries
        
        Args:
            base: Base configuration
            override: Override configuration
        """
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value
    
    def _load_env_overrides(self) -> None:
        """
        Load configuration overrides from environment variables
        
        Environment variables should be prefixed with FACE_ATTENDANCE_
        and use double underscore as separator for nested keys:
        FACE_ATTENDANCE_UI__THEME=dark
        """
        # Get all environment variables with the prefix
        for key, value in os.environ.items():
            if key.startswith(self.env_prefix):
                # Remove prefix
                key = key[len(self.env_prefix):]
                
                # Handle nested keys (separated by double underscore)
                parts = key.split('__')
                
                # Convert value
                try:
                    # Try to parse as JSON
                    value = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    # Keep as string
                    pass
                
                # Update config
                current = self.config
                for part in parts[:-1]:
                    if part.lower() not in current:
                        current[part.lower()] = {}
                    current = current[part.lower()]
                
                # Set value
                current[parts[-1].lower()] = value
    
    def get(self, path: str, default: Any = None) -> Any:
        """
        Get a configuration value by path
        
        Args:
            path: Path to the configuration value (dot notation)
            default: Default value if not found
            
        Returns:
            The configuration value
        """
        try:
            parts = path.split('.')
            value = self.config
            
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return default
            
            return value
            
        except Exception as e:
            logger.warning(f"Error getting configuration value for {path}: {e}")
            return default
    
    def set(self, path: str, value: Any) -> bool:
        """
        Set a configuration value by path
        
        Args:
            path: Path to the configuration value (dot notation)
            value: Value to set
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            parts = path.split('.')
            config = self.config
            
            # Navigate to the parent element
            for part in parts[:-1]:
                if part not in config:
                    config[part] = {}
                config = config[part]
            
            # Set the value
            config[parts[-1]] = value
            
            # Save to file
            return self.save_config()
            
        except Exception as e:
            logger.error(f"Error setting configuration value for {path}: {e}")
            return False
    
    def save_config(self) -> bool:
        """
        Save configuration to file
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create directory if it doesn't exist
            config_file = Path(self.config_path)
            config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write to file
            with open(config_file, 'w') as file:
                json.dump(self.config, file, indent=4)
                
            logger.info(f"Configuration saved to {self.config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving configuration to {self.config_path}: {e}")
            return False
    
    def get_database_config(self) -> Dict[str, Any]:
        """
        Get database configuration with environment variable overrides
        
        Returns:
            Database configuration
        """
        # Get base configuration
        config = self.get('database', {})
        
        # Override with environment variables
        db_path = env_manager.get("FACE_ATTENDANCE_DB_PATH", config.get('path'))
        if db_path:
            config['path'] = db_path
        
        pool_size = env_manager.get_int("FACE_ATTENDANCE_DB_POOL_SIZE", config.get('pool_size'))
        if pool_size is not None:
            config['pool_size'] = pool_size
        
        return config
    
    def get_security_config(self) -> Dict[str, Any]:
        """
        Get security configuration with environment variable overrides
        
        Returns:
            Security configuration
        """
        # Get base configuration
        config = self.get('security', {})
        
        # Override with environment variables
        use_encryption = env_manager.get_bool("FACE_ATTENDANCE_USE_ENCRYPTION", config.get('use_encryption'))
        if use_encryption is not None:
            config['use_encryption'] = use_encryption
        
        return config
    
    def get_camera_config(self) -> Dict[str, Any]:
        """
        Get camera configuration
        
        Returns:
            Camera configuration
        """
        return self.get('camera', {})
    
    def get_face_recognition_config(self) -> Dict[str, Any]:
        """
        Get face recognition configuration
        
        Returns:
            Face recognition configuration
        """
        # Get base configuration
        config = self.get('face_recognition', {})
        
        # Override with environment variables
        threshold = env_manager.get_float("FACE_ATTENDANCE_RECOGNITION_THRESHOLD", 
                                       config.get('confidence_threshold'))
        if threshold is not None:
            config['confidence_threshold'] = threshold
        
        use_gpu = env_manager.get_bool("FACE_ATTENDANCE_USE_GPU", config.get('use_gpu'))
        if use_gpu is not None:
            config['use_gpu'] = use_gpu
        
        return config