"""
Settings Page for Face Detection Attendance System
"""
import os
import logging
import tkinter as tk
import customtkinter as ctk
from PIL import Image

from src.utils.config_manager import ConfigManager
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
        
        # Title
        self.general_title = ctk.CTkLabel(
            self.general_panel,
            text="General Settings",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.general_title.grid(row=0, column=0, padx=20, pady=(15, 15), sticky="w")
        
        # Appearance mode
        self.appearance_frame = ctk.CTkFrame(self.general_panel)
        self.appearance_frame.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")
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
        
        # Camera settings
        self.camera_frame = ctk.CTkFrame(self.general_panel)
        self.camera_frame.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")
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
        
        # Face recognition settings
        self.recognition_frame = ctk.CTkFrame(self.general_panel)
        self.recognition_frame.grid(row=3, column=0, padx=20, pady=(0, 10), sticky="ew")
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
        
        # Save button
        self.save_button = ctk.CTkButton(
            self.general_panel,
            text="Save Settings",
            command=self._save_settings,
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40
        )
        self.save_button.grid(row=4, column=0, padx=20, pady=(20, 10), sticky="ew")
        
        # Status message
        self.general_status = ctk.CTkLabel(
            self.general_panel,
            text="",
            text_color="green",
            font=ctk.CTkFont(size=12)
        )
        self.general_status.grid(row=5, column=0, padx=20, pady=(0, 10), sticky="ew")
        
        # Right panel: Backup settings
        self.backup_panel = ctk.CTkFrame(self)
        self.backup_panel.grid(row=0, column=1, padx=(10, 20), pady=20, sticky="nsew")
        self.backup_panel.grid_columnconfigure(0, weight=1)
        
        # Title
        self.backup_title = ctk.CTkLabel(
            self.backup_panel,
            text="Backup Settings",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.backup_title.grid(row=0, column=0, padx=20, pady=(15, 15), sticky="w")
        
        # Auto backup
        self.auto_backup_frame = ctk.CTkFrame(self.backup_panel)
        self.auto_backup_frame.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.auto_backup_frame.grid_columnconfigure(1, weight=1)
        
        self.auto_backup_label = ctk.CTkLabel(
            self.auto_backup_frame,
            text="Automatic Backup:",
            anchor="w"
        )
        self.auto_backup_label.grid(row=0, column=0, padx=(20, 10), pady=10, sticky="w")
        
        auto_backup = self.config.get("backup", {}).get("auto_backup", True)
        self.auto_backup_var = ctk.BooleanVar(value=auto_backup)
        self.auto_backup_switch = ctk.CTkSwitch(
            self.auto_backup_frame,
            text="",
            variable=self.auto_backup_var
        )
        self.auto_backup_switch.grid(row=0, column=1, padx=(0, 20), pady=10, sticky="w")
        
        # Backup frequency
        self.frequency_label = ctk.CTkLabel(
            self.auto_backup_frame,
            text="Backup Frequency (days):",
            anchor="w"
        )
        self.frequency_label.grid(row=1, column=0, padx=(20, 10), pady=10, sticky="w")
        
        frequency = self.config.get("backup", {}).get("frequency_days", 7)
        self.frequency_var = ctk.IntVar(value=frequency)
        self.frequency_options = ctk.CTkOptionMenu(
            self.auto_backup_frame,
            values=["1", "3", "7", "14", "30"],
            variable=self.frequency_var
        )
        self.frequency_options.grid(row=1, column=1, padx=(0, 20), pady=10, sticky="w")
        
        # Manual backup button
        self.backup_button = ctk.CTkButton(
            self.backup_panel,
            text="Perform Backup Now",
            command=self._perform_backup,
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40
        )
        self.backup_button.grid(row=2, column=0, padx=20, pady=(20, 10), sticky="ew")
        
        # Clean old backups button
        self.clean_button = ctk.CTkButton(
            self.backup_panel,
            text="Clean Old Backups (>30 days)",
            command=self._clean_old_backups,
            font=ctk.CTkFont(size=14),
            height=40
        )
        self.clean_button.grid(row=3, column=0, padx=20, pady=(10, 10), sticky="ew")
        
        # Backup status
        self.backup_status = ctk.CTkLabel(
            self.backup_panel,
            text="",
            text_color="green",
            font=ctk.CTkFont(size=12)
        )
        self.backup_status.grid(row=4, column=0, padx=20, pady=(0, 10), sticky="ew")
        
        # Database location
        self.db_frame = ctk.CTkFrame(self.backup_panel)
        self.db_frame.grid(row=5, column=0, padx=20, pady=(10, 10), sticky="ew")
        self.db_frame.grid_columnconfigure(1, weight=1)
        
        self.db_label = ctk.CTkLabel(
            self.db_frame,
            text="Database Location:",
            anchor="w"
        )
        self.db_label.grid(row=0, column=0, padx=(20, 10), pady=10, sticky="w")
        
        db_path = self.config.get("database", {}).get("path", "Data/attendance.db")
        self.db_var = ctk.StringVar(value=db_path)
        self.db_entry = ctk.CTkEntry(
            self.db_frame,
            textvariable=self.db_var,
            width=200
        )
        self.db_entry.grid(row=0, column=1, padx=(0, 20), pady=10, sticky="ew")
        
        # Reset to defaults button
        self.reset_button = ctk.CTkButton(
            self.backup_panel,
            text="Reset to Default Settings",
            command=self._reset_defaults,
            font=ctk.CTkFont(size=14),
            fg_color="#FF5722",
            hover_color="#E64A19"
        )
        self.reset_button.grid(row=6, column=0, padx=20, pady=(20, 10), sticky="ew")
    
    def _on_appearance_change(self, value):
        """
        Handle appearance mode change
        
        Args:
            value: New appearance mode
        """
        ctk.set_appearance_mode(value)
    
    def _on_threshold_change(self, value):
        """
        Handle threshold slider change
        
        Args:
            value: New threshold value
        """
        self.threshold_value_label.configure(text=f"{value:.2f}")
    
    def _save_settings(self):
        """Save settings to configuration file"""
        try:
            # Prepare new config
            new_config = {
                "theme": self.appearance_var.get(),
                "face_recognition": {
                    "threshold": self.threshold_var.get(),
                    "method": self.method_var.get()
                },
                "camera": {
                    "id": int(self.camera_var.get()),
                    "resolution": self.resolution_var.get()
                },
                "database": {
                    "path": self.db_var.get()
                },
                "backup": {
                    "auto_backup": self.auto_backup_var.get(),
                    "frequency_days": int(self.frequency_var.get())
                }
            }
            
            # Save to config file
            if self.config_manager.update_config(new_config):
                logger.info("Settings saved successfully")
                self.general_status.configure(text="Settings saved successfully", text_color="green")
                
                # Schedule reset of status message
                self.after(3000, lambda: self.general_status.configure(text=""))
            else:
                logger.error("Failed to save settings")
                self.general_status.configure(text="Failed to save settings", text_color="red")
        
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            self.general_status.configure(text=f"Error: {str(e)}", text_color="red")
    
    def _perform_backup(self):
        """Perform manual backup"""
        try:
            # Update backup button state
            self.backup_button.configure(text="Backing up...", state="disabled")
            
            # Perform backup
            result = self.backup_manager.perform_backup()
            
            # Update status
            if result.success:
                logger.info("Manual backup completed successfully")
                self.backup_status.configure(text="Backup completed successfully", text_color="green")
            else:
                logger.error(f"Backup failed: {result.message}")
                self.backup_status.configure(text=f"Backup failed: {result.message}", text_color="red")
            
            # Reset button
            self.backup_button.configure(text="Perform Backup Now", state="normal")
            
            # Schedule reset of status message
            self.after(5000, lambda: self.backup_status.configure(text=""))
        
        except Exception as e:
            logger.error(f"Error performing backup: {e}")
            self.backup_status.configure(text=f"Error: {str(e)}", text_color="red")
            self.backup_button.configure(text="Perform Backup Now", state="normal")
    
    def _clean_old_backups(self):
        """Clean old backup files"""
        try:
            # Update button state
            self.clean_button.configure(text="Cleaning...", state="disabled")
            
            # Clean old backups
            result = self.backup_manager.clean_old_backups(max_days=30)
            
            # Update status
            if result.success:
                logger.info("Old backups cleaned successfully")
                self.backup_status.configure(text=result.message, text_color="green")
            else:
                logger.error(f"Cleaning backups failed: {result.message}")
                self.backup_status.configure(text=f"Cleaning failed: {result.message}", text_color="red")
            
            # Reset button
            self.clean_button.configure(text="Clean Old Backups (>30 days)", state="normal")
            
            # Schedule reset of status message
            self.after(5000, lambda: self.backup_status.configure(text=""))
        
        except Exception as e:
            logger.error(f"Error cleaning backups: {e}")
            self.backup_status.configure(text=f"Error: {str(e)}", text_color="red")
            self.clean_button.configure(text="Clean Old Backups (>30 days)", state="normal")
    
    def _reset_defaults(self):
        """Reset all settings to defaults"""
        # Show confirmation dialog
        confirm = ctk.CTkInputDialog(
            title="Confirm Reset",
            text="Type 'RESET' to confirm resetting all settings to defaults:"
        )
        user_input = confirm.get_input()
        
        if user_input == "RESET":
            try:
                # Reset config to defaults
                if self.config_manager.restore_defaults():
                    # Reload config
                    self.config = self.config_manager.get_config()
                    
                    # Update UI elements
                    self.appearance_var.set(self.config.get("theme", "system"))
                    ctk.set_appearance_mode(self.config.get("theme", "system"))
                    
                    self.camera_var.set(str(self.config.get("camera", {}).get("id", 0)))
                    self.resolution_var.set(self.config.get("camera", {}).get("resolution", "640x480"))
                    
                    self.method_var.set(self.config.get("face_recognition", {}).get("method", "hybrid"))
                    self.threshold_var.set(self.config.get("face_recognition", {}).get("threshold", 0.6))
                    self.threshold_value_label.configure(text=f"{self.threshold_var.get():.2f}")
                    
                    self.auto_backup_var.set(self.config.get("backup", {}).get("auto_backup", True))
                    self.frequency_var.set(str(self.config.get("backup", {}).get("frequency_days", 7)))
                    
                    self.db_var.set(self.config.get("database", {}).get("path", "Data/attendance.db"))
                    
                    logger.info("Settings reset to defaults")
                    self.backup_status.configure(text="Settings reset to defaults", text_color="green")
                    
                    # Schedule reset of status message
                    self.after(5000, lambda: self.backup_status.configure(text=""))
                else:
                    logger.error("Failed to reset settings")
                    self.backup_status.configure(text="Failed to reset settings", text_color="red")
            
            except Exception as e:
                logger.error(f"Error resetting settings: {e}")
                self.backup_status.configure(text=f"Error: {str(e)}", text_color="red")
        
        else:
            logger.info("Reset canceled by user")