"""
Application module that reexports the FaceAttendanceApp from src.ui.app

This module exists to maintain backward compatibility with imports from src.app
"""
import tkinter as tk
from src.ui.app import FaceAttendanceApp

class Application:
    """Main application class that initializes and starts the UI"""
    
    def __init__(self):
        """Initialize the application"""
        self.root = None
        self.app = None
    
    def start(self):
        """Start the application"""
        self.root = tk.Tk()
        self.app = FaceAttendanceApp(self.root)
        self.root.mainloop()