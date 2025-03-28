"""
Settings UI - Interface for configuring application settings
"""
import os
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Dict, Any, Optional
import logging

# Import local modules
from src.utils.camera_manager import CameraManager, list_available_cameras

# Configure logging
logger = logging.getLogger(__name__)

class AppConfig:
    """Class for managing application configuration"""
    
    def __init__(self, config_file="config/config.json"):
        """
        Initialize config with default values and load from file if available
        
        Args:
            config_file (str): Path to the config file
        """
        self.config_file = config_file
        
        # Default configuration
        self.default_config = {
            # General settings
            "app_name": "Face Detection Attendance System",
            "theme": "default",
            "log_level": "INFO",
            
            # Camera settings
            "camera": {
                "id": 0,
                "resolution": [640, 480],
                "fps": 30
            },
            
            # Face detection settings
            "face_detection": {
                "confidence_threshold": 60,
                "recognition_buffer_size": 5,
                "min_recognized_frames": 3,
                "show_recognition_confidence": True,
                "show_bounding_box": True,
                "late_threshold_seconds": 300  # 5 minutes
            },
            
            # Attendance settings
            "attendance": {
                "default_subject": "CS101",
                "auto_backup": True,
                "attendance_directory": "Attendance"
            },
            
            # UI settings
            "ui": {
                "font_family": "Helvetica",
                "title_font_size": 16,
                "normal_font_size": 12,
                "window_width": 1024,
                "window_height": 768,
                "fullscreen": False,
                "show_status_bar": True
            }
        }
        
        # Current configuration (will be loaded from file)
        self.config = self.default_config.copy()
        
        # Load configuration from file if available
        self.load_config()
    
    def get(self, key, default=None):
        """
        Get a configuration value
        
        Args:
            key (str): Configuration key (can be nested with dots)
            default: Default value if key doesn't exist
            
        Returns:
            Configuration value or default
        """
        # Handle nested keys (e.g., "camera.id")
        if "." in key:
            parts = key.split(".")
            value = self.config
            try:
                for part in parts:
                    value = value[part]
                return value
            except (KeyError, TypeError):
                return default
        
        # Simple key
        return self.config.get(key, default)
    
    def set(self, key, value):
        """
        Set a configuration value
        
        Args:
            key (str): Configuration key (can be nested with dots)
            value: Value to set
            
        Returns:
            bool: True if successful
        """
        # Handle nested keys (e.g., "camera.id")
        if "." in key:
            parts = key.split(".")
            config = self.config
            for part in parts[:-1]:
                if part not in config or not isinstance(config[part], dict):
                    config[part] = {}
                config = config[part]
            config[parts[-1]] = value
        else:
            # Simple key
            self.config[key] = value
        
        return True
    
    def load_config(self):
        """
        Load configuration from file
        
        Returns:
            bool: True if successful
        """
        try:
            if not os.path.exists(self.config_file):
                # Create config directory if it doesn't exist
                os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
                # Save default config
                self.save_config()
                return True
                
            with open(self.config_file, 'r') as f:
                loaded_config = json.load(f)
                
                # Update config with loaded values
                self._update_dict_recursive(self.config, loaded_config)
                
            logger.info(f"Configuration loaded successfully from {self.config_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}")
            return False
    
    def save_config(self):
        """
        Save configuration to file
        
        Returns:
            bool: True if successful
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
                
            logger.info(f"Configuration saved successfully to {self.config_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving configuration: {str(e)}")
            return False
    
    def reset_to_defaults(self):
        """
        Reset configuration to defaults
        
        Returns:
            bool: True if successful
        """
        self.config = self.default_config.copy()
        return self.save_config()
    
    def _update_dict_recursive(self, target, source):
        """
        Update dictionary recursively (helper method)
        
        Args:
            target (dict): Target dictionary to update
            source (dict): Source dictionary with updates
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._update_dict_recursive(target[key], value)
            else:
                target[key] = value


