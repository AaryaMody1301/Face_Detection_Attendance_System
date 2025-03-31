"""
Compatibility module for Face Detection Attendance System

This module provides patches and fixes for compatibility issues between different
Python versions and platform-specific issues.
"""
import sys
import logging
import importlib.util
import types

logger = logging.getLogger(__name__)

def apply_python313_tkinter_patches():
    """Apply patches to make CustomTkinter compatible with Python 3.13"""
    if sys.version_info >= (3, 13):
        logger.info("Applying Python 3.13 compatibility patches for tkinter")
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
        
        logger.info("Python 3.13 tkinter patches applied successfully")

def add_missing_methods_to_faceattendanceapp():
    """Add missing methods to FaceAttendanceApp class"""
    # Import the module that contains FaceAttendanceApp
    mod_spec = importlib.util.find_spec("src.ui.app")
    if not mod_spec:
        logger.warning("Could not find the app module to patch")
        return
    
    module = importlib.util.module_from_spec(mod_spec)
    mod_spec.loader.exec_module(module)
    
    # Check if the class exists and add missing methods if needed
    if hasattr(module, 'FaceAttendanceApp'):
        cls = module.FaceAttendanceApp
        
        # Add toggle_start_button method if it's missing
        if not hasattr(cls, 'toggle_start_button'):
            logger.info("Adding missing toggle_start_button method to FaceAttendanceApp")
            
            def toggle_start_button(self):
                """
                Toggle the state of the track image button based on camera status
                This method is called when camera is started or stopped
                """
                try:
                    # Safely check if the track_img_btn attribute exists and is a widget
                    if hasattr(self, 'track_img_btn') and hasattr(self.track_img_btn, 'configure'):
                        if self.is_capturing:
                            self.track_img_btn.configure(state='normal')
                        else:
                            self.track_img_btn.configure(state='disabled')
                    
                    # Log the state change
                    logger.debug(f"Track image button state toggled, camera is {'active' if self.is_capturing else 'inactive'}")
                except Exception as e:
                    logger.error(f"Error toggling button state: {e}")
                    # Continue execution even if toggle fails
            
            # Add the method to the class
            cls.toggle_start_button = toggle_start_button
            
        # Patch start_capture and stop_capture methods to handle missing toggle_start_button
        # Get the original methods
        original_start_capture = cls.start_capture
        original_stop_capture = cls.stop_capture
        
        # Create patched versions that don't fail if toggle_start_button is missing
        def patched_start_capture(self, *args, **kwargs):
            result = original_start_capture(self, *args, **kwargs)
            
            # Safe way to toggle button state without causing errors
            try:
                if hasattr(self, 'track_img_btn') and hasattr(self.track_img_btn, 'configure'):
                    if self.is_capturing:
                        self.track_img_btn.configure(state='normal')
                    else:
                        self.track_img_btn.configure(state='disabled')
            except Exception as e:
                logger.debug(f"Failed to toggle button state during start: {e}")
                
            return result
        
        def patched_stop_capture(self, *args, **kwargs):
            result = original_stop_capture(self, *args, **kwargs)
            
            # Safe way to toggle button state without causing errors
            try:
                if hasattr(self, 'track_img_btn') and hasattr(self.track_img_btn, 'configure'):
                    self.track_img_btn.configure(state='disabled')
            except Exception as e:
                logger.debug(f"Failed to toggle button state during stop: {e}")
                
            return result
        
        # Apply the patches
        cls.start_capture = patched_start_capture
        cls.stop_capture = patched_stop_capture
        
        logger.info("FaceAttendanceApp patches applied successfully")
    else:
        logger.warning("FaceAttendanceApp class not found, could not apply patches")

def apply_all_patches():
    """Apply all compatibility patches"""
    apply_python313_tkinter_patches()
    add_missing_methods_to_faceattendanceapp()
    
    logger.info("All compatibility patches applied successfully")

# Apply patches when this module is imported
apply_all_patches()