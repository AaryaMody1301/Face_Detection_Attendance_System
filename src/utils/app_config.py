"""
Application Configuration for Face Detection Attendance System

This module provides a centralized way to manage application configuration
settings from different sources (JSON file, environment variables, etc.)
"""
import os
import json
import logging
import threading
from pathlib import Path
from typing import Dict, Any, Optional, Union, List, TypeVar, cast
from dataclasses import dataclass, field
import dotenv
import datetime

from .exceptions import ConfigError

# Load environment variables from .env file
dotenv.load_dotenv()

# Type variable for generic type hinting
T = TypeVar('T')

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class AppConfig:
    """
    Application Configuration class for managing settings
    
    Attributes:
        config_path: Path to the configuration file
        _config: Dictionary of configuration settings
        _initialized: Whether the configuration has been initialized
    """
    
    # Class-level variable for singleton pattern
    _instance = None
    _lock = threading.Lock()
    
    # Default configuration path
    config_path: str = field(default=None)
    
    # Dictionary for configuration settings
    _config: Dict[str, Any] = field(default_factory=dict)
    
    # Flag for initialized state
    _initialized: bool = field(default=False)
    
    # Secret keys that shouldn't be logged
    _secret_keys: List[str] = field(default_factory=list)
    
    def __new__(cls, config_path: Optional[str] = None):
        """Implement singleton pattern"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(AppConfig, cls).__new__(cls)
                cls._instance._init(config_path)
            elif config_path is not None and cls._instance.config_path != config_path:
                # If a different config path is specified, reload with the new path
                cls._instance._init(config_path)
            return cls._instance
    
    def _init(self, config_path: Optional[str] = None):
        """Initialize configuration settings"""
        if self._initialized and config_path is None:
            return
            
        # Set config path
        if config_path is not None:
            self.config_path = config_path
        elif self.config_path is None:
            # Use default path based on project root
            self.config_path = os.path.join(self._get_project_root(), "config", "config.json")
            
        # Initialize secret keys list
        self._secret_keys = [
            "database.password", 
            "email.password",
            "aws_secret_key",
            "api_key",
            "jwt_secret",
            "credentials"
        ]
            
        # Load configuration
        self._load_config()
        
        # Load environment variables
        self._load_env_variables()
        
        # Mark as initialized
        self._initialized = True
        
        logger.info(f"AppConfig initialized with config file: {self.config_path}")
    
    def _get_project_root(self) -> str:
        """Get the project root directory"""
        # Start with the location of this file and go up until finding the project root
        current_path = Path(__file__).resolve().parent
        
        # Go up the directory tree until we find the project root (where main.py is located)
        while not (current_path / "main.py").exists() and current_path != current_path.parent:
            current_path = current_path.parent
            
        if not (current_path / "main.py").exists():
            # Fallback to the current working directory
            return os.getcwd()
            
        return str(current_path)
    
    def _load_config(self):
        """Load configuration from file"""
        try:
            # Create default configuration if it doesn't exist
            if not os.path.exists(self.config_path):
                self._create_default_config()
                
            # Load configuration from file
            with open(self.config_path, 'r') as f:
                self._config = json.load(f)
                
            logger.info(f"Configuration loaded from {self.config_path}")
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            
            # Use default configuration if loading fails
            self._create_default_config(use_as_fallback=True)
    
    def _create_default_config(self, use_as_fallback: bool = False):
        """
        Create default configuration file
        
        Args:
            use_as_fallback: Whether to use the default configuration as a fallback
                            without writing to file
        """
        # Define default configuration
        default_config = {
            "app_name": "Face Detection Attendance System",
            "version": "1.0.0",
            "environment": "development",
            "log_level": "INFO",
            "database": {
                "path": "Data/attendance.db",
                "pool_size": 5,
                "backup_dir": "backups/data_backup"
            },
            "camera": {
                "id": 0,
                "resolution": [640, 480],
                "fps": 30,
                "flip_image": False
            },
            "face_detection": {
                "confidence_threshold": 65,
                "recognition_buffer_size": 5,
                "min_recognized_frames": 3,
                "show_recognition_confidence": True,
                "show_bounding_box": True,
                "late_threshold_seconds": 300
            },
            "training": {
                "images_directory": "TrainingImage",
                "labels_directory": "TrainingImageLabel",
                "samples_per_person": 20,
                "augment_data": True,
                "model_type": "standard"
            },
            "attendance": {
                "directory": "Attendance",
                "backup_directory": "backups/attendance_backup",
                "default_subject": "Python",
                "auto_export": False,
                "export_format": "csv",
                "duplicate_action": "update"
            },
            "ui": {
                "theme": "system",
                "font_family": "Helvetica",
                "title_font_size": 16,
                "normal_font_size": 12,
                "window_width": 1280,
                "window_height": 720,
                "fullscreen": False,
                "show_status_bar": True,
                "show_toolbar": True,
                "confirm_exit": True
            },
            "security": {
                "require_login": False,
                "session_timeout_minutes": 30,
                "max_login_attempts": 5,
                "jwt_expiry_days": 7
            }
        }
        
        # Use default configuration
        if use_as_fallback:
            self._config = default_config
            logger.warning("Using default configuration as fallback")
            return
            
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            # Write default configuration to file
            with open(self.config_path, 'w') as f:
                json.dump(default_config, f, indent=4)
                
            # Use default configuration
            self._config = default_config
            
            logger.info(f"Default configuration created at {self.config_path}")
        except Exception as e:
            logger.error(f"Error creating default configuration: {e}")
            self._config = default_config
    
    def _load_env_variables(self):
        """
        Load configuration from environment variables
        
        Environment variables should be
        """
        # Implementation can be added later if needed
        pass
        
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get a configuration value by its key path
        
        Args:
            key_path: Dot-separated path to the configuration key (e.g. "database.path")
            default: Default value to return if the key doesn't exist
            
        Returns:
            The configuration value or default if not found
        """
        try:
            # Split the key path into parts
            keys = key_path.split('.')
            
            # Start with the root config
            value = self._config
            
            # Navigate through the nested dictionary
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return default
                    
            return value
        except Exception as e:
            logger.error(f"Error accessing configuration key '{key_path}': {e}")
            return default