class SettingsDialog:
    """Dialog window for application settings"""
    
    def __init__(self, parent, app_config):
        """
        Initialize settings dialog
        
        Args:
            parent: Parent window
            app_config (AppConfig): Application configuration
        """
        self.parent = parent
        self.config = app_config
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Settings")
        self.dialog.geometry("600x500")
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog on the screen
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        # Create settings UI
        self._create_widgets()
        
        # Load current settings
        self._load_current_settings()
    
    def _create_widgets(self):
        """Create settings dialog widgets"""
        # Main frame with padding
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create notebook (tabs)
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create tabs
        self.general_tab = ttk.Frame(self.notebook)
        self.camera_tab = ttk.Frame(self.notebook)
        self.face_detection_tab = ttk.Frame(self.notebook)
        self.attendance_tab = ttk.Frame(self.notebook)
        self.appearance_tab = ttk.Frame(self.notebook)
        
        # Add tabs to notebook
        self.notebook.add(self.general_tab, text="General")
        self.notebook.add(self.camera_tab, text="Camera")
        self.notebook.add(self.face_detection_tab, text="Face Detection")
        self.notebook.add(self.attendance_tab, text="Attendance")
        self.notebook.add(self.appearance_tab, text="Appearance")
        
        # Build tab contents
        self._build_general_tab()
        self._build_camera_tab()
        self._build_face_detection_tab()
        self._build_attendance_tab()
        self._build_appearance_tab()
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        # Reset button
        reset_btn = ttk.Button(
            button_frame, 
            text="Reset to Defaults", 
            command=self._reset_to_defaults
        )
        reset_btn.pack(side=tk.LEFT, padx=5)
        
        # Save button
        save_btn = ttk.Button(
            button_frame, 
            text="Save", 
            command=self._save_settings
        )
        save_btn.pack(side=tk.RIGHT, padx=5)
        
        # Cancel button
        cancel_btn = ttk.Button(
            button_frame, 
            text="Cancel", 
            command=self.dialog.destroy
        )
        cancel_btn.pack(side=tk.RIGHT, padx=5)
    
    def _build_general_tab(self):
        """Build general settings tab"""
        # General frame with padding
        frame = ttk.LabelFrame(self.general_tab, text="General Settings", padding="10")
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # App name
        ttk.Label(frame, text="Application Name:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.app_name_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.app_name_var, width=30).grid(row=0, column=1, sticky=tk.W, padx=5)
        
        # Log level
        ttk.Label(frame, text="Log Level:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.log_level_var = tk.StringVar()
        log_level_combo = ttk.Combobox(frame, textvariable=self.log_level_var, width=10)
        log_level_combo['values'] = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
        log_level_combo.grid(row=1, column=1, sticky=tk.W, padx=5)
        
        # Theme
        ttk.Label(frame, text="Theme:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.theme_var = tk.StringVar()
        theme_combo = ttk.Combobox(frame, textvariable=self.theme_var, width=15)
        theme_combo['values'] = ("default", "light", "dark", "system")
        theme_combo.grid(row=2, column=1, sticky=tk.W, padx=5)
        
        # Add some space to improve layout
        for i in range(10):
            frame.grid_rowconfigure(i+3, weight=1)
    
    def _build_camera_tab(self):
        """Build camera settings tab"""
        # Camera frame with padding
        frame = ttk.LabelFrame(self.camera_tab, text="Camera Settings", padding="10")
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Advanced camera settings button
        advanced_btn = ttk.Button(
            frame, 
            text="Advanced Camera Settings", 
            command=self._open_camera_settings_dialog
        )
        advanced_btn.grid(row=0, column=0, columnspan=4, sticky=tk.W+tk.E, padx=5, pady=10)
        
        # Separator
        ttk.Separator(frame, orient=tk.HORIZONTAL).grid(
            row=1, column=0, columnspan=4, sticky=tk.W+tk.E, padx=5, pady=10
        )
        
        # Camera ID
        ttk.Label(frame, text="Camera:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.camera_id_var = tk.IntVar()
        
        # Get available cameras
        available_cameras = list_available_cameras()
        camera_values = list(range(10)) if not available_cameras else available_cameras
        
        camera_combo = ttk.Combobox(frame, textvariable=self.camera_id_var, width=10)
        camera_combo['values'] = camera_values
        camera_combo.grid(row=2, column=1, sticky=tk.W, padx=5)
        
        # Refresh cameras button
        refresh_btn = ttk.Button(frame, text="Refresh List", command=self._refresh_cameras)
        refresh_btn.grid(row=2, column=2, padx=5)
        
        # Test camera button
        test_btn = ttk.Button(frame, text="Test Camera", command=self._test_camera)
        test_btn.grid(row=2, column=3, padx=5)
        
        # Resolution
        ttk.Label(frame, text="Resolution:").grid(row=3, column=0, sticky=tk.W, pady=5)
        
        resolution_frame = ttk.Frame(frame)
        resolution_frame.grid(row=3, column=1, columnspan=3, sticky=tk.W, padx=5)
        
        self.resolution_width_var = tk.IntVar()
        self.resolution_height_var = tk.IntVar()
        
        ttk.Entry(resolution_frame, textvariable=self.resolution_width_var, width=6).pack(side=tk.LEFT)
        ttk.Label(resolution_frame, text="x").pack(side=tk.LEFT, padx=2)
        ttk.Entry(resolution_frame, textvariable=self.resolution_height_var, width=6).pack(side=tk.LEFT)
        
        # Common resolutions
        ttk.Label(frame, text="Preset:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.resolution_preset_var = tk.StringVar()
        resolution_presets = ttk.Combobox(frame, textvariable=self.resolution_preset_var, width=15)
        resolution_presets['values'] = (
            "640x480", "800x600", "1280x720", "1920x1080", "Custom"
        )
        resolution_presets.grid(row=4, column=1, columnspan=2, sticky=tk.W, padx=5)
        
        # Bind resolution preset change
        def on_resolution_selected(event):
            if resolution_presets.get() != "Custom":
                width, height = resolution_presets.get().split("x")
                self.resolution_width_var.set(int(width))
                self.resolution_height_var.set(int(height))
                
        resolution_presets.bind("<<ComboboxSelected>>", on_resolution_selected)
        
        # FPS
        ttk.Label(frame, text="FPS:").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.fps_var = tk.IntVar()
        fps_combo = ttk.Combobox(frame, textvariable=self.fps_var, width=10)
        fps_combo['values'] = (15, 20, 30, 60)
        fps_combo.grid(row=5, column=1, sticky=tk.W, padx=5)
        
        # Flip image horizontally option
        self.flip_image_var = tk.BooleanVar()
        ttk.Checkbutton(
            frame, 
            text="Flip Image Horizontally (mirror)", 
            variable=self.flip_image_var
        ).grid(row=6, column=0, columnspan=4, sticky=tk.W, pady=5)
        
        # Auto focus option
        self.auto_focus_var = tk.BooleanVar()
        ttk.Checkbutton(
            frame, 
            text="Auto Focus (if supported)", 
            variable=self.auto_focus_var
        ).grid(row=7, column=0, columnspan=4, sticky=tk.W, pady=5)
        
        # Auto exposure option
        self.auto_exposure_var = tk.BooleanVar()
        ttk.Checkbutton(
            frame, 
            text="Auto Exposure (if supported)", 
            variable=self.auto_exposure_var
        ).grid(row=8, column=0, columnspan=4, sticky=tk.W, pady=5)
        
        # Camera info label
        self.camera_info_var = tk.StringVar(value="Select a camera and click 'Test Camera' to get information")
        info_label = ttk.Label(
            frame, 
            textvariable=self.camera_info_var, 
            background="#f0f0f0", 
            wraplength=400
        )
        info_label.grid(row=9, column=0, columnspan=4, sticky=tk.W+tk.E, pady=10, padx=5)
        
        # Add some space to improve layout
        for i in range(10):
            frame.grid_rowconfigure(i+10, weight=1)
    
    def _build_face_detection_tab(self):
        """Build face detection settings tab"""
        # Face detection frame with padding
        frame = ttk.LabelFrame(self.face_detection_tab, text="Face Detection Settings", padding="10")
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Confidence threshold
        ttk.Label(frame, text="Confidence Threshold:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.confidence_threshold_var = tk.IntVar()
        ttk.Scale(frame, from_=0, to=100, variable=self.confidence_threshold_var, orient=tk.HORIZONTAL) \
            .grid(row=0, column=1, sticky=tk.W+tk.E, padx=5)
        ttk.Label(frame, textvariable=self.confidence_threshold_var).grid(row=0, column=2, padx=5)
        
        # Recognition buffer size
        ttk.Label(frame, text="Recognition Buffer Size:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.buffer_size_var = tk.IntVar()
        ttk.Spinbox(frame, from_=1, to=20, textvariable=self.buffer_size_var, width=5) \
            .grid(row=1, column=1, sticky=tk.W, padx=5)
        
        # Min recognized frames
        ttk.Label(frame, text="Min Recognized Frames:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.min_frames_var = tk.IntVar()
        ttk.Spinbox(frame, from_=1, to=20, textvariable=self.min_frames_var, width=5) \
            .grid(row=2, column=1, sticky=tk.W, padx=5)
        
        # Show recognition confidence
        self.show_confidence_var = tk.BooleanVar()
        ttk.Checkbutton(frame, text="Show Recognition Confidence", variable=self.show_confidence_var) \
            .grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Show bounding box
        self.show_bbox_var = tk.BooleanVar()
        ttk.Checkbutton(frame, text="Show Bounding Box", variable=self.show_bbox_var) \
            .grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=5)
            
        # Late threshold
        ttk.Label(frame, text="Late Threshold (seconds):").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.late_threshold_var = tk.IntVar()
        ttk.Entry(frame, textvariable=self.late_threshold_var, width=10) \
            .grid(row=5, column=1, sticky=tk.W, padx=5)
        
        # Add some space to improve layout
        for i in range(10):
            frame.grid_rowconfigure(i+6, weight=1)
    
    def _build_attendance_tab(self):
        """Build attendance settings tab"""
        # Attendance frame with padding
        frame = ttk.LabelFrame(self.attendance_tab, text="Attendance Settings", padding="10")
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Default subject
        ttk.Label(frame, text="Default Subject:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.default_subject_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.default_subject_var, width=20) \
            .grid(row=0, column=1, columnspan=2, sticky=tk.W, padx=5)
        
        # Auto backup
        self.auto_backup_var = tk.BooleanVar()
        ttk.Checkbutton(frame, text="Auto Backup", variable=self.auto_backup_var) \
            .grid(row=1, column=0, sticky=tk.W, pady=5)
        
        # Attendance directory
        ttk.Label(frame, text="Attendance Directory:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.attendance_dir_var = tk.StringVar()
        dir_entry = ttk.Entry(frame, textvariable=self.attendance_dir_var, width=30)
        dir_entry.grid(row=2, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        
        # Browse button
        browse_btn = ttk.Button(frame, text="Browse", command=self._browse_attendance_dir)
        browse_btn.grid(row=2, column=2, padx=5)
        
        # Add some space to improve layout
        for i in range(10):
            frame.grid_rowconfigure(i+3, weight=1)
    
    def _build_appearance_tab(self):
        """Build appearance settings tab"""
        # Appearance frame with padding
        frame = ttk.LabelFrame(self.appearance_tab, text="Appearance Settings", padding="10")
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Font family
        ttk.Label(frame, text="Font Family:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.font_family_var = tk.StringVar()
        font_combo = ttk.Combobox(frame, textvariable=self.font_family_var, width=20)
        font_combo['values'] = ("Helvetica", "Arial", "Times New Roman", "Courier New", "Verdana")
        font_combo.grid(row=0, column=1, sticky=tk.W, padx=5)
        
        # Title font size
        ttk.Label(frame, text="Title Font Size:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.title_font_size_var = tk.IntVar()
        ttk.Spinbox(frame, from_=10, to=30, textvariable=self.title_font_size_var, width=5) \
            .grid(row=1, column=1, sticky=tk.W, padx=5)
        
        # Normal font size
        ttk.Label(frame, text="Normal Font Size:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.normal_font_size_var = tk.IntVar()
        ttk.Spinbox(frame, from_=8, to=20, textvariable=self.normal_font_size_var, width=5) \
            .grid(row=2, column=1, sticky=tk.W, padx=5)
        
        # Window size
        ttk.Label(frame, text="Window Size:").grid(row=3, column=0, sticky=tk.W, pady=5)
        
        size_frame = ttk.Frame(frame)
        size_frame.grid(row=3, column=1, sticky=tk.W, padx=5)
        
        self.window_width_var = tk.IntVar()
        self.window_height_var = tk.IntVar()
        
        ttk.Entry(size_frame, textvariable=self.window_width_var, width=6).pack(side=tk.LEFT)
        ttk.Label(size_frame, text="x").pack(side=tk.LEFT, padx=2)
        ttk.Entry(size_frame, textvariable=self.window_height_var, width=6).pack(side=tk.LEFT)
        
        # Fullscreen option
        self.fullscreen_var = tk.BooleanVar()
        ttk.Checkbutton(frame, text="Fullscreen Mode", variable=self.fullscreen_var) \
            .grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Show status bar option
        self.show_status_bar_var = tk.BooleanVar()
        ttk.Checkbutton(frame, text="Show Status Bar", variable=self.show_status_bar_var) \
            .grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Add some space to improve layout
        for i in range(10):
            frame.grid_rowconfigure(i+6, weight=1)
    
    def _load_current_settings(self):
        """Load current settings into dialog"""
        # General tab
        self.app_name_var.set(self.config.get("app_name", "Face Detection Attendance System"))
        self.log_level_var.set(self.config.get("log_level", "INFO"))
        self.theme_var.set(self.config.get("theme", "default"))
        
        # Camera tab
        self.camera_id_var.set(self.config.get("camera.id", 0))
        resolution = self.config.get("camera.resolution", [640, 480])
        self.resolution_width_var.set(resolution[0])
        self.resolution_height_var.set(resolution[1])
        self.fps_var.set(self.config.get("camera.fps", 30))
        self.flip_image_var.set(self.config.get("camera.flip_image", False))
        self.auto_focus_var.set(self.config.get("camera.auto_focus", False))
        self.auto_exposure_var.set(self.config.get("camera.auto_exposure", False))
        
        # Face detection tab
        self.confidence_threshold_var.set(self.config.get("face_detection.confidence_threshold", 60))
        self.buffer_size_var.set(self.config.get("face_detection.recognition_buffer_size", 5))
        self.min_frames_var.set(self.config.get("face_detection.min_recognized_frames", 3))
        self.show_confidence_var.set(self.config.get("face_detection.show_recognition_confidence", True))
        self.show_bbox_var.set(self.config.get("face_detection.show_bounding_box", True))
        self.late_threshold_var.set(self.config.get("face_detection.late_threshold_seconds", 300))
        
        # Attendance tab
        self.default_subject_var.set(self.config.get("attendance.default_subject", "CS101"))
        self.auto_backup_var.set(self.config.get("attendance.auto_backup", True))
        self.attendance_dir_var.set(self.config.get("attendance.attendance_directory", "Attendance"))
        
        # Appearance tab
        self.font_family_var.set(self.config.get("ui.font_family", "Helvetica"))
        self.title_font_size_var.set(self.config.get("ui.title_font_size", 16))
        self.normal_font_size_var.set(self.config.get("ui.normal_font_size", 12))
        self.window_width_var.set(self.config.get("ui.window_width", 1024))
        self.window_height_var.set(self.config.get("ui.window_height", 768))
        self.fullscreen_var.set(self.config.get("ui.fullscreen", False))
        self.show_status_bar_var.set(self.config.get("ui.show_status_bar", True))
    
    def _save_settings(self):
        """Save settings to config and close dialog"""
        # General tab
        self.config.set("app_name", self.app_name_var.get())
        self.config.set("log_level", self.log_level_var.get())
        self.config.set("theme", self.theme_var.get())
        
        # Camera tab
        self.config.set("camera.id", self.camera_id_var.get())
        self.config.set("camera.resolution", [
            self.resolution_width_var.get(), 
            self.resolution_height_var.get()
        ])
        self.config.set("camera.fps", self.fps_var.get())
        self.config.set("camera.flip_image", self.flip_image_var.get())
        self.config.set("camera.auto_focus", self.auto_focus_var.get())
        self.config.set("camera.auto_exposure", self.auto_exposure_var.get())
        
        # Face detection tab
        self.config.set("face_detection.confidence_threshold", self.confidence_threshold_var.get())
        self.config.set("face_detection.recognition_buffer_size", self.buffer_size_var.get())
        self.config.set("face_detection.min_recognized_frames", self.min_frames_var.get())
        self.config.set("face_detection.show_recognition_confidence", self.show_confidence_var.get())
        self.config.set("face_detection.show_bounding_box", self.show_bbox_var.get())
        self.config.set("face_detection.late_threshold_seconds", self.late_threshold_var.get())
        
        # Attendance tab
        self.config.set("attendance.default_subject", self.default_subject_var.get())
        self.config.set("attendance.auto_backup", self.auto_backup_var.get())
        self.config.set("attendance.attendance_directory", self.attendance_dir_var.get())
        
        # Appearance tab
        self.config.set("ui.font_family", self.font_family_var.get())
        self.config.set("ui.title_font_size", self.title_font_size_var.get())
        self.config.set("ui.normal_font_size", self.normal_font_size_var.get())
        self.config.set("ui.window_width", self.window_width_var.get())
        self.config.set("ui.window_height", self.window_height_var.get())
        self.config.set("ui.fullscreen", self.fullscreen_var.get())
        self.config.set("ui.show_status_bar", self.show_status_bar_var.get())
        
        # Save to file
        if self.config.save_config():
            messagebox.showinfo("Settings", "Settings saved successfully")
            self.dialog.destroy()
        else:
            messagebox.showerror("Settings", "Error saving settings")
    
    def _reset_to_defaults(self):
        """Reset settings to defaults"""
        if messagebox.askyesno("Reset Settings", "Are you sure you want to reset all settings to default values?"):
            # Reset the configuration
            self.config.reset_to_defaults()
            # Reload settings into dialog
            self._load_current_settings()
            messagebox.showinfo("Settings", "Settings have been reset to defaults")
    
    def _test_camera(self):
        """Test camera connection"""
        try:
            camera_id = self.camera_id_var.get()
            width = self.resolution_width_var.get()
            height = self.resolution_height_var.get()
            
            # Create a test window
            test_window = tk.Toplevel(self.dialog)
            test_window.title(f"Camera Test (ID: {camera_id})")
            test_window.geometry(f"{width}x{height}")
            
            # Create a label to show the camera feed
            video_label = ttk.Label(test_window)
            video_label.pack(fill=tk.BOTH, expand=True)
            
            # Create a close button
            close_btn = ttk.Button(test_window, text="Close", command=test_window.destroy)
            close_btn.pack(pady=10)
            
            # Initialize camera
            camera = CameraManager(camera_id=camera_id, resolution=(width, height))
            if not camera.connect():
                messagebox.showerror("Camera Test", f"Failed to connect to camera {camera_id}")
                test_window.destroy()
                return
                
            # Create video display widget
            from src.utils.camera_manager import VideoDisplayWidget
            video_display = VideoDisplayWidget(video_label, camera)
            video_display.start()
            
            # Make sure the video display stops when the window is closed
            def on_test_window_close():
                video_display.stop()
                camera.disconnect()
                test_window.destroy()
                
            test_window.protocol("WM_DELETE_WINDOW", on_test_window_close)
            
        except Exception as e:
            messagebox.showerror("Camera Test", f"Error testing camera: {str(e)}")
    
    def _refresh_cameras(self):
        """Refresh the list of available cameras"""
        try:
            # Initialize camera manager if not available
            if not hasattr(self, 'camera_manager'):
                from src.utils.camera_manager import CameraManager
                self.camera_manager = CameraManager()
            
            # Refresh cameras and update UI
            self.camera_manager.refresh_cameras()
            cameras = self.camera_manager.list_cameras()
            
            # Update camera combobox values
            cameras_dropdown = self.camera_tab.winfo_children()[0].grid_slaves(row=0, column=1)[0]
            
            # Create dropdown values
            camera_values = ["Auto-detect (default)"]
            for camera in cameras:
                camera_values.append(f"Camera {camera.index}: {camera.name}")
            
            # If no cameras found other than auto-detect, add some placeholders
            if len(camera_values) == 1:
                camera_values.extend(["Camera 0", "Camera 1", "Camera 2"])
            
            cameras_dropdown['values'] = camera_values
            
            # Update status
            num_cameras = len(cameras)
            self.camera_info_var.set(f"Found {num_cameras} camera(s). Select a camera and click 'Test Camera' to try it.")
            
            # Show a message
            messagebox.showinfo("Cameras", f"Found {num_cameras} camera(s)")
            
        except Exception as e:
            logger.exception(f"Error refreshing camera list: {e}")
            messagebox.showerror("Refresh Cameras", f"Error refreshing camera list: {str(e)}")
    
    def _browse_attendance_dir(self):
        """Browse for attendance directory"""
        directory = filedialog.askdirectory(
            initialdir=self.attendance_dir_var.get(),
            title="Select Attendance Directory"
        )
        if directory:
            self.attendance_dir_var.set(directory)
    
    def _open_camera_settings_dialog(self):
        """Open the advanced camera settings dialog"""
        try:
            # Import the camera settings dialog
            from src.ui.camera_settings_dialog import CameraSettingsDialog
            
            # Initialize camera manager if needed
            if not hasattr(self, 'camera_manager'):
                from src.utils.camera_manager import CameraManager
                self.camera_manager = CameraManager()
            
            # Create and show the camera settings dialog
            camera_dialog = CameraSettingsDialog(self.dialog, self.camera_manager, self.config)
            
            # Wait for dialog to close
            self.dialog.wait_window(camera_dialog.dialog)
            
            # Reload camera settings after dialog closes
            self._load_current_settings()
            
        except Exception as e:
            logger.exception(f"Error opening camera settings dialog: {e}")
            messagebox.showerror("Camera Settings", f"Error opening camera settings dialog: {str(e)}")

# For standalone testing
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Test Settings Dialog")
    
    config = AppConfig()
    
    def open_settings():
        dialog = SettingsDialog(root, config)
    
    open_btn = ttk.Button(root, text="Open Settings", command=open_settings)
    open_btn.pack(padx=20, pady=20)
    
    root.mainloop()