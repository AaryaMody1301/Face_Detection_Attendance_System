"""
Launcher for the modern UI version of Face Detection Attendance System
"""
import os
import sys
import tkinter as tk
import customtkinter as ctk
import logging

# Configure logging
logger = logging.getLogger(__name__)

def launch_modern_ui():
    """
    Launch the modern UI version of Face Detection Attendance System
    """
    try:
        # Import the modern app
        from src.ui.modern_app import ModernAttendanceApp
        
        # Create a simple authentication system for now
        # This will be replaced with a proper auth system in the future
        from src.auth.simple_auth import SimpleAuthSystem
        auth_system = SimpleAuthSystem()
        
        # Auto-login as admin for testing (will be removed in production)
        auth_system.login("admin", "admin")
        
        # Initialize and run the modern app
        app = ModernAttendanceApp(auth_system)
        app.mainloop()
        
        logger.info("Modern UI closed normally")
        return True
    except Exception as e:
        logger.error(f"Error launching modern UI: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    launch_modern_ui()