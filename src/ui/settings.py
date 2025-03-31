"""
Settings Page for Face Detection Attendance System
"""
import os
import logging
import tkinter as tk
import customtkinter as ctk
from PIL import Image

from src.core.utils.config_manager import ConfigManager
from src.utils.backup_manager import BackupManager

# Set up logging
logger = logging.getLogger(__name__)

class SettingsPage(ctk.CTkFrame):
    """Settings page for configuring application parameters"""
    
    def __init__(self, master):
        """
        Initialize the settings page
        
        Args:
            master: Parent widget
        """
        super().__init__(master)
        
        # Load configuration
        self.config_manager = ConfigManager()
        self.config = self.config_manager.get_config()
        
        # Initialize backup manager
        self.backup_manager = BackupManager()
        
        # Create UI elements
        self._setup_ui()
        
        logger.info("Settings page initialized")
    
    def _setup_ui(self):
        """Set up the settings UI"""
        # Configure grid layout (2x1)
        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Left panel: General settings
        self.general_panel = ctk.CTkFrame(self)
        self.general_panel.grid(row=0, column=0, padx=(20, 10), pady=20, sticky="nsew")
        self.general_panel.grid_columnconfigure(0, weight=1)
        
        # Scrollable frame for settings
        self.general_scrollable = ctk.CTkScrollableFrame(self.general_panel)
        self.general_scrollable.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.general_scrollable.grid_columnconfigure(0, weight=1)
        self.general_panel.grid_rowconfigure(0, weight=1)
        
        # Title
        self.general_title = ctk.CTkLabel(
            self.general_scrollable,
            text="General Settings",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.general_title.grid(row=0, column=0, padx=20, pady=(15, 15), sticky="w")
        
        # Theme section
        self.theme_section = self._create_section_frame(self.general_scrollable, "Theme")
        self.theme_section.grid(row=1, column=0, padx=20, pady=(0, 15), sticky="ew")
        
        # Appearance mode
        self.appearance_frame = ctk.CTkFrame(self.theme_section, fg_color="transparent")
        self.appearance_frame.grid(row=0, column=0, padx=10, pady=(5, 10), sticky="ew")
        self.appearance_frame.grid_columnconfigure(1, weight=1)
        
        self.appearance_label = ctk.CTkLabel(
            self.appearance_frame,
            text="Appearance Mode:",
            anchor="w"
        )
        self.appearance_label.grid(row=0, column=0, padx=(20, 10), pady=10, sticky="w")
        
        self.appearance_var = ctk.StringVar(value=self.config.get("theme", "system"))
        self.appearance_options = ctk.CTkOptionMenu(
            self.appearance_frame,
            values=["system", "light", "dark"],
            variable=self.appearance_var,
            command=self._on_appearance_change
        )
        self.appearance_options.grid(row=0, column=1, padx=(0, 20), pady=10, sticky="ew")
        
        # Dark/Light Mode toggle
        self.toggle_frame = ctk.CTkFrame(self.theme_section, fg_color="transparent")
        self.toggle_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.toggle_frame.grid_columnconfigure(1, weight=1)
        
        self.toggle_label = ctk.CTkLabel(
            self.toggle_frame,
            text="Dark/Light Mode:",
            anchor="w"
        )
        self.toggle_label.grid(row=0, column=0, padx=(20, 10), pady=10, sticky="w")
        
        # Toggle switch
        current_mode = ctk.get_appearance_mode().lower()
        self.toggle_var = ctk.StringVar(value=current_mode)
        self.toggle_switch = ctk.CTkSwitch(
            self.toggle_frame,
            text="Dark Mode" if current_mode == "dark" else "Light Mode",
            command=self._on_theme_toggle,
            variable=self.toggle_var,
            onvalue="dark",
            offvalue="light"
        )
        self.toggle_switch.grid(row=0, column=1, padx=(0, 20), pady=10, sticky="w")
        
        # Update switch state based on current theme
        if current_mode == "dark":
            self.toggle_switch.select()
        else:
            self.toggle_switch.deselect()
        
        # Color theme selection
        self.color_frame = ctk.CTkFrame(self.theme_section, fg_color="transparent")
        self.color_frame.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.color_frame.grid_columnconfigure(1, weight=1)
        
        self.color_label = ctk.CTkLabel(
            self.color_frame,
            text="Color Theme:",
            anchor="w"
        )
        self.color_label.grid(row=0, column=0, padx=(20, 10), pady=10, sticky="w")
        
        color_theme = self.config.get("ui", {}).get("color_theme", "blue")
        self.color_var = ctk.StringVar(value=color_theme)
        self.color_options = ctk.CTkOptionMenu(
            self.color_frame,
            values=["blue", "green", "dark-blue", "purple"],
            variable=self.color_var,
            command=self._on_color_change
        )
        self.color_options.grid(row=0, column=1, padx=(0, 20), pady=10, sticky="ew")
        
        # Camera section
        self.camera_section = self._create_section_frame(self.general_scrollable, "Camera Settings")
        self.camera_section.grid(row=2, column=0, padx=20, pady=(0, 15), sticky="ew")
        
        # Camera settings
        self.camera_frame = ctk.CTkFrame(self.camera_section, fg_color="transparent")
        self.camera_frame.grid(row=0, column=0, padx=10, pady=(5, 10), sticky="ew")
        self.camera_frame.grid_columnconfigure(1, weight=1)
        
        self.camera_label = ctk.CTkLabel(
            self.camera_frame,
            text="Camera ID:",
            anchor="w"
        )
        self.camera_label.grid(row=0, column=0, padx=(20, 10), pady=10, sticky="w")
        
        camera_id = self.config.get("camera", {}).get("id", 0)
        self.camera_var = ctk.StringVar(value=str(camera_id))
        self.camera_entry = ctk.CTkEntry(
            self.camera_frame,
            textvariable=self.camera_var
        )
        self.camera_entry.grid(row=0, column=1, padx=(0, 20), pady=10, sticky="ew")
        
        # Camera resolution
        self.resolution_label = ctk.CTkLabel(
            self.camera_frame,
            text="Resolution:",
            anchor="w"
        )
        self.resolution_label.grid(row=1, column=0, padx=(20, 10), pady=10, sticky="w")
        
        resolution = self.config.get("camera", {}).get("resolution", "640x480")
        self.resolution_var = ctk.StringVar(value=resolution)
        self.resolution_options = ctk.CTkOptionMenu(
            self.camera_frame,
            values=["320x240", "640x480", "800x600", "1280x720"],
            variable=self.resolution_var
        )
        self.resolution_options.grid(row=1, column=1, padx=(0, 20), pady=10, sticky="ew")
        
        # Test camera button
        self.test_camera_button = ctk.CTkButton(
            self.camera_frame,
            text="Test Camera",
            command=self._test_camera,
            font=ctk.CTkFont(size=13),
            height=30
        )
        self.test_camera_button.grid(row=2, column=1, padx=(0, 20), pady=10, sticky="ew")
        
        # Recognition section
        self.recognition_section = self._create_section_frame(self.general_scrollable, "Face Recognition")
        self.recognition_section.grid(row=3, column=0, padx=20, pady=(0, 15), sticky="ew")
        
        # Face recognition settings
        self.recognition_frame = ctk.CTkFrame(self.recognition_section, fg_color="transparent")
        self.recognition_frame.grid(row=0, column=0, padx=10, pady=(5, 10), sticky="ew")
        self.recognition_frame.grid_columnconfigure(1, weight=1)
        
        self.method_label = ctk.CTkLabel(
            self.recognition_frame,
            text="Recognition Method:",
            anchor="w"
        )
        self.method_label.grid(row=0, column=0, padx=(20, 10), pady=10, sticky="w")
        
        method = self.config.get("face_recognition", {}).get("method", "hybrid")
        self.method_var = ctk.StringVar(value=method)
        self.method_options = ctk.CTkOptionMenu(
            self.recognition_frame,
            values=["hybrid", "haar_cascade", "dlib", "mtcnn"],
            variable=self.method_var
        )
        self.method_options.grid(row=0, column=1, padx=(0, 20), pady=10, sticky="ew")
        
        # Confidence threshold
        self.threshold_label = ctk.CTkLabel(
            self.recognition_frame,
            text="Confidence Threshold:",
            anchor="w"
        )
        self.threshold_label.grid(row=1, column=0, padx=(20, 10), pady=10, sticky="w")
        
        threshold = self.config.get("face_recognition", {}).get("threshold", 0.6)
        self.threshold_var = ctk.DoubleVar(value=threshold)
        self.threshold_slider = ctk.CTkSlider(
            self.recognition_frame,
            from_=0.1,
            to=0.95,
            variable=self.threshold_var,
            number_of_steps=17
        )
        self.threshold_slider.grid(row=1, column=1, padx=(0, 20), pady=10, sticky="ew")
        
        # Threshold value label
        self.threshold_value_label = ctk.CTkLabel(
            self.recognition_frame,
            text=f"{threshold:.2f}",
            anchor="w",
            width=30
        )
        self.threshold_value_label.grid(row=1, column=2, padx=(0, 10), pady=10, sticky="w")
        
        # Bind threshold change
        self.threshold_slider.configure(command=self._on_threshold_change)
        
        # Use multi detection checkbox
        self.multi_detection_var = ctk.BooleanVar(
            value=self.config.get("face_recognition", {}).get("multi_detection", True)
        )
        self.multi_detection_checkbox = ctk.CTkCheckBox(
            self.recognition_frame,
            text="Allow Multiple Face Detection",
            variable=self.multi_detection_var
        )
        self.multi_detection_checkbox.grid(row=2, column=0, columnspan=3, padx=20, pady=(10, 10), sticky="w")
        
        # Accessibility section
        self.accessibility_section = self._create_section_frame(self.general_scrollable, "Accessibility")
        self.accessibility_section.grid(row=4, column=0, padx=20, pady=(0, 15), sticky="ew")
        
        # Font size
        self.font_frame = ctk.CTkFrame(self.accessibility_section, fg_color="transparent")
        self.font_frame.grid(row=0, column=0, padx=10, pady=(5, 10), sticky="ew")
        self.font_frame.grid_columnconfigure(1, weight=1)
        
        self.font_label = ctk.CTkLabel(
            self.font_frame,
            text="UI Font Size:",
            anchor="w"
        )
        self.font_label.grid(row=0, column=0, padx=(20, 10), pady=10, sticky="w")
        
        font_size = self.config.get("accessibility", {}).get("font_size", "medium")
        self.font_var = ctk.StringVar(value=font_size)
        self.font_options = ctk.CTkOptionMenu(
            self.font_frame,
            values=["small", "medium", "large"],
            variable=self.font_var,
            command=self._on_font_change
        )
        self.font_options.grid(row=0, column=1, padx=(0, 20), pady=10, sticky="ew")
        
        # High contrast mode
        self.contrast_var = ctk.BooleanVar(
            value=self.config.get("accessibility", {}).get("high_contrast", False)
        )
        self.contrast_checkbox = ctk.CTkCheckBox(
            self.font_frame,
            text="High Contrast Mode",
            variable=self.contrast_var
        )
        self.contrast_checkbox.grid(row=1, column=0, columnspan=2, padx=20, pady=(5, 10), sticky="w")
        
        # Show tooltips option
        self.tooltips_var = ctk.BooleanVar(
            value=self.config.get("accessibility", {}).get("show_tooltips", True)
        )
        self.tooltips_checkbox = ctk.CTkCheckBox(
            self.font_frame,
            text="Show Tooltips",
            variable=self.tooltips_var
        )
        self.tooltips_checkbox.grid(row=2, column=0, columnspan=2, padx=20, pady=(5, 10), sticky="w")
        
        # Action buttons
        self.button_frame = ctk.CTkFrame(self.general_panel, fg_color="transparent")
        self.button_frame.grid(row=1, column=0, padx=20, pady=(10, 10), sticky="ew")
        self.button_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        # Save button
        self.save_button = ctk.CTkButton(
            self.button_frame,
            text="Save Settings",
            command=self._save_settings,
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40
        )
        self.save_button.grid(row=0, column=0, padx=(0, 5), pady=10, sticky="ew")
        
        # Reset defaults button
        self.reset_button = ctk.CTkButton(
            self.button_frame,
            text="Reset to Defaults",
            command=self._reset_defaults,
            font=ctk.CTkFont(size=14),
            height=40,
            fg_color="gray50",
            hover_color="gray30"
        )
        self.reset_button.grid(row=0, column=1, padx=5, pady=10, sticky="ew")
        
        # Cancel button
        self.cancel_button = ctk.CTkButton(
            self.button_frame,
            text="Cancel",
            command=self._cancel_changes,
            font=ctk.CTkFont(size=14),
            height=40,
            fg_color="#E74C3C",
            hover_color="#C0392B"
        )
        self.cancel_button.grid(row=0, column=2, padx=(5, 0), pady=10, sticky="ew")
        
        # Status message
        self.general_status = ctk.CTkLabel(
            self.general_panel,
            text="",
            text_color="green",
            font=ctk.CTkFont(size=12)
        )
        self.general_status.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")
        
        # Right panel: Backup settings
        self.backup_panel = ctk.CTkFrame(self)
        self.backup_panel.grid(row=0, column=1, padx=(10, 20), pady=20, sticky="nsew")
        self.backup_panel.grid_columnconfigure(0, weight=1)
        self.backup_panel.grid_rowconfigure(0, weight=1)
        
        # Scrollable frame for backup settings
        self.backup_scrollable = ctk.CTkScrollableFrame(self.backup_panel)
        self.backup_scrollable.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.backup_scrollable.grid_columnconfigure(0, weight=1)
        
        # Title
        self.backup_title = ctk.CTkLabel(
            self.backup_scrollable,
            text="Backup Settings",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.backup_title.grid(row=0, column=0, padx=20, pady=(15, 15), sticky="w")

        # Add existing backup settings here
        # ...

        # Add keyboard navigation support
        self._setup_keyboard_navigation()
    
    def _create_section_frame(self, parent, title):
        """Create a section frame with a title"""
        section = ctk.CTkFrame(parent)
        section.grid_columnconfigure(0, weight=1)
        
        # Section header
        header = ctk.CTkLabel(
            section,
            text=title,
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        )
        header.grid(row=0, column=0, padx=15, pady=(10, 0), sticky="w")
        
        # Separator
        separator = ctk.CTkFrame(section, height=1, fg_color="gray")
        separator.grid(row=1, column=0, padx=15, pady=(5, 0), sticky="ew")
        
        return section
    
    def _setup_keyboard_navigation(self):
        """Setup keyboard navigation for accessibility"""
        # Tab order setup
        # This makes the widgets focusable in a logical order
        
        # Bind Enter key for buttons
        self.save_button.bind("<Return>", lambda e: self._save_settings())
        self.reset_button.bind("<Return>", lambda e: self._reset_defaults())
        self.cancel_button.bind("<Return>", lambda e: self._cancel_changes())
        self.test_camera_button.bind("<Return>", lambda e: self._test_camera())
        
        # Set focus to the first control
        self.appearance_options.focus_set()
    
    def _on_appearance_change(self, value):
        """Handle appearance mode change"""
        # Apply the new appearance mode
        ctk.set_appearance_mode(value)
        
        # Update the config
        self.config["theme"] = value
        
        # Update toggle switch if needed
        if value != "system":
            if value == "dark":
                self.toggle_switch.select()
                self.toggle_switch.configure(text="Dark Mode")
            else:
                self.toggle_switch.deselect()
                self.toggle_switch.configure(text="Light Mode")
    
    def _on_theme_toggle(self):
        """Handle theme toggle switch"""
        # Get the new theme from the toggle variable
        theme = self.toggle_var.get()
        
        # Update the appearance mode
        ctk.set_appearance_mode(theme)
        
        # Update the dropdown to match
        self.appearance_var.set(theme)
        
        # Update toggle text
        self.toggle_switch.configure(text="Dark Mode" if theme == "dark" else "Light Mode")
        
        # Update the config
        self.config["theme"] = theme
    
    def _on_color_change(self, value):
        """Handle color theme change"""
        # Update the config
        if "ui" not in self.config:
            self.config["ui"] = {}
        self.config["ui"]["color_theme"] = value
        
        # Can't apply color theme without restarting application
        self.general_status.configure(
            text="Color theme will apply after restart",
            text_color="orange"
        )
    
    def _on_font_change(self, value):
        """Handle font size change"""
        # Update the config
        if "accessibility" not in self.config:
            self.config["accessibility"] = {}
        self.config["accessibility"]["font_size"] = value
        
        # Can't apply font size without restarting application
        self.general_status.configure(
            text="Font size will apply after restart",
            text_color="orange"
        )
    
    def _on_threshold_change(self, value):
        """Handle threshold slider change"""
        # Update the label
        self.threshold_value_label.configure(text=f"{float(value):.2f}")
    
    def _test_camera(self):
        """Test the camera with current settings"""
        try:
            import cv2
            
            # Get camera ID
            camera_id = int(self.camera_var.get())
            
            # Open camera
            cap = cv2.VideoCapture(camera_id)
            
            if not cap.isOpened():
                self.general_status.configure(
                    text=f"Error: Could not open camera {camera_id}",
                    text_color="red"
                )
                return
            
            # Get resolution
            resolution = self.resolution_var.get().split("x")
            width, height = int(resolution[0]), int(resolution[1])
            
            # Set resolution
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            
            # Capture a frame
            ret, frame = cap.read()
            
            # Close camera
            cap.release()
            
            if ret:
                self.general_status.configure(
                    text=f"Camera {camera_id} tested successfully",
                    text_color="green"
                )
            else:
                self.general_status.configure(
                    text=f"Error: Could not capture frame from camera {camera_id}",
                    text_color="red"
                )
                
        except Exception as e:
            self.general_status.configure(
                text=f"Error testing camera: {str(e)}",
                text_color="red"
            )
            logger.error(f"Camera test error: {e}")
    
    def _save_settings(self):
        """Save settings to configuration"""
        try:
            # Theme settings
            self.config["theme"] = self.appearance_var.get()
            
            if "ui" not in self.config:
                self.config["ui"] = {}
            self.config["ui"]["color_theme"] = self.color_var.get()
            
            # Camera settings
            if "camera" not in self.config:
                self.config["camera"] = {}
            self.config["camera"]["id"] = int(self.camera_var.get())
            self.config["camera"]["resolution"] = self.resolution_var.get()
            
            # Face recognition settings
            if "face_recognition" not in self.config:
                self.config["face_recognition"] = {}
            self.config["face_recognition"]["method"] = self.method_var.get()
            self.config["face_recognition"]["threshold"] = float(self.threshold_var.get())
            self.config["face_recognition"]["multi_detection"] = bool(self.multi_detection_var.get())
            
            # Accessibility settings
            if "accessibility" not in self.config:
                self.config["accessibility"] = {}
            self.config["accessibility"]["font_size"] = self.font_var.get()
            self.config["accessibility"]["high_contrast"] = bool(self.contrast_var.get())
            self.config["accessibility"]["show_tooltips"] = bool(self.tooltips_var.get())
            
            # Backup settings
            # ...
            
            # Save config
            self.config_manager.save()
            
            # Show success message
            self.general_status.configure(
                text="Settings saved successfully!",
                text_color="green"
            )
            
            # Schedule message clear
            self.after(3000, lambda: self.general_status.configure(text=""))
            
            logger.info("Settings saved")
            return True
            
        except Exception as e:
            # Show error message
            self.general_status.configure(
                text=f"Error saving settings: {str(e)}",
                text_color="red"
            )
            logger.error(f"Error saving settings: {e}")
            return False
    
    def _cancel_changes(self):
        """Cancel changes and reload settings"""
        # Reload the config
        self.config_manager = ConfigManager()
        self.config = self.config_manager.get_config()
        
        # Refresh UI with original values
        self._setup_ui()
        
        # Show message
        self.general_status.configure(
            text="Changes canceled, original settings restored",
            text_color="orange"
        )
        
        # Schedule message clear
        self.after(3000, lambda: self.general_status.configure(text=""))

    def _reset_defaults(self):
        """Reset settings to defaults"""
        # Ask for confirmation
        confirm_dialog = ctk.CTkInputDialog(
            title="Confirm Reset",
            text="Type 'reset' to confirm resetting all settings to defaults:"
        )
        result = confirm_dialog.get_input()
        
        if result != "reset":
            self.general_status.configure(
                text="Reset canceled",
                text_color="orange"
            )
            return
        
        try:
            # Reset to defaults
            default_config = {
                "theme": "system",
                "ui": {
                    "color_theme": "blue"
                },
                "camera": {
                    "id": 0,
                    "resolution": "640x480"
                },
                "face_recognition": {
                    "method": "hybrid",
                    "threshold": 0.6,
                    "multi_detection": True
                },
                "accessibility": {
                    "font_size": "medium",
                    "high_contrast": False,
                    "show_tooltips": True
                }
                # Add additional default settings
            }
            
            # Apply defaults
            self.config = default_config
            
            # Save to disk
            self.config_manager.save()
            
            # Update UI
            self._setup_ui()
            
            # Show success message
            self.general_status.configure(
                text="Settings reset to defaults",
                text_color="green"
            )
            
            # Apply appearance mode
            ctk.set_appearance_mode(default_config["theme"])
            
        except Exception as e:
            self.general_status.configure(
                text=f"Error resetting settings: {str(e)}",
                text_color="red"
            )
            logger.error(f"Error resetting settings: {e}")
    
    def _perform_backup(self):
        # Existing implementation for backup functionality
        # ...
        pass
    
    def _clean_old_backups(self):
        # Existing implementation for cleaning old backups
        # ...
        pass