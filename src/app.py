"""
Main Application class for the Face Detection Attendance System

This module provides the Application class which acts as the entry point for
the application and coordinates the initialization of components following
the MVC (Model-View-Controller) architecture.
"""
import os
import sys
import logging
import threading
import traceback
from typing import Dict, Any, Optional, List, Type, Union
import tkinter as tk

from .utils.app_config import AppConfig
from .utils.exceptions import ApplicationError, DatabaseError, ConfigError
from .database.db_manager import DatabaseManager
from .controllers.attendance_controller import AttendanceController
from .controllers.student_controller import StudentController
from .ui.modern_app import ModernAttendanceApp
from .auth.auth_system import AuthSystem

# Configure logger
logger = logging.getLogger(__name__)

class Application:
    """Main application class that initializes and coordinates all components"""
    
    def __init__(self):
        """Initialize the application components"""
        logger.info("Initializing Face Detection Attendance System")
        self.config = AppConfig()
        self.db_manager = None
        self.auth_system = None
        self.controllers = {}
        self.ui = None
        
    def start(self):
        """Start the application"""
        try:
            # Initialize database
            db_path = self.config.get("database.path", "Data/attendance.db")
            self.db_manager = DatabaseManager(db_path)
            
            # Initialize authentication system
            self.auth_system = AuthSystem(self.db_manager)
            
            # Initialize controllers
            self._init_controllers()
            
            # Initialize UI
            self._init_ui()
            
            logger.info("Application started successfully")
            
        except (ApplicationError, DatabaseError, ConfigError) as e:
            logger.error(f"Failed to start application: {e}")
            raise
            
    def _init_controllers(self):
        """Initialize all controllers"""
        self.controllers['attendance'] = AttendanceController(self.db_manager)
        self.controllers['student'] = StudentController(self.db_manager)
        
    def _init_ui(self):
        """Initialize and start the UI"""
        self.ui = ModernAttendanceApp(self.auth_system)
        self.ui.mainloop()