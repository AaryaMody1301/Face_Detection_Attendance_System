"""
Compatibility module for Face Detection Attendance System

This module provides compatibility between the old project structure and the new one,
helping with migration by redirecting old imports to the new core modules with deprecation warnings.
"""

import sys
import warnings
import logging
import importlib.util
from functools import wraps

# Configure logging
logger = logging.getLogger(__name__)

# Dictionary mapping old import paths to new ones
IMPORT_MAPPINGS = {
    # Configuration
    "src.utils.config_manager": "src.core.utils.config_manager",
    "src.utils.app_config": "src.core.utils.config_manager",
    "src.utils.config": "src.core.utils.config_manager",
    
    # Face recognition
    "src.face_recognition.detector": "src.core.face_recognition.face_detector",
    "src.face_recognition.video_processor": "src.core.utils.video_processor",
    
    # Database
    "src.database.sqlite_handler": "src.core.database.db_handler",
    "src.database.db_manager": "src.core.database.db_handler",
}

# Classes that have been renamed
CLASS_MAPPINGS = {
    "Detector": "FaceDetector",
    "SQLiteHandler": "DatabaseHandler",
    "AppConfig": "ConfigManager",
}

def deprecated_import_warning(old_path, new_path):
    """Generate a deprecation warning for an old import path"""
    warnings.warn(
        f"Import from '{old_path}' is deprecated and will be removed in a future version. "
        f"Use '{new_path}' instead.",
        DeprecationWarning,
        stacklevel=3
    )
    logger.warning(f"Deprecated import: {old_path} -> {new_path}")

def deprecated_class_warning(old_class, new_class):
    """Generate a deprecation warning for an old class name"""
    warnings.warn(
        f"Class '{old_class}' is deprecated and will be removed in a future version. "
        f"Use '{new_class}' instead.",
        DeprecationWarning,
        stacklevel=3
    )
    logger.warning(f"Deprecated class: {old_class} -> {new_class}")

def redirect_import(old_path):
    """
    Redirect an import from an old path to a new one
    
    Args:
        old_path (str): Old import path
        
    Returns:
        module: Imported module from the new path
    """
    if old_path in IMPORT_MAPPINGS:
        new_path = IMPORT_MAPPINGS[old_path]
        deprecated_import_warning(old_path, new_path)
        
        # Import and return the new module
        return importlib.import_module(new_path)
    else:
        # If no mapping exists, try to import the original
        return importlib.import_module(old_path)

def compatibility_class_wrapper(old_class, new_class):
    """
    Create a compatibility wrapper for a renamed class
    
    Args:
        old_class (str): Old class name
        new_class (type): New class
        
    Returns:
        type: A wrapper class that inherits from the new class but has the old name
    """
    @wraps(new_class)
    def wrapped_init(self, *args, **kwargs):
        deprecated_class_warning(old_class, new_class.__name__)
        new_class.__init__(self, *args, **kwargs)
    
    # Create a new class with the old name
    wrapper_class = type(old_class, (new_class,), {"__init__": wrapped_init})
    return wrapper_class

def patch_sys_modules():
    """
    Patch sys.modules to redirect imports
    
    This function adds hooks to sys.modules for all the old import paths,
    so when code tries to import from an old path, it gets the new module with a warning.
    """
    for old_path, new_path in IMPORT_MAPPINGS.items():
        if old_path not in sys.modules and new_path not in sys.modules:
            # Only add the hook if neither module is already imported
            continue
            
        # If the new module is imported, create a reference from the old path
        if new_path in sys.modules:
            sys.modules[old_path] = sys.modules[new_path]
            logger.debug(f"Added sys.modules hook: {old_path} -> {new_path}")
        
        # If only the old module is imported, replace it with the new one
        elif old_path in sys.modules:
            try:
                new_module = importlib.import_module(new_path)
                sys.modules[old_path] = new_module
                logger.debug(f"Replaced sys.modules entry: {old_path} -> {new_path}")
            except ImportError:
                logger.error(f"Failed to import {new_path} for compatibility with {old_path}")

def setup_compatibility():
    """
    Set up compatibility features
    
    Call this function at the start of the application to enable
    all compatibility features for smooth migration.
    """
    # Enable deprecation warnings
    warnings.filterwarnings("always", category=DeprecationWarning)
    
    # Patch sys.modules
    patch_sys_modules()
    
    logger.info("Compatibility layer initialized")

# When this module is imported, automatically patch sys.modules
patch_sys_modules() 