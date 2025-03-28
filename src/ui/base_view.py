"""
Base View for the Face Detection Attendance System

This module provides the base view class that all other views inherit from.
"""
import logging
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from typing import Optional, Callable, Dict, Any, Union

class BaseView(ctk.CTkFrame):
    """
    Base view class for all views in the application
    
    This class provides common functionality used by all views:
    - Logging
    - Message dialogs
    - Loading overlay
    - Common layout helpers
    
    All views should inherit from this class.
    """
    
    def __init__(
        self, 
        master,
        width: int = 1024,
        height: int = 768,
        **kwargs
    ):
        """
        Initialize base view
        
        Args:
            master: Parent widget
            width: View width
            height: View height
            **kwargs: Additional arguments for CTkFrame
        """
        # Setup logger for this class
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Initialize frame
        super().__init__(master, width=width, height=height, **kwargs)
        
        # Store references
        self.master = master
        self.width = width
        self.height = height
        
        # Loading overlay
        self._loading_overlay = None
        self._loading_label = None
        self._loading_spinner = None
        self._loading_message = tk.StringVar(value="Loading...")
    
    def show_info(self, message: str, title: str = "Information"):
        """
        Show information message dialog
        
        Args:
            message: Message to show
            title: Dialog title
        """
        # In themed CTk style
        messagebox.showinfo(title, message)
    
    def show_warning(self, message: str, title: str = "Warning"):
        """
        Show warning message dialog
        
        Args:
            message: Message to show
            title: Dialog title
        """
        messagebox.showwarning(title, message)
    
    def show_error(self, message: str, title: str = "Error"):
        """
        Show error message dialog
        
        Args:
            message: Message to show
            title: Dialog title
        """
        messagebox.showerror(title, message)
    
    def show_confirmation(
        self, 
        message: str, 
        title: str = "Confirmation", 
        on_yes: Optional[Callable] = None,
        on_no: Optional[Callable] = None
    ):
        """
        Show confirmation dialog
        
        Args:
            message: Message to show
            title: Dialog title
            on_yes: Callback for Yes button
            on_no: Callback for No button
            
        Returns:
            True if Yes was clicked, False otherwise
        """
        result = messagebox.askyesno(title, message)
        
        if result and on_yes:
            on_yes()
        elif not result and on_no:
            on_no()
            
        return result
    
    def show_input(
        self, 
        message: str, 
        title: str = "Input", 
        initial_value: str = ""
    ) -> Optional[str]:
        """
        Show input dialog
        
        Args:
            message: Message to show
            title: Dialog title
            initial_value: Initial value for input
            
        Returns:
            Input value or None if canceled
        """
        return messagebox.askstring(title, message, initialvalue=initial_value)
    
    def show_success(self, message: str, title: str = "Success"):
        """
        Show success message dialog
        
        Args:
            message: Message to show
            title: Dialog title
        """
        messagebox.showinfo(title, message)
    
    def show_loading(self, message: str = "Loading..."):
        """
        Show loading overlay
        
        Args:
            message: Loading message
        """
        if self._loading_overlay is not None:
            # Already showing, just update message
            self._loading_message.set(message)
            return
            
        # Create overlay
        self._loading_overlay = ctk.CTkFrame(self, fg_color=("#FFFFFF80", "#00000080"))
        self._loading_overlay.place(relx=0.5, rely=0.5, anchor="center", relwidth=1, relheight=1)
        
        # Create loading container
        loading_container = ctk.CTkFrame(self._loading_overlay)
        loading_container.place(relx=0.5, rely=0.5, anchor="center")
        
        # Create loading spinner (placeholder - use actual spinner in real implementation)
        self._loading_spinner = ctk.CTkLabel(loading_container, text="⟳", font=ctk.CTkFont(size=36))
        self._loading_spinner.pack(pady=10)
        
        # Start spinner animation (just a simple animation for this example)
        self._animate_spinner()
        
        # Create loading label
        self._loading_message.set(message)
        self._loading_label = ctk.CTkLabel(
            loading_container,
            textvariable=self._loading_message,
            font=ctk.CTkFont(size=16)
        )
        self._loading_label.pack(pady=10)
        
        # Force update
        self.update_idletasks()
    
    def hide_loading(self):
        """Hide loading overlay"""
        if self._loading_overlay is not None:
            self._loading_overlay.destroy()
            self._loading_overlay = None
            self._loading_label = None
            self._loading_spinner = None
    
    def _animate_spinner(self):
        """Animate loading spinner"""
        if self._loading_spinner is None:
            return
            
        # Get current text
        current_text = self._loading_spinner.cget("text")
        
        # Rotate spinner character
        spinner_chars = "⟳⟲"
        next_index = (spinner_chars.index(current_text) + 1) % len(spinner_chars)
        self._loading_spinner.configure(text=spinner_chars[next_index])
        
        # Schedule next animation frame
        self.after(250, self._animate_spinner)
    
    def refresh(self):
        """
        Refresh view data
        
        Override in subclasses to refresh data displayed in the view.
        """
        pass
    
    def on_close(self):
        """
        Clean up resources when view is closed
        
        Override in subclasses to perform cleanup when view is closed.
        """
        # Default implementation - nothing to clean up
        pass

    def create_scrollable_frame(self, master=None, **kwargs):
        """
        Create a scrollable frame
        
        Args:
            master: Parent widget (default: self)
            **kwargs: Additional arguments for CTkScrollableFrame
            
        Returns:
            Scrollable frame widget
        """
        if master is None:
            master = self
            
        return ctk.CTkScrollableFrame(master, **kwargs)
    
    def create_section_header(self, parent, text, **kwargs):
        """
        Create a section header
        
        Args:
            parent: Parent widget
            text: Header text
            **kwargs: Additional arguments for CTkLabel
            
        Returns:
            Header label widget
        """
        default_kwargs = {
            "font": ctk.CTkFont(size=16, weight="bold"),
            "anchor": "w"
        }
        default_kwargs.update(kwargs)
        
        label = ctk.CTkLabel(parent, text=text, **default_kwargs)
        return label
        
    def create_form_field(
        self, 
        parent, 
        label_text: str, 
        field_type: str = "entry",
        variable: Optional[Union[tk.StringVar, tk.BooleanVar, tk.IntVar]] = None,
        options: Optional[list] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a labeled form field
        
        Args:
            parent: Parent widget
            label_text: Label text
            field_type: Field type (entry, dropdown, checkbox, etc.)
            variable: Variable to bind to the field
            options: Options for dropdown fields
            **kwargs: Additional arguments for the field widget
            
        Returns:
            Dictionary containing the frame, label, and field widgets
        """
        # Create container frame
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        
        # Create label
        label = ctk.CTkLabel(
            frame, 
            text=label_text,
            font=ctk.CTkFont(size=14),
            anchor="w"
        )
        label.pack(anchor="w", pady=(0, 5))
        
        # Create field based on type
        field = None
        
        if field_type == "entry":
            field = ctk.CTkEntry(frame, **kwargs)
            if variable:
                field.configure(textvariable=variable)
                
        elif field_type == "dropdown":
            field = ctk.CTkOptionMenu(
                frame, 
                values=options or [],
                **kwargs
            )
            if variable:
                field.configure(variable=variable)
                
        elif field_type == "checkbox":
            field = ctk.CTkCheckBox(
                frame,
                text="",
                **kwargs
            )
            if variable:
                field.configure(variable=variable)
                
        elif field_type == "text":
            field = ctk.CTkTextbox(frame, **kwargs)
            # Text widgets don't use variables directly
            
        else:
            # Default to entry
            field = ctk.CTkEntry(frame, **kwargs)
            if variable:
                field.configure(textvariable=variable)
        
        # Pack the field
        field.pack(fill="x", expand=True)
        
        # Return all widgets
        return {
            "frame": frame,
            "label": label,
            "field": field
        }