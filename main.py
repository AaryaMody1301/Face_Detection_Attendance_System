#!/usr/bin/env python3
"""
Face Detection Attendance System - Main Entry Point

This module serves as the entry point for the Face Detection Attendance System,
initializing and starting the main application.
"""
import sys
import os
import traceback
import logging

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

def main():
    """Main function to start the application"""
    try:
        # Add the current directory to the Python path to resolve imports
        base_dir = os.path.dirname(os.path.abspath(__file__))
        if base_dir not in sys.path:
            sys.path.insert(0, base_dir)
        
        # Import the application
        from src.app import Application
        
        logger.info("Starting Face Detection Attendance System")
        
        # Create and start the application
        app = Application()
        app.start()
        
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
        return 0
    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.error(f"Python path: {sys.path}")
        traceback.print_exc()
        return 1
    except Exception as e:
        logger.error(f"Error starting application: {e}")
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())