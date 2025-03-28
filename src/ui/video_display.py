"""
Custom video display widget for reliable image handling in Tkinter
"""
import tkinter as tk
from PIL import Image, ImageTk
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VideoDisplayWidget(tk.Frame):
    """
    A specialized widget for displaying video frames in Tkinter
    that avoids the common image reference issues.
    """
    
    def __init__(self, master, width=640, height=480, bg="black"):
        """
        Initialize the video display widget
        
        Args:
            master: Parent widget
            width: Initial width
            height: Initial height
            bg: Background color
        """
        super().__init__(master)
        
        # Configure frame
        self.configure(bg=bg, highlightthickness=0)
        
        # Initialize attributes
        self.width = width
        self.height = height
        self.current_image = None
        self._image_refs = []  # Keep strong references to all images
        
        # Create canvas for displaying images
        self.canvas = tk.Canvas(
            self,
            width=width,
            height=height,
            bg=bg,
            highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True)
        
        # Image ID for canvas
        self.image_id = None
        
        # Display placeholder text
        self.text_id = self.canvas.create_text(
            width // 2, height // 2,
            text="Camera feed will appear here",
            fill="white",
            font=("Arial", 14)
        )
        
    def display_image(self, pil_image):
        """
        Display a PIL image on the canvas
        
        Args:
            pil_image: PIL Image object to display
        """
        if pil_image is None:
            return
            
        try:
            # Get current widget dimensions
            w = self.canvas.winfo_width() or self.width
            h = self.canvas.winfo_height() or self.height
            
            # Ensure dimensions are reasonable
            if w < 10:
                w = self.width
            if h < 10:
                h = self.height
            
            # Resize image to fit canvas (maintaining aspect ratio)
            img_w, img_h = pil_image.size
            scale = min(w / img_w, h / img_h)
            new_w = int(img_w * scale)
            new_h = int(img_h * scale)
            
            # Only resize if needed
            if new_w != img_w or new_h != img_h:
                pil_image = pil_image.resize((new_w, new_h), Image.LANCZOS)
            
            # Convert to Tkinter PhotoImage
            tk_image = ImageTk.PhotoImage(pil_image)
            
            # Add to our reference list and limit the size to prevent memory leaks
            self._image_refs.append(tk_image)
            if len(self._image_refs) > 5:  # Keep last 5 images
                self._image_refs.pop(0)
                
            # Store current image
            self.current_image = tk_image
            
            # Remove placeholder text if it exists
            if self.text_id:
                self.canvas.delete(self.text_id)
                self.text_id = None
            
            # If there's already an image on the canvas, delete it
            if self.image_id:
                self.canvas.delete(self.image_id)
            
            # Calculate position to center the image
            x = w // 2
            y = h // 2
            
            # Create new image on canvas (centered)
            self.image_id = self.canvas.create_image(
                x, y, 
                image=tk_image, 
                anchor="center"
            )
            
        except Exception as e:
            # Just log it, don't raise - this is a UI component
            logger.debug(f"Error displaying image: {e}")
    
    def clear(self):
        """Clear the displayed image"""
        if self.image_id:
            self.canvas.delete(self.image_id)
            self.image_id = None
        
        # Clear image references
        self.current_image = None
        self._image_refs.clear()
        
        # Add placeholder text back
        if not self.text_id:
            self.text_id = self.canvas.create_text(
                self.width // 2, self.height // 2,
                text="Camera feed will appear here",
                fill="white",
                font=("Arial", 14)
            )
        
    def resize(self, width, height):
        """Resize the canvas"""
        self.width = width
        self.height = height
        self.canvas.config(width=width, height=height)
        
    def configure(self, *args, **kwargs):
        """Override configure to handle image setting for compatibility"""
        # Special handling for image attribute
        if 'image' in kwargs:
            image = kwargs.pop('image')
            if image:
                # Convert to PIL if it's already a PhotoImage
                if isinstance(image, ImageTk.PhotoImage):
                    self.current_image = image
                    self._image_refs.append(image)
                    if len(self._image_refs) > 5:
                        self._image_refs.pop(0)
            else:
                self.clear()
                
        # Pass remaining args to parent configure
        super().configure(*args, **kwargs)