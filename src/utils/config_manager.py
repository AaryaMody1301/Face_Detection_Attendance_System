"""
Configuration Manager for Face Detection Attendance System
"""
import os
import json
import logging
from pathlib import Path

# Set up logging
logger = logging.getLogger(__name__)

class ConfigManager:
    """Handles configuration settings for the application"""
    
    DEFAULT_CONFIG = {
        "theme": "system",
        "face_recognition": {
            "threshold": 0.60,
            "method": "hybrid"
        },
        "camera": {
            "id": 0,
            "resolution": "640x480"
        },
        "database": {
            "path": "Data/attendance.db"
        },
        "backup": {
            "auto_backup": True,
            "frequency_days": 7
        }
    }
    
    def __init__(self, config_path=None):
        """
        Initialize the configuration manager
        
        Args:
            config_path: Path to the configuration file (default: config/config.json)
        """
        self.config_path = config_path or os.path.join("config", "config.json")
        self.config = self.load_config()
    
    def load_config(self):
        """
        Load configuration from file
        
        Returns:
            dict: Configuration dictionary
        """
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                logger.info(f"Loaded configuration from {self.config_path}")
                
                # Merge with default config to ensure all required fields
                merged_config = self.DEFAULT_CONFIG.copy()
                self._deep_update(merged_config, config)
                return merged_config
            else:
                logger.warning(f"Configuration file {self.config_path} not found, using defaults")
                return self.DEFAULT_CONFIG.copy()
        
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return self.DEFAULT_CONFIG.copy()
    
    def save_config(self, config=None):
        """
        Save configuration to file
        
        Args:
            config: Configuration dictionary to save (default: current config)
            
        Returns:
            bool: Success status
        """
        if config is None:
            config = self.config
        
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=4)
            
            logger.info(f"Saved configuration to {self.config_path}")
            return True
        
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            return False
    
    def get_config(self):
        """
        Get current configuration
        
        Returns:
            dict: Configuration dictionary
        """
        return self.config
    
    def update_config(self, new_config):
        """
        Update configuration
        
        Args:
            new_config: New configuration dictionary
            
        Returns:
            bool: Success status
        """
        try:
            # Deep update current config
            self._deep_update(self.config, new_config)
            
            # Save updated config
            return self.save_config()
        
        except Exception as e:
            logger.error(f"Error updating configuration: {e}")
            return False
    
    def restore_defaults(self):
        """
        Restore default configuration
        
        Returns:
            bool: Success status
        """
        self.config = self.DEFAULT_CONFIG.copy()
        return self.save_config()
    
    def _deep_update(self, target, source):
        """
        Recursively update nested dictionaries
        
        Args:
            target: Target dictionary to update
            source: Source dictionary with updates
        """
        for key, value in source.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                # Recursively update nested dictionaries
                self._deep_update(target[key], value)
            else:
                # Update or add value
                target[key] = value