"""
Camera settings dialog - A dedicated GUI for camera configuration
"""
import os
import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import threading
import logging
from PIL import Image, ImageTk

# Import local modules
from src.utils.camera_manager import CameraManager, VideoDisplayWidget, CameraInfo, CameraResult
from src.ui.settings import AppConfig

# Set up logging
logger = logging.getLogger(__name__)

class CameraSettingsDialog:
    """Dialog for configuring camera settings with live preview"""
    
    def __init__(self, parent, camera_manager=None, config=None):
        """
        Initialize the camera settings dialog
        
        Args:
            parent: Parent window
            camera_manager (CameraManager, optional): Camera manager instance
            config (AppConfig, optional): Application configuration
        """
        self.parent = parent
        self.camera_manager = camera_manager or CameraManager()
        self.config = config or AppConfig()
        self.video_display = None
        self.is_testing = False
        self.camera_id = self.config.get("camera.id", 0)
        self.test_thread = None
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Camera Settings")
        self.dialog.geometry("800x600")
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Handle window close
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Center the dialog on the parent window
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")
        
        # Create the UI
        self._create_widgets()
        
        # Load current settings
        self._load_current_settings()
        
        # Refresh camera list on startup
        self.refresh_cameras()
    
    def _create_widgets(self):
        """Create the dialog widgets"""
        # Main content with two columns
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left column for settings
        settings_frame = ttk.LabelFrame(main_frame, text="Camera Settings", padding="10")
        settings_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Camera selection
        camera_frame = ttk.Frame(settings_frame)
        camera_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(camera_frame, text="Camera:").grid(row=0, column=0, sticky=tk.W, pady=5)
        
        # Camera dropdown with string var to handle both string and int values
        self.camera_var = tk.StringVar()
        self.camera_combo = ttk.Combobox(camera_frame, textvariable=self.camera_var, width=40)
        self.camera_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Refresh button
        refresh_btn = ttk.Button(camera_frame, text="Refresh List", command=self.refresh_cameras)
        refresh_btn.grid(row=0, column=2, padx=5, pady=5)
        
        # Resolution
        resolution_frame = ttk.Frame(settings_frame)
        resolution_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(resolution_frame, text="Resolution:").grid(row=0, column=0, sticky=tk.W, pady=5)
        
        # Resolution presets
        self.resolution_var = tk.StringVar()
        resolution_combo = ttk.Combobox(resolution_frame, textvariable=self.resolution_var, width=15)
        resolution_combo['values'] = ("320x240", "640x480", "800x600", "1280x720", "1920x1080", "Custom")
        resolution_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # FPS
        fps_frame = ttk.Frame(settings_frame)
        fps_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(fps_frame, text="FPS:").grid(row=0, column=0, sticky=tk.W, pady=5)
        
        self.fps_var = tk.StringVar()
        fps_combo = ttk.Combobox(fps_frame, textvariable=self.fps_var, width=10)
        fps_combo['values'] = ("15", "20", "30", "60")
        fps_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Flip image horizontally
        flip_frame = ttk.Frame(settings_frame)
        flip_frame.pack(fill=tk.X, pady=5)
        
        self.flip_var = tk.BooleanVar(value=False)
        flip_check = ttk.Checkbutton(
            flip_frame, 
            text="Mirror Image (flip horizontally)", 
            variable=self.flip_var
        )
        flip_check.pack(fill=tk.X, pady=5)
        
        # Advanced options section
        advanced_frame = ttk.LabelFrame(settings_frame, text="Advanced Options", padding="10")
        advanced_frame.pack(fill=tk.X, pady=10)
        
        # Auto focus
        self.auto_focus_var = tk.BooleanVar(value=True)
        auto_focus_check = ttk.Checkbutton(
            advanced_frame, 
            text="Auto Focus (if supported)", 
            variable=self.auto_focus_var
        )
        auto_focus_check.pack(fill=tk.X, pady=5)
        
        # Auto exposure
        self.auto_exposure_var = tk.BooleanVar(value=True)
        auto_exposure_check = ttk.Checkbutton(
            advanced_frame, 
            text="Auto Exposure (if supported)", 
            variable=self.auto_exposure_var
        )
        auto_exposure_check.pack(fill=tk.X, pady=5)
        
        # Test button
        test_btn = ttk.Button(
            settings_frame,
            text="Test Camera",
            command=self.test_camera,
            width=15
        )
        test_btn.pack(pady=20)
        
        # Status label
        self.status_var = tk.StringVar(value="Ready to test camera")
        status_label = ttk.Label(
            settings_frame,
            textvariable=self.status_var,
            wraplength=300
        )
        status_label.pack(pady=10, fill=tk.X)
        
        # Right column for camera preview
        preview_frame = ttk.LabelFrame(main_frame, text="Camera Preview", padding="10")
        preview_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # Video frame container 
        video_container = ttk.Frame(preview_frame, width=400, height=300)
        video_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Fix the size of the container
        video_container.pack_propagate(False)
        
        # Create a label for displaying video frames
        self.video_label = ttk.Label(video_container, background="black")
        self.video_label.pack(fill=tk.BOTH, expand=True)
        
        # Create a default message
        self.default_message = ttk.Label(
            self.video_label,
            text="Camera preview will appear here\nClick 'Test Camera' to start",
            foreground="white",
            background="black",
            justify="center"
        )
        self.default_message.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        # Button frame at the bottom
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, pady=10, padx=10)
        
        # Reset button
        reset_btn = ttk.Button(
            button_frame,
            text="Reset to Defaults",
            command=self._reset_to_defaults,
        )
        reset_btn.pack(side=tk.LEFT, padx=5)
        
        # Save button
        save_btn = ttk.Button(
            button_frame,
            text="Apply & Save",
            command=self._save_settings,
            style="Accent.TButton"
        )
        save_btn.pack(side=tk.RIGHT, padx=5)
        
        # Cancel button
        cancel_btn = ttk.Button(
            button_frame,
            text="Cancel",
            command=self.dialog.destroy
        )
        cancel_btn.pack(side=tk.RIGHT, padx=5)
        
        # Bind resolution change
        def on_resolution_selected(event):
            if self.resolution_var.get() == "Custom":
                # Open a dialog to enter custom resolution
                self._custom_resolution_dialog()
                
        resolution_combo.bind("<<ComboboxSelected>>", on_resolution_selected)
        
        # Add styles if supported by Tkinter version
        try:
            self.dialog.tk.call("source", "azure.tcl")
            self.dialog.tk.call("set_theme", "light")
            style = ttk.Style()
            style.configure("Accent.TButton", font=("Arial", 10, "bold"))
        except:
            pass
    
    def _custom_resolution_dialog(self):
        """Open a dialog to set custom resolution"""
        # Extract current resolution
        current_res = self.resolution_var.get()
        if current_res != "Custom" and "x" in current_res:
            try:
                width, height = map(int, current_res.split("x"))
            except:
                width, height = 640, 480
        else:
            width, height = 640, 480
        
        # Create a dialog
        dialog = tk.Toplevel(self.dialog)
        dialog.title("Custom Resolution")
        dialog.geometry("300x150")
        dialog.resizable(False, False)
        dialog.transient(self.dialog)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = self.dialog.winfo_x() + (self.dialog.winfo_width() - dialog.winfo_width()) // 2
        y = self.dialog.winfo_y() + (self.dialog.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        
        # Frame for content
        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Width
        ttk.Label(frame, text="Width:").grid(row=0, column=0, sticky=tk.W, pady=5)
        width_var = tk.IntVar(value=width)
        width_entry = ttk.Entry(frame, textvariable=width_var, width=10)
        width_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # Height
        ttk.Label(frame, text="Height:").grid(row=1, column=0, sticky=tk.W, pady=5)
        height_var = tk.IntVar(value=height)
        height_entry = ttk.Entry(frame, textvariable=height_var, width=10)
        height_entry.grid(row=1, column=1, padx=5, pady=5)
        
        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        def on_ok():
            try:
                w = width_var.get()
                h = height_var.get()
                if w > 0 and h > 0:
                    self.resolution_var.set(f"{w}x{h}")
                    dialog.destroy()
            except:
                messagebox.showerror("Invalid Input", "Please enter valid positive integers.")
        
        ttk.Button(button_frame, text="OK", command=on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        # Focus width entry
        width_entry.focus_set()
    
    def _load_current_settings(self):
        """Load current camera settings"""
        # Load camera ID
        self.camera_id = self.config.get("camera.id", 0)
        
        # Load resolution
        resolution = self.config.get("camera.resolution", [640, 480])
        self.resolution_var.set(f"{resolution[0]}x{resolution[1]}")
        
        # Load FPS
        fps = self.config.get("camera.fps", 30)
        self.fps_var.set(str(fps))
        
        # Load flip setting
        self.flip_var.set(self.config.get("camera.flip_image", False))
        
        # Load advanced settings
        self.auto_focus_var.set(self.config.get("camera.auto_focus", True))
        self.auto_exposure_var.set(self.config.get("camera.auto_exposure", True))
    
    def refresh_cameras(self):
        """Refresh the list of available cameras"""
        try:
            # Set status
            self.status_var.set("Refreshing camera list...")
            
            # Refresh cameras
            cameras = self.camera_manager.refresh_cameras()
            
            # Clear and update camera dropdown
            self.camera_combo['values'] = []
            camera_options = ["Auto-detect (default)"]
            
            # Add each camera
            for camera in cameras:
                camera_name = f"Camera {camera.index}: {camera.name}"
                camera_options.append(camera_name)
            
            # If no cameras found, add some placeholders
            if len(camera_options) == 1:
                camera_options.extend(["Camera 0", "Camera 1"])
            
            # Update combobox
            self.camera_combo['values'] = camera_options
            
            # Select current camera if possible
            if self.camera_id >= 0 and self.camera_id < len(cameras):
                self.camera_var.set(f"Camera {self.camera_id}: {cameras[self.camera_id].name}")
            else:
                self.camera_var.set(camera_options[0])
            
            # Update status
            self.status_var.set(f"Found {len(cameras)} camera(s). Select a camera and click 'Test Camera'.")
            
        except Exception as e:
            self.status_var.set(f"Error refreshing cameras: {str(e)}")
            logger.exception(f"Error refreshing cameras: {e}")
    
    def test_camera(self):
        """Test the selected camera with the current settings"""
        try:
            # If already testing, stop the test
            if self.is_testing:
                self._stop_camera_test()
                return
            
            # Get selected camera ID
            selected_camera = self.camera_var.get()
            if "Auto-detect" in selected_camera:
                camera_id = 0  # Use default camera
            else:
                # Extract camera ID from the string (Camera X: Name)
                try:
                    camera_id = int(selected_camera.split(":")[0].replace("Camera", "").strip())
                except:
                    camera_id = 0
            
            # Get resolution
            resolution_str = self.resolution_var.get()
            try:
                width, height = map(int, resolution_str.split("x"))
            except:
                width, height = 640, 480
            
            # Get FPS
            try:
                fps = int(self.fps_var.get())
            except:
                fps = 30
            
            # Get flip setting
            flip = self.flip_var.get()
            
            self.status_var.set(f"Testing camera {camera_id} with resolution {width}x{height} @ {fps}fps...")
            
            # Start camera test in a separate thread
            self.test_thread = threading.Thread(
                target=self._run_camera_test,
                args=(camera_id, width, height, fps, flip),
                daemon=True
            )
            self.test_thread.start()
            
        except Exception as e:
            self.status_var.set(f"Error testing camera: {str(e)}")
            logger.exception(f"Error testing camera: {e}")
    
    def _run_camera_test(self, camera_id, width, height, fps, flip):
        """Run camera test in a background thread"""
        try:
            # Signal that we're testing
            self.is_testing = True
            
            # Set up camera with the specified settings
            camera_manager = CameraManager(camera_id=camera_id, resolution=(width, height))
            camera_manager.flip_horizontal = flip
            
            # Try to connect
            if not camera_manager.connect():
                self.status_var.set(f"Failed to connect to camera {camera_id}. Please try another camera.")
                self.is_testing = False
                return
            
            # Set up video display
            self.video_display = VideoDisplayWidget(self.video_label, camera_manager, update_interval=1000//fps)
            
            # Remove default message
            self.default_message.place_forget()
            
            # Start video display
            self.video_display.start()
            
            # Update status with actual camera properties
            camera_info = camera_manager.get_camera_info()
            if camera_info["status"] == "connected":
                actual_width, actual_height = camera_info["resolution"]
                actual_fps = camera_info["fps"]
                self.status_var.set(
                    f"Camera {camera_id} connected successfully! "
                    f"Actual resolution: {actual_width}x{actual_height} @ {actual_fps:.1f}fps. "
                    f"Click 'Test Camera' again to stop."
                )
            else:
                self.status_var.set(f"Camera {camera_id} is connected, but couldn't get properties.")
                
        except Exception as e:
            self.status_var.set(f"Error testing camera: {str(e)}")
            logger.exception(f"Error in camera test thread: {e}")
            self.is_testing = False
    
    def _stop_camera_test(self):
        """Stop the camera test and clean up resources"""
        try:
            if self.video_display is not None:
                self.video_display.stop()
                self.video_display = None
            
            # Show default message again
            self.default_message.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
            
            # Reset status
            self.status_var.set("Camera test stopped. Ready to test again.")
            
            # Reset testing flag
            self.is_testing = False
            
        except Exception as e:
            self.status_var.set(f"Error stopping camera: {str(e)}")
            logger.exception(f"Error stopping camera: {e}")
    
    def _save_settings(self):
        """Save camera settings to config and close dialog"""
        try:
            # Stop any running camera test
            if self.is_testing:
                self._stop_camera_test()
            
            # Get selected camera ID
            selected_camera = self.camera_var.get()
            if "Auto-detect" in selected_camera:
                camera_id = 0
            else:
                try:
                    camera_id = int(selected_camera.split(":")[0].replace("Camera", "").strip())
                except:
                    camera_id = 0
            
            # Get resolution
            resolution_str = self.resolution_var.get()
            try:
                width, height = map(int, resolution_str.split("x"))
                resolution = [width, height]
            except:
                resolution = [640, 480]
            
            # Get FPS
            try:
                fps = int(self.fps_var.get())
            except:
                fps = 30
                
            # Get other settings
            flip_image = self.flip_var.get()
            auto_focus = self.auto_focus_var.get()
            auto_exposure = self.auto_exposure_var.get()
            
            # Update config
            self.config.set("camera.id", camera_id)
            self.config.set("camera.resolution", resolution)
            self.config.set("camera.fps", fps)
            self.config.set("camera.flip_image", flip_image)
            self.config.set("camera.auto_focus", auto_focus)
            self.config.set("camera.auto_exposure", auto_exposure)
            
            # Save to file
            if self.config.save_config():
                messagebox.showinfo("Camera Settings", "Camera settings saved successfully!")
                
                # Update camera manager if it exists
                if hasattr(self, 'camera_manager') and self.camera_manager:
                    self.camera_manager.set_preferred_settings(
                        camera_id=camera_id,
                        resolution=resolution,
                        fps=fps,
                        flip=flip_image
                    )
                
                # Close the dialog
                self.dialog.destroy()
            else:
                messagebox.showerror("Error", "Failed to save camera settings")
                
        except Exception as e:
            messagebox.showerror("Error", f"Error saving settings: {str(e)}")
            logger.exception(f"Error saving camera settings: {e}")
    
    def _reset_to_defaults(self):
        """Reset camera settings to defaults"""
        if messagebox.askyesno("Reset Settings", "Are you sure you want to reset the camera settings to defaults?"):
            # Default values
            self.camera_var.set("Auto-detect (default)")
            self.resolution_var.set("640x480")
            self.fps_var.set("30")
            self.flip_var.set(False)
            self.auto_focus_var.set(True)
            self.auto_exposure_var.set(True)
            
            self.status_var.set("Settings reset to defaults. Click 'Apply & Save' to save changes.")
    
    def on_closing(self):
        """Handle window closing event"""
        # Stop any running camera test
        if self.is_testing:
            self._stop_camera_test()
            
        # Close the dialog
        self.dialog.destroy()


# For standalone testing
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Test Camera Settings Dialog")
    root.geometry("300x200")
    
    def open_dialog():
        dialog = CameraSettingsDialog(root)
    
    ttk.Button(root, text="Open Camera Settings", command=open_dialog).pack(padx=20, pady=20)
    
    root.mainloop()