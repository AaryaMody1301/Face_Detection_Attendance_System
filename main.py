#!/usr/bin/env python3
"""
Face Detection Attendance System - Main Entry Point

This module serves as the entry point for the Face Detection Attendance System,
initializing and starting the main application with a choice of UI.
"""
import sys
import os
import traceback
import logging
import tkinter as tk
import customtkinter as ctk
import cv2
import threading
import time
import json
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "app.log"))
    ]
)
logger = logging.getLogger(__name__)

# Ensure the logs directory exists
os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs"), exist_ok=True)

# Create other necessary directories
REQUIRED_DIRS = ["TrainingImage", "TrainingImageLabel", "Attendance", "Data", "StudentDetails", "backups", "config"]
for directory in REQUIRED_DIRS:
    os.makedirs(directory, exist_ok=True)

def check_dependencies():
    """Check if all required libraries are available"""
    try:
        # Check OpenCV
        cv2_version = cv2.__version__
        logger.info(f"OpenCV version: {cv2_version}")
        
        # Check for face_recognition
        try:
            import face_recognition
            logger.info("face_recognition library is available")
        except ImportError:
            logger.warning("face_recognition library is not available. Using fallback methods.")
            
        # Check CustomTkinter
        ctk_version = ctk.__version__
        logger.info(f"CustomTkinter version: {ctk_version}")
        
        # Check for dlib
        try:
            import dlib
            logger.info(f"dlib version: {dlib.__version__}")
        except ImportError:
            logger.warning("dlib library is not available. Face recognition may have limited functionality.")
            
        return True
    except Exception as e:
        logger.error(f"Dependency check failed: {e}")
        return False

def show_splash_screen():
    """Show a splash screen while the app is loading"""
    # Create root window
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    
    # Create the splash screen
    splash = tk.Toplevel(root)
    splash.title("Loading...")
    
    # Set window position to center of screen
    screen_width = splash.winfo_screenwidth()
    screen_height = splash.winfo_screenheight()
    width = 400
    height = 300
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    splash.geometry(f"{width}x{height}+{x}+{y}")
    
    # Remove window decorations
    splash.overrideredirect(True)
    
    # Set background color
    splash.configure(bg="#2d3436")
    
    # Add app name
    tk.Label(
        splash, 
        text="Face Detection Attendance System", 
        font=("Arial", 16, "bold"),
        bg="#2d3436",
        fg="white"
    ).pack(pady=(50, 20))
    
    # Add loading message
    message_var = tk.StringVar(value="Loading components...")
    message_label = tk.Label(
        splash, 
        textvariable=message_var,
        font=("Arial", 10),
        bg="#2d3436",
        fg="white"
    )
    message_label.pack(pady=10)
    
    # Add progress bar
    progress_var = tk.DoubleVar()
    progress = tk.ttk.Progressbar(
        splash, 
        orient="horizontal", 
        length=300,
        mode="determinate", 
        variable=progress_var
    )
    progress.pack(pady=20)
    
    # Update function for loading sequence
    def update_splash(step=0, max_steps=5):
        steps = [
            "Checking dependencies...",
            "Initializing database...",
            "Loading face detection models...",
            "Preparing user interface...",
            "Starting application..."
        ]
        
        if step < max_steps:
            # Update message and progress
            message_var.set(steps[step])
            progress_var.set((step + 1) / max_steps * 100)
            splash.update()
            # Schedule next update
            splash.after(800, lambda: update_splash(step + 1, max_steps))
        else:
            # Finish splash screen
            splash.destroy()
            root.destroy()
    
    # Start the update sequence
    splash.after(200, update_splash)
    
    # Run the splash screen
    root.mainloop()

def main():
    """Main function to start the application"""
    try:
        # Show splash screen first
        show_splash_screen()
        
        # Add the current directory to the Python path to resolve imports
        base_dir = os.path.dirname(os.path.abspath(__file__))
        if base_dir not in sys.path:
            sys.path.insert(0, base_dir)
        
        # Check dependencies
        if not check_dependencies():
            logger.error("Required dependencies are missing or incompatible")
            return 1
        
        # Check for models directory and required face detection models
        models_dir = os.path.join(base_dir, "models")
        if not os.path.exists(models_dir):
            os.makedirs(models_dir, exist_ok=True)
            logger.info("Created models directory")
        
        # Show UI selector to let user choose which UI to use
        from src.ui.ui_selector import select_ui
        ui_type = select_ui()
        
        logger.info(f"Selected UI type: {ui_type}")
        
        # Start the appropriate UI
        if ui_type.lower() == "modern":
            try:
                # Import modern UI
                from src.ui.modern_launcher import launch_modern_ui
                launch_modern_ui()
            except ImportError as e:
                logger.error(f"Failed to import modern UI: {e}")
                # Fall back to classic UI
                from src.ui.classic_launcher import launch_classic_ui
                launch_classic_ui()
        else:
            # Use classic UI
            from src.ui.classic_launcher import launch_classic_ui
            launch_classic_ui()
        
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
        return 0
    except Exception as e:
        logger.error(f"Error starting application: {e}")
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())