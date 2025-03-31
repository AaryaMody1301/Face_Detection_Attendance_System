"""
Application module that reexports the FaceAttendanceApp from src.ui.app

This module exists to maintain backward compatibility with imports from src.app
"""
import tkinter as tk
import logging
import sys

# Set up logger
logger = logging.getLogger(__name__)

# Add Python 3.13 compatibility for CustomTkinter
if sys.version_info >= (3, 13):
    logger.info("Python 3.13+ detected, applying CustomTkinter compatibility patches")
    import tkinter
    
    # Add missing methods to avoid AttributeError
    def block_update_dimensions_event(self):
        pass
        
    def unblock_update_dimensions_event(self):
        pass
    
    # Monkey patch Tk and Toplevel classes with missing methods
    tkinter.Tk.block_update_dimensions_event = block_update_dimensions_event
    tkinter.Tk.unblock_update_dimensions_event = unblock_update_dimensions_event
    tkinter.Toplevel.block_update_dimensions_event = block_update_dimensions_event
    tkinter.Toplevel.unblock_update_dimensions_event = unblock_update_dimensions_event

try:
    from src.ui.app import FaceAttendanceApp
except ImportError as e:
    logger.error(f"Error importing FaceAttendanceApp: {e}")
    raise

class Application:
    """Main application class that initializes and starts the UI"""
    
    def __init__(self):
        """Initialize the application"""
        self.root = None
        self.app = None
    
    def start(self):
        """Start the application"""
        logger.info("Initializing application")
        self.root = tk.Tk()
        self.app = FaceAttendanceApp(self.root)
        logger.info("Starting main event loop")
        self.root.mainloop()