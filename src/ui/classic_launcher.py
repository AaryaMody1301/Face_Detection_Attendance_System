"""
Launcher for the classic UI version of Face Detection Attendance System
"""
import os
import sys
import tkinter as tk
import logging

# Configure logging
logger = logging.getLogger(__name__)

def launch_classic_ui():
    """
    Launch the classic UI version of Face Detection Attendance System
    """
    try:
        # Import the classic app
        from src.ui.app import FaceAttendanceApp
        
        # Create root Tkinter window
        root = tk.Tk()
        
        # Initialize and run the app
        app = FaceAttendanceApp(root)
        root.mainloop()
        
        logger.info("Classic UI closed normally")
        return True
    except Exception as e:
        logger.error(f"Error launching classic UI: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    launch_classic_ui()