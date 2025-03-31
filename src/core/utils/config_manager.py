"""
Configuration Manager for Face Detection Attendance System

This module provides a configuration management system for both UI variants.
"""
import os
import json
import logging
import datetime
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

class ConfigManager:
    """
    Configuration manager for the Face Detection Attendance System
    
    Handles loading, saving, and accessing configuration settings
    """
    
    def __init__(self, config_file="config/config.json"):
        """
        Initialize the configuration manager
        
        Args:
            config_file (str): Path to the configuration file
        """
        self.config_file = config_file
        self.config = {}
        self.defaults = {
            "app": {
                "name": "Face Detection Attendance System",
                "version": "1.0.0"
            },
            "ui": {
                "type": "modern",  # modern or classic
                "theme": "system",  # system, light, or dark
                "remember_last_UI": True
            },
            "face_detection": {
                "detection_method": "auto",  # auto, hog, cnn, haarcascade, dnn
                "recognition_method": "hybrid",  # hybrid, lbph, embedding
                "scale_factor": 0.5,
                "min_face_size": 30,
                "confidence_threshold": 0.6
            },
            "camera": {
                "device_id": 0,  # Default camera
                "resolution": {
                    "width": 640,
                    "height": 480
                },
                "fps": 30
            },
            "database": {
                "path": "attendance.db",
                "backup": {
                    "enabled": True,
                    "interval_days": 7,
                    "max_backups": 5
                }
            },
            "paths": {
                "training_images": "TrainingImage",
                "attendance_records": "Attendance",
                "student_details": "StudentDetails"
            },
            "attendance": {
                "auto_export_csv": True,
                "duplicate_timeout": 600  # 10 minutes in seconds
            },
            "training": {
                "max_images": 50,
                "interval": 0.5  # seconds between captures
            },
            "memory": {
                "auto_gc": True
            }
        }
        
        # Load configuration
        self.load()
    
    def load(self):
        """
        Load configuration from file
        
        Returns:
            bool: Success or failure
        """
        try:
            # Check if config file exists
            if not os.path.exists(self.config_file):
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
                
                # Use defaults and save them
                self.config = self.defaults.copy()
                self.save()
                logger.info("Created default configuration file")
                return True
                
            # Load from file
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
                
            # Check for missing keys and add defaults
            self._ensure_defaults()
            
            logger.info(f"Loaded configuration from {self.config_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            # Use defaults
            self.config = self.defaults.copy()
            return False
    
    def save(self):
        """
        Save configuration to file
        
        Returns:
            bool: Success or failure
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            # Save to file
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
                
            logger.info(f"Saved configuration to {self.config_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            return False
    
    def _ensure_defaults(self):
        """Ensure all default config keys exist in the loaded config"""
        def update_dict(target, source):
            for key, value in source.items():
                if key not in target:
                    target[key] = value
                elif isinstance(value, dict) and isinstance(target[key], dict):
                    update_dict(target[key], value)
        
        update_dict(self.config, self.defaults)
    
    def get(self, key=None, default=None):
        """
        Get a configuration value
        
        Args:
            key (str, optional): Dot-separated key path (e.g. 'ui.theme')
            default: Default value to return if key is not found
            
        Returns:
            The configuration value or default
        """
        if key is None:
            return self.config
            
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key, value):
        """
        Set a configuration value
        
        Args:
            key (str): Dot-separated key path (e.g. 'ui.theme')
            value: Value to set
            
        Returns:
            bool: Success or failure
        """
        if not key:
            return False
            
        keys = key.split('.')
        config = self.config
        
        try:
            # Navigate to the parent of the final key
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]
                
            # Set the value
            config[keys[-1]] = value
            
            # Save the updated configuration
            return self.save()
        except Exception as e:
            logger.error(f"Error setting configuration {key}: {e}")
            return False
    
    def reset(self, key=None):
        """
        Reset configuration to defaults
        
        Args:
            key (str, optional): Dot-separated key path to reset, or None to reset all
            
        Returns:
            bool: Success or failure
        """
        try:
            if key is None:
                # Reset entire configuration
                self.config = self.defaults.copy()
                return self.save()
                
            # Reset specific path
            keys = key.split('.')
            default_value = self.defaults
            config = self.config
            
            # Navigate to the default value
            for k in keys:
                default_value = default_value.get(k)
                if default_value is None:
                    logger.warning(f"No default value for {key}")
                    return False
            
            # Navigate to the parent in the actual config
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]
                
            # Set the default value
            config[keys[-1]] = default_value
            
            return self.save()
            
        except Exception as e:
            logger.error(f"Error resetting configuration: {e}")
            return False
    
    def export(self, export_path=None):
        """
        Export configuration to a file
        
        Args:
            export_path (str, optional): Path to export file, or None for default
            
        Returns:
            str: Path to the exported file or None on failure
        """
        try:
            if export_path is None:
                # Generate default export path
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                os.makedirs("exports", exist_ok=True)
                export_path = f"exports/config_export_{timestamp}.json"
                
            # Ensure directory exists
            os.makedirs(os.path.dirname(export_path), exist_ok=True)
            
            # Export configuration
            with open(export_path, 'w') as f:
                json.dump(self.config, f, indent=4)
                
            logger.info(f"Exported configuration to {export_path}")
            return export_path
            
        except Exception as e:
            logger.error(f"Error exporting configuration: {e}")
            return None
    
    def import_config(self, import_path):
        """
        Import configuration from a file
        
        Args:
            import_path (str): Path to import file
            
        Returns:
            bool: Success or failure
        """
        try:
            if not os.path.exists(import_path):
                logger.error(f"Import file not found: {import_path}")
                return False
                
            # Load imported configuration
            with open(import_path, 'r') as f:
                imported_config = json.load(f)
                
            # Make a backup of current configuration
            backup_path = self.export()
            
            if not backup_path:
                logger.warning("Failed to create backup before import")
                
            # Set the new configuration
            self.config = imported_config
            
            # Ensure defaults for any missing keys
            self._ensure_defaults()
            
            # Save the imported configuration
            result = self.save()
            
            if result:
                logger.info(f"Imported configuration from {import_path}")
                
            return result
            
        except Exception as e:
            logger.error(f"Error importing configuration: {e}")
            return False
    
    def get_config(self):
        """
        Get the entire configuration dictionary
        
        Returns:
            dict: The current configuration
        """
        return self.config.copy() 