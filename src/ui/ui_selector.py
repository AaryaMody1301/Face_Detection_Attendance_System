"""
UI Selector for Face Detection Attendance System

Provides a clean interface to select between the modern and classic UI versions.
"""
import tkinter as tk
import logging
import os
import json
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

class UISelectorDialog:
    """Dialog to select between modern and classic UI"""
    
    def __init__(self, parent=None):
        """
        Initialize the UI selector dialog
        
        Args:
            parent: Parent window (optional)
        """
        # Load current preference
        self.config_file = os.path.join("config", "config.json")
        self.current_preference = self.get_current_preference()
        
        # Create a new Toplevel window if parent is provided, otherwise create a new Tk root
        if parent:
            self.root = tk.Toplevel(parent)
            self.is_toplevel = True
        else:
            self.root = tk.Tk()
            self.is_toplevel = False
            
        # Configure the window
        self.root.title("Select User Interface")
        self.root.geometry("400x300")
        self.root.resizable(False, False)
        
        # Center the window
        self.center_window()
        
        # Result variable
        self.result = None
        
        # Create the UI
        self.create_ui()
        
        # Make dialog modal if it's a toplevel window
        if self.is_toplevel:
            self.root.transient(parent)
            self.root.grab_set()
            
    def center_window(self):
        """Center the window on the screen"""
        self.root.update_idletasks()
        
        # Get window dimensions
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        
        # Calculate position
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        
        # Set position
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        
    def get_current_preference(self):
        """Get the current UI preference from config"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    return config.get("ui", {}).get("type", "modern")
            return "modern"  # Default to modern UI
        except Exception as e:
            logger.error(f"Error reading config: {e}")
            return "modern"
            
    def save_preference(self, ui_type):
        """Save UI preference to config"""
        try:
            # Create config directory if it doesn't exist
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            # Load existing config or create new one
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
            else:
                config = {}
                
            # Ensure ui section exists
            if "ui" not in config:
                config["ui"] = {}
                
            # Set UI type
            config["ui"]["type"] = ui_type
            
            # Save config
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=4)
                
            logger.info(f"Saved UI preference: {ui_type}")
            return True
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            return False
            
    def create_ui(self):
        """Create the UI elements"""
        # Main frame
        main_frame = tk.Frame(self.root, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = tk.Label(
            main_frame, 
            text="Face Detection Attendance System",
            font=("Arial", 16, "bold"),
            pady=10
        )
        title_label.pack(fill=tk.X)
        
        # Subtitle
        subtitle_label = tk.Label(
            main_frame,
            text="Select User Interface",
            font=("Arial", 12),
            pady=5
        )
        subtitle_label.pack(fill=tk.X)
        
        # Modern UI option
        self.modern_var = tk.BooleanVar(value=(self.current_preference == "modern"))
        
        modern_frame = tk.Frame(main_frame, pady=10)
        modern_frame.pack(fill=tk.X)
        
        modern_radio = tk.Radiobutton(
            modern_frame,
            text="Modern UI",
            variable=self.modern_var,
            value=True,
            font=("Arial", 11),
            command=lambda: self.on_selection_change("modern")
        )
        modern_radio.pack(side=tk.LEFT)
        
        modern_desc = tk.Label(
            modern_frame,
            text="Sleek tabbed interface with customizable themes",
            font=("Arial", 10),
            fg="gray50"
        )
        modern_desc.pack(side=tk.LEFT, padx=10)
        
        # Classic UI option
        classic_frame = tk.Frame(main_frame, pady=10)
        classic_frame.pack(fill=tk.X)
        
        classic_radio = tk.Radiobutton(
            classic_frame,
            text="Classic UI",
            variable=self.modern_var,
            value=False,
            font=("Arial", 11),
            command=lambda: self.on_selection_change("classic")
        )
        classic_radio.pack(side=tk.LEFT)
        
        classic_desc = tk.Label(
            classic_frame,
            text="Traditional interface with simple layout",
            font=("Arial", 10),
            fg="gray50"
        )
        classic_desc.pack(side=tk.LEFT, padx=10)
        
        # Remember choice checkbox
        self.remember_var = tk.BooleanVar(value=True)
        remember_cb = tk.Checkbutton(
            main_frame,
            text="Remember my choice",
            variable=self.remember_var,
            font=("Arial", 10)
        )
        remember_cb.pack(pady=10, anchor=tk.W)
        
        # Buttons frame
        buttons_frame = tk.Frame(main_frame, pady=10)
        buttons_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        # Start button
        start_button = tk.Button(
            buttons_frame,
            text="Start",
            command=self.on_start,
            padx=20,
            pady=5
        )
        start_button.pack(side=tk.RIGHT)
        
        # Cancel button (only if this is a toplevel window)
        if self.is_toplevel:
            cancel_button = tk.Button(
                buttons_frame,
                text="Cancel",
                command=self.on_cancel,
                padx=20,
                pady=5
            )
            cancel_button.pack(side=tk.RIGHT, padx=10)
            
    def on_selection_change(self, selection):
        """Handle selection change"""
        self.current_preference = selection
        
    def on_start(self):
        """Handle start button click"""
        # Determine selected UI
        selected_ui = "modern" if self.modern_var.get() else "classic"
        
        # Save preference if requested
        if self.remember_var.get():
            self.save_preference(selected_ui)
            
        # Set result
        self.result = selected_ui
        
        # Close dialog
        self.root.destroy()
        
    def on_cancel(self):
        """Handle cancel button click"""
        # Set result to None (use default)
        self.result = None
        
        # Close dialog
        self.root.destroy()
        
    def show(self):
        """
        Show the dialog and wait for user input
        
        Returns:
            str: Selected UI type ("modern" or "classic") or None if cancelled
        """
        # Run the dialog
        if self.is_toplevel:
            self.root.wait_window()
        else:
            self.root.mainloop()
            
        return self.result
        
def select_ui(parent=None, force_selection=False):
    """
    Show the UI selector dialog
    
    Args:
        parent: Parent window (optional)
        force_selection (bool): If True, always show the dialog even if there's a preference
        
    Returns:
        str: Selected UI type ("modern" or "classic")
    """
    # Check for existing preference if not forcing selection
    if not force_selection:
        config_file = os.path.join("config", "config.json")
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    ui_type = config.get("ui", {}).get("type")
                    if ui_type in ("modern", "classic"):
                        return ui_type
        except Exception:
            pass
            
    # Show dialog
    dialog = UISelectorDialog(parent)
    selected_ui = dialog.show()
    
    # Return selected UI or default to modern
    return selected_ui if selected_ui else "modern"
    
if __name__ == "__main__":
    # Test the UI selector
    selection = select_ui(force_selection=True)
    print(f"Selected UI: {selection}")