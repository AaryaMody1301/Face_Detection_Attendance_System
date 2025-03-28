"""
Base View class for UI components in the Face Detection Attendance System
"""
import logging
import tkinter as tk
from typing import Any, Dict, Optional, Callable
import customtkinter as ctk

from ..utils.exceptions import ValidationError

class BaseView(ctk.CTkFrame):
    """
    Base class for all view components
    
    Attributes:
        controller: Associated controller instance
        logger: Logger instance
    """
    
    def __init__(self, master, controller=None, **kwargs):
        """
        Initialize the base view
        
        Args:
            master: Parent widget
            controller: Associated controller
            **kwargs: Additional arguments for CTkFrame
        """
        super().__init__(master, **kwargs)
        
        # Initialize logger
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Store controller reference
        self.controller = controller
        
        # Store configuration options
        self.config_options = {}
        
        # UI state
        self.is_loading = False
        self.loading_frame = None
    
    def setup_ui(self) -> None:
        """Set up the UI components - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement setup_ui()")
    
    def update_from_controller(self, data: Dict[str, Any] = None) -> None:
        """
        Update the view with data from the controller
        
        Args:
            data: Data from the controller to update the view
        """
        pass  # Optional implementation in subclasses
    
    def show_loading(self, message: str = "Loading...") -> None:
        """
        Show loading overlay
        
        Args:
            message: Message to display
        """
        if self.is_loading or self.loading_frame:
            return  # Already showing
            
        self.is_loading = True
        
        # Create loading overlay
        self.loading_frame = ctk.CTkFrame(self, corner_radius=10)
        self.loading_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        # Loading indicator
        loading_label = ctk.CTkLabel(
            self.loading_frame,
            text=message,
            font=ctk.CTkFont(size=16)
        )
        loading_label.pack(padx=20, pady=20)
        
        # Update UI
        self.update_idletasks()
    
    def hide_loading(self) -> None:
        """Hide loading overlay"""
        if not self.is_loading or not self.loading_frame:
            return  # Not showing
            
        self.is_loading = False
        
        # Remove loading overlay
        if self.loading_frame:
            self.loading_frame.destroy()
            self.loading_frame = None
            
        # Update UI
        self.update_idletasks()
    
    def show_error(self, message: str) -> None:
        """
        Show error message
        
        Args:
            message: Error message to display
        """
        from tkinter import messagebox
        messagebox.showerror("Error", message)
        self.logger.error(f"UI Error: {message}")
    
    def show_info(self, message: str) -> None:
        """
        Show information message
        
        Args:
            message: Information message to display
        """
        from tkinter import messagebox
        messagebox.showinfo("Information", message)
        self.logger.info(f"UI Info: {message}")
    
    def show_warning(self, message: str) -> None:
        """
        Show warning message
        
        Args:
            message: Warning message to display
        """
        from tkinter import messagebox
        messagebox.showwarning("Warning", message)
        self.logger.warning(f"UI Warning: {message}")
    
    def validate_text_input(self, value: str, required: bool = True, 
                           min_length: int = 0, max_length: int = None) -> bool:
        """
        Validate text input
        
        Args:
            value: Text value to validate
            required: Whether the field is required
            min_length: Minimum length
            max_length: Maximum length
            
        Returns:
            bool: True if valid, False otherwise
            
        Raises:
            ValidationError: If validation fails
        """
        if required and not value:
            raise ValidationError("This field is required")
            
        if value and min_length > 0 and len(value) < min_length:
            raise ValidationError(f"Must be at least {min_length} characters")
            
        if value and max_length and len(value) > max_length:
            raise ValidationError(f"Cannot be more than {max_length} characters")
            
        return True
    
    def validate_numeric_input(self, value: str, required: bool = True,
                              min_value: float = None, max_value: float = None,
                              integer_only: bool = False) -> bool:
        """
        Validate numeric input
        
        Args:
            value: Numeric value to validate
            required: Whether the field is required
            min_value: Minimum value
            max_value: Maximum value
            integer_only: Whether only integers are allowed
            
        Returns:
            bool: True if valid, False otherwise
            
        Raises:
            ValidationError: If validation fails
        """
        if required and not value:
            raise ValidationError("This field is required")
            
        if not value:
            return True
            
        try:
            if integer_only:
                # Try to convert to integer
                num_value = int(value)
                
                # Check if it's really an integer (no decimal part)
                if float(value) != num_value:
                    raise ValidationError("Must be an integer value")
            else:
                # Just convert to float
                num_value = float(value)
                
            # Check range
            if min_value is not None and num_value < min_value:
                raise ValidationError(f"Must be at least {min_value}")
                
            if max_value is not None and num_value > max_value:
                raise ValidationError(f"Cannot be more than {max_value}")
                
            return True
                
        except ValueError:
            raise ValidationError("Must be a valid number")
    
    def on_close(self) -> None:
        """Handle view closing - cleanup resources"""
        # Clean up resources when view is closed
        self.logger.info(f"Closing {self.__class__.__name__}")