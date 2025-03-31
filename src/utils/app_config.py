"""
Application Configuration Management

This module provides a central location for managing application configuration settings.
"""
import os
import json
import logging

logger = logging.getLogger(__name__)

class AppConfig:
    """
    Application Configuration Manager
    
    Provides methods to load, save, and access application configuration settings.
    """
    
    def __init__(self):
        """Initialize the configuration manager"""
        self.config = {}
        self.config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "config",
            "config.json"
        )
        self.load_config()
    
    def load_config(self):
        """Load configuration from file"""
        try:
            # Make sure the config directory exists
            config_dir = os.path.dirname(self.config_path)
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)
            
            # Load config if it exists, otherwise create default
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    self.config = json.load(f)
                logger.info(f"Configuration loaded from {self.config_path}")
            else:
                # Create default config
                self.config = {
                    "ui": {
                        "type": "modern",
                        "theme": "system",
                        "fullscreen": False,
                        "window_width": 1280,
                        "window_height": 720,
                        "show_status_bar": True
                    },
                    "camera": {
                        "id": 0,
                        "resolution": [640, 480],
                        "fps": 30,
                        "flip_image": False
                    },
                    "face_detection": {
                        "confidence_threshold": 60,
                        "use_gpu": False,
                        "detection_model": "hog"  # 'hog' or 'cnn'
                    },
                    "attendance": {
                        "default_subject": "Python",
                        "auto_backup": True,
                        "backup_interval": 1  # days
                    },
                    "database": {
                        "type": "sqlite",
                        "path": "Data/attendance.db",
                        "backup_dir": "backups/data_backup"
                    },
                    "memory": {
                        "auto_gc": True
                    },
                    "app_name": "Face Recognition Attendance System"
                }
                self.save_config()
                logger.info("Created default configuration")
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            # Fallback to minimal default config
            self.config = {
                "ui": {"type": "modern", "theme": "system"},
                "camera": {"id": 0}
            }
    
    def save_config(self):
        """Save configuration to file"""
        try:
            # Make sure the config directory exists
            config_dir = os.path.dirname(self.config_path)
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)
            
            # Write config to file
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
            logger.info(f"Configuration saved to {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            return False
    
    def get(self, key_path, default=None):
        """
        Get a configuration value by its key path
        
        Args:
            key_path (str): Dot-separated path to the config value (e.g., 'ui.theme')
            default: Default value if the key doesn't exist
            
        Returns:
            The configuration value or the default
        """
        try:
            parts = key_path.split('.')
            value = self.config
            
            # Handle top-level key case
            if len(parts) == 1:
                return value.get(parts[0], default)
            
            # Navigate through the nested structure
            for part in parts[:-1]:
                if part not in value or not isinstance(value[part], dict):
                    return default
                value = value[part]
            
            # Get the final value
            return value.get(parts[-1], default)
        except Exception as e:
            logger.error(f"Error getting config value for {key_path}: {e}")
            return default
    
    def set(self, key_path, value):
        """
        Set a configuration value by its key path
        
        Args:
            key_path (str): Dot-separated path to the config value (e.g., 'ui.theme')
            value: The value to set
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            parts = key_path.split('.')
            config = self.config
            
            # Handle top-level key case
            if len(parts) == 1:
                config[parts[0]] = value
                return self.save_config()
            
            # Navigate through the nested structure, creating if needed
            for part in parts[:-1]:
                if part not in config:
                    config[part] = {}
                elif not isinstance(config[part], dict):
                    config[part] = {}
                config = config[part]
            
            # Set the final value
            config[parts[-1]] = value
            
            # Save the updated config
            return self.save_config()
        except Exception as e:
            logger.error(f"Error setting config value for {key_path}: {e}")
            return False
    
    def get_all(self):
        """
        Get the entire configuration dictionary
        
        Returns:
            dict: The entire configuration dictionary
        """
        return self.config.copy()