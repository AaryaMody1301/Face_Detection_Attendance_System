"""
Logging configuration for the Face Detection Attendance System

This module provides a customized logging configuration for the application
with different log levels, formatting, and output destinations.
"""

import os
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from typing import Optional, Union, Dict, Any


class Logger:
    """
    Custom logger for the Face Detection Attendance System
    
    Configures logging with file and console handlers, rotation, and custom formatting.
    """
    
    # Log levels
    LOG_LEVELS = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL
    }
    
    def __init__(
        self, 
        log_file: str = "app.log", 
        log_dir: str = "logs",
        app_name: str = "FaceAttendance",
        console_level: str = "info",
        file_level: str = "debug",
        log_format: str = "[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s"
    ):
        """
        Initialize the logger with custom configuration
        
        Args:
            log_file: Name of the log file
            log_dir: Directory to store log files
            app_name: Name of the application (used as logger name)
            console_level: Logging level for console output
            file_level: Logging level for file output
            log_format: Format string for log messages
        """
        self.app_name = app_name
        self.log_format = log_format
        
        # Ensure log directory exists
        log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True, parents=True)
        
        self.log_file = os.path.join(log_dir, log_file)
        
        # Set log levels
        self.console_level = self.LOG_LEVELS.get(console_level.lower(), logging.INFO)
        self.file_level = self.LOG_LEVELS.get(file_level.lower(), logging.DEBUG)
        
        # Create and configure the logger
        self.logger = logging.getLogger(app_name)
        self.logger.setLevel(logging.DEBUG)  # Set to lowest level, handlers will filter
        
        # Only add handlers if they don't exist
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self) -> None:
        """Set up logging handlers for file and console output"""
        # Create formatters
        formatter = logging.Formatter(self.log_format)
        
        # Configure file handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            self.log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(self.file_level)
        file_handler.setFormatter(formatter)
        
        # Configure console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.console_level)
        console_handler.setFormatter(formatter)
        
        # Add handlers to logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def get_logger(self) -> logging.Logger:
        """Get the configured logger instance"""
        return self.logger
    
    def debug(self, message: str, **kwargs) -> None:
        """Log a debug message"""
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """Log an info message"""
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log a warning message"""
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, exception: Optional[Exception] = None, **kwargs) -> None:
        """
        Log an error message with optional exception details
        
        Args:
            message: Error message to log
            exception: Optional exception to include details from
            **kwargs: Additional context to include in the log
        """
        if exception:
            # Add exception details to kwargs
            kwargs["exception_type"] = type(exception).__name__
            kwargs["exception_message"] = str(exception)
            
            # Include exception in the log message
            self._log(logging.ERROR, f"{message} - {type(exception).__name__}: {str(exception)}", **kwargs)
        else:
            self._log(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, exception: Optional[Exception] = None, **kwargs) -> None:
        """
        Log a critical message with optional exception details
        
        Args:
            message: Critical message to log
            exception: Optional exception to include details from
            **kwargs: Additional context to include in the log
        """
        if exception:
            # Add exception details to kwargs
            kwargs["exception_type"] = type(exception).__name__
            kwargs["exception_message"] = str(exception)
            
            # Include exception in the log message
            self._log(logging.CRITICAL, f"{message} - {type(exception).__name__}: {str(exception)}", **kwargs)
        else:
            self._log(logging.CRITICAL, message, **kwargs)
    
    def _log(self, level: int, message: str, **kwargs) -> None:
        """
        Internal method to handle logging with context
        
        Args:
            level: Logging level
            message: Message to log
            **kwargs: Additional context to include in the log
        """
        # Add timestamp to the context
        kwargs["timestamp"] = datetime.now().isoformat()
        
        # If there are additional context variables, include them in the log
        if kwargs:
            context_str = " | ".join(f"{k}={v}" for k, v in kwargs.items())
            self.logger.log(level, f"{message} | {context_str}")
        else:
            self.logger.log(level, message)


# Create a default logger instance
app_logger = Logger().get_logger()

# Convenience function to get a logger with a specific name
def get_logger(name: str = None) -> logging.Logger:
    """
    Get a logger with a specific name
    
    Args:
        name: Name for the logger (will be appended to app name)
        
    Returns:
        A configured logger instance
    """
    if name:
        return logging.getLogger(f"FaceAttendance.{name}")
    return app_logger