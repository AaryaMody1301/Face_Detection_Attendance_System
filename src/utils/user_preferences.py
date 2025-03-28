"""
User Preferences Module for Analytics

This module provides functionality to save, load, and manage user preferences
for the analytics dashboard.
"""
import os
import json
import logging
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

# Default preferences
DEFAULT_PREFERENCES = {
    # Camera settings
    "camera": {
        "device": "Auto-detect (default)",
        "resolution": "640x480",
        "fps": 30,
        "flip_image": False,
        "auto_focus": True,
        "auto_exposure": True
    },
    
    # Face detection settings
    "face_detection": {
        "confidence_threshold": 60,
        "min_frames": 3,
        "detection_method": "hog",  # 'hog' or 'cnn'
        "use_gpu": False,
        "face_model": "HOG"
    },
    
    # Application settings
    "application": {
        "theme": "system",  # 'light', 'dark', or 'system'
        "language": "en",
        "startup_mode": "default",  # 'default', 'minimized', or 'fullscreen'
        "check_updates": True,
        "show_splash": True
    },
    
    # Training settings
    "training": {
        "samples_per_person": 20,
        "augment_data": True,
        "model_type": "standard"  # 'standard', 'light', or 'enhanced'
    },
    
    # UI settings
    "ui": {
        "show_status_bar": True,
        "show_toolbar": True,
        "confirm_exit": True,
        "auto_save": True
    },
    
    # Attendance settings
    "attendance": {
        "default_subject": "",
        "auto_export": False,
        "export_format": "csv",
        "folder_structure": "date",  # 'date', 'subject', or 'flat'
        "duplicate_action": "update"  # 'update', 'skip', or 'create_new'
    },
    
    # Chart colors for analytics
    "chart_colors": {
        "primary": "#1976D2",
        "secondary": "#FFA000",
        "accent": "#4CAF50",
        "error": "#F44336",
        "background": "#FFFFFF"
    },
    "chart_fonts": {
        "title_size": 14,
        "label_size": 12,
        "tick_size": 10,
        "family": "Arial"
    },
    "chart_style": {
        "theme": "default",
        "grid": True,
        "legend": True,
        "animate": True
    },
    "default_views": {
        "main_chart": "trend",
        "date_range": "month",
        "show_summary": True,
        "auto_refresh": False
    },
    "export_settings": {
        "default_format": "csv",
        "include_charts": True,
        "dpi": 300
    },
    "advanced": {
        "cache_enabled": True,
        "cache_duration_hours": 24,
        "show_stats": True,
        "debug_mode": False
    },
    "color_palettes": {
        "default": ["#1976D2", "#FFA000", "#4CAF50", "#F44336", "#9C27B0", "#607D8B", "#FF5722", "#795548"],
        "pastel": ["#90CAF9", "#FFCC80", "#A5D6A7", "#EF9A9A", "#CE93D8", "#B0BEC5", "#FFAB91", "#BCAAA4"],
        "vivid": ["#2962FF", "#FF6D00", "#00C853", "#D50000", "#AA00FF", "#263238", "#DD2C00", "#3E2723"],
        "monochrome": ["#0D47A1", "#1565C0", "#1976D2", "#1E88E5", "#2196F3", "#42A5F5", "#64B5F6", "#90CAF9"]
    },
    "last_updated": datetime.now().isoformat()
}

class UserPreferences:
    """Class for managing user preferences"""
    
    def __init__(self, config_dir="config"):
        """
        Initialize user preferences
        
        Args:
            config_dir (str): Directory to store config files
        """
        self.config_dir = config_dir
        self.preferences_file = os.path.join(config_dir, "preferences.json")
        self.preferences = DEFAULT_PREFERENCES.copy()
        
        # Create config directory if it doesn't exist
        os.makedirs(config_dir, exist_ok=True)
        
        # Load existing preferences if available
        self.load()
    
    def load(self):
        """
        Load preferences from file
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if os.path.exists(self.preferences_file):
                with open(self.preferences_file, 'r') as f:
                    loaded_prefs = json.load(f)
                    
                    # Update preferences with loaded values
                    for category, values in loaded_prefs.items():
                        if category in self.preferences:
                            if isinstance(values, dict):
                                self.preferences[category].update(values)
                            else:
                                self.preferences[category] = values
                    
                    logger.info("Loaded user preferences")
                    return True
            return False
        except Exception as e:
            logger.error(f"Error loading preferences: {e}")
            return False
    
    def save(self):
        """
        Save preferences to file
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Update last updated timestamp
            self.preferences["last_updated"] = datetime.now().isoformat()
            
            with open(self.preferences_file, 'w') as f:
                json.dump(self.preferences, f, indent=4)
                
            logger.info("Saved user preferences")
            return True
        except Exception as e:
            logger.error(f"Error saving preferences: {e}")
            return False
    
    def get_preference(self, category, key=None, default=None):
        """
        Get a preference value
        
        Args:
            category (str): Preference category
            key (str, optional): Specific preference key
            default: Default value if preference doesn't exist
            
        Returns:
            object: Preference value or default
        """
        try:
            if category in self.preferences:
                if key is not None:
                    return self.preferences[category].get(key, default)
                return self.preferences[category]
            return default
        except Exception as e:
            logger.error(f"Error getting preference: {e}")
            return default
    
    def set_preference(self, category, key, value):
        """
        Set a preference value
        
        Args:
            category (str): Preference category
            key (str): Preference key
            value: Preference value
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if category not in self.preferences:
                self.preferences[category] = {}
                
            self.preferences[category][key] = value
            logger.info(f"Set preference {category}.{key}")
            return True
        except Exception as e:
            logger.error(f"Error setting preference: {e}")
            return False
    
    def reset_category(self, category):
        """
        Reset a preference category to defaults
        
        Args:
            category (str): Preference category to reset
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if category in DEFAULT_PREFERENCES:
                self.preferences[category] = DEFAULT_PREFERENCES[category].copy()
                logger.info(f"Reset {category} preferences to defaults")
                return True
            return False
        except Exception as e:
            logger.error(f"Error resetting preferences: {e}")
            return False
    
    def reset_all(self):
        """
        Reset all preferences to defaults
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.preferences = DEFAULT_PREFERENCES.copy()
            logger.info("Reset all preferences to defaults")
            return True
        except Exception as e:
            logger.error(f"Error resetting all preferences: {e}")
            return False
    
    def get_color_palette(self, name="default"):
        """
        Get a color palette by name
        
        Args:
            name (str): Name of the palette
            
        Returns:
            list: List of color codes
        """
        palettes = self.get_preference("color_palettes")
        return palettes.get(name, palettes.get("default"))
    
    def add_color_palette(self, name, colors):
        """
        Add a new color palette
        
        Args:
            name (str): Name of the palette
            colors (list): List of color codes
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if "color_palettes" not in self.preferences:
                self.preferences["color_palettes"] = {}
                
            self.preferences["color_palettes"][name] = colors
            logger.info(f"Added color palette: {name}")
            return True
        except Exception as e:
            logger.error(f"Error adding color palette: {e}")
            return False
    
    def get_theme(self):
        """
        Get the current theme settings
        
        Returns:
            dict: Theme settings
        """
        theme = {
            "colors": self.get_preference("chart_colors"),
            "fonts": self.get_preference("chart_fonts"),
            "style": self.get_preference("chart_style")
        }
        return theme
    
    # Camera-related convenience methods
    def get_camera_settings(self):
        """
        Get all camera settings
        
        Returns:
            dict: Camera settings
        """
        return self.get_preference("camera", default={})
    
    def set_camera_device(self, device_id):
        """
        Set preferred camera device
        
        Args:
            device_id: Camera device identifier
            
        Returns:
            bool: True if successful
        """
        return self.set_preference("camera", "device", device_id)
    
    def get_camera_resolution(self):
        """
        Get camera resolution as a tuple (width, height)
        
        Returns:
            tuple: Resolution as (width, height)
        """
        resolution_str = self.get_preference("camera", "resolution", "640x480")
        try:
            width, height = map(int, resolution_str.split("x"))
            return width, height
        except:
            return 640, 480
    
    # Application-related convenience methods
    def get_app_theme(self):
        """
        Get application theme
        
        Returns:
            str: Theme name
        """
        return self.get_preference("application", "theme", "system")
    
    def set_app_theme(self, theme):
        """
        Set application theme
        
        Args:
            theme (str): Theme name
            
        Returns:
            bool: True if successful
        """
        return self.set_preference("application", "theme", theme)