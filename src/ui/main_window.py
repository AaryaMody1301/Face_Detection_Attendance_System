import os
import sys
import logging
import traceback
import tkinter as tk
from PIL import Image, ImageDraw, ImageTk
import customtkinter as ctk

# Configure logger
logger = logging.getLogger(__name__)

# Set application theme
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class MainWindow(ctk.CTk):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        
        # Configure the main window
        self.title("Face Recognition Attendance System")
        self.geometry("1200x800")
        self.minsize(900, 600)
        
        # Initialize icon manager
        self.icons = IconManager()
        
        # Set appearance mode based on system settings
        self._set_appearance_mode()
        
        # Initialize the UI
        self._create_ui()
        
        # Set up initial view
        self._show_dashboard()
        
        # Configure event bindings
        self._setup_event_bindings()
        
        # Log application startup
        logger.info("Application started")

class IconManager:
    """Manages icon loading and caching for the application"""
    
    def __init__(self):
        self.icon_cache = {}
        self.icon_paths = {
            # Navigation icons
            "dashboard": self._create_icon_path("dashboard.png"),
            "attendance": self._create_icon_path("attendance.png"),
            "students": self._create_icon_path("students.png"),
            "reports": self._create_icon_path("reports.png"),
            "settings": self._create_icon_path("settings.png"),
            
            # Action icons
            "capture": self._create_icon_path("capture.png"),
            "save": self._create_icon_path("save.png"),
            "add": self._create_icon_path("add.png"),
            "delete": self._create_icon_path("delete.png"),
            "edit": self._create_icon_path("edit.png"),
            "search": self._create_icon_path("search.png"),
            "refresh": self._create_icon_path("refresh.png"),
            
            # UI icons
            "dark_mode": self._create_icon_path("dark_mode.png"),
            "light_mode": self._create_icon_path("light_mode.png"),
            "menu": self._create_icon_path("menu.png"),
            "close": self._create_icon_path("close.png"),
            "back": self._create_icon_path("back.png"),
        }
        
        # Create default icons for missing ones
        self._create_default_icons()
        
    def _create_icon_path(self, filename):
        """Create the full path to an icon file"""
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "icons", filename)
        
    def _create_default_icons(self):
        """Create default icons for any missing icon files"""
        # Ensure the icons directory exists
        icons_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "icons")
        os.makedirs(icons_dir, exist_ok=True)
        
        # Generate default icons for any that don't exist
        for name, path in self.icon_paths.items():
            if not os.path.exists(path):
                self._generate_default_icon(path, name)
                
    def _generate_default_icon(self, path, name):
        """Generate a default icon if the real icon is missing"""
        try:
            # Create a blank 64x64 image
            img = Image.new('RGBA', (64, 64), color=(240, 240, 240, 0))
            draw = ImageDraw.Draw(img)
            
            # Draw a simple shape based on the icon name
            if "dashboard" in name:
                self._draw_shape(draw, "rectangle")
            elif "attendance" in name:
                self._draw_shape(draw, "checkmark")
            elif "students" in name:
                self._draw_shape(draw, "people")
            elif "dark_mode" in name or "light_mode" in name:
                self._draw_shape(draw, "circle")
            else:
                # Default generic icon
                self._draw_shape(draw, "default")
                
            # Add text label
            draw.text((32, 50), name[:8], fill=(100, 100, 100, 200), anchor="ms")
            
            # Save the icon
            img.save(path)
            logger.info(f"Generated default icon for {name}")
            
        except Exception as e:
            logger.error(f"Error generating default icon for {name}: {e}")
            
    def _draw_shape(self, draw, shape_type):
        """Draw different shapes for different icon types"""
        if shape_type == "rectangle":
            draw.rectangle((16, 16, 48, 48), outline=(100, 100, 100, 200), width=2)
        elif shape_type == "circle":
            draw.ellipse((16, 16, 48, 48), outline=(100, 100, 100, 200), width=2)
        elif shape_type == "checkmark":
            draw.line((16, 32, 28, 44, 48, 20), fill=(100, 100, 100, 200), width=2)
        elif shape_type == "people":
            # Draw a simple person icon
            draw.ellipse((24, 16, 40, 32), outline=(100, 100, 100, 200), width=2)  # Head
            draw.line((32, 32, 32, 44), fill=(100, 100, 100, 200), width=2)  # Body
            draw.line((32, 38, 24, 46), fill=(100, 100, 100, 200), width=2)  # Left arm
            draw.line((32, 38, 40, 46), fill=(100, 100, 100, 200), width=2)  # Right arm
        else:
            # Default icon (just a dot)
            draw.ellipse((28, 28, 36, 36), fill=(100, 100, 100, 200))
            
    def get_icon(self, name, size=(24, 24)):
        """Get an icon by name with caching and resizing"""
        # Generate cache key
        cache_key = f"{name}_{size[0]}x{size[1]}"
        
        # Check if icon is already cached
        if cache_key in self.icon_cache:
            return self.icon_cache[cache_key]
            
        # If not in cache, load and resize
        try:
            if name in self.icon_paths:
                path = self.icon_paths[name]
                
                # Check if file exists
                if not os.path.exists(path):
                    logger.warning(f"Icon not found: {name}")
                    # Generate a default icon
                    self._generate_default_icon(path, name)
                
                # Load and resize image
                img = Image.open(path)
                img = img.resize(size, Image.Resampling.LANCZOS)
                
                # Convert to CTkImage
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=size)
                
                # Cache the image
                self.icon_cache[cache_key] = ctk_img
                
                return ctk_img
            else:
                logger.warning(f"Icon not defined in paths: {name}")
                return None
                
        except Exception as e:
            logger.error(f"Error loading icon {name}: {e}")
            return None 