"""
Utility functions for image processing
"""
import os
import cv2
import numpy as np
from PIL import Image


def resize_image(image, width=None, height=None):
    """
    Resize an image while maintaining aspect ratio
    
    Args:
        image (numpy.ndarray): Image to resize
        width (int, optional): Target width
        height (int, optional): Target height
        
    Returns:
        numpy.ndarray: Resized image
    """
    if width is None and height is None:
        return image
        
    h, w = image.shape[:2]
    
    if width is None:
        aspect = height / float(h)
        dim = (int(w * aspect), height)
    elif height is None:
        aspect = width / float(w)
        dim = (width, int(h * aspect))
    else:
        dim = (width, height)
        
    resized = cv2.resize(image, dim, interpolation=cv2.INTER_AREA)
    return resized


def convert_to_grayscale(image):
    """
    Convert an image to grayscale
    
    Args:
        image (numpy.ndarray): Image to convert
        
    Returns:
        numpy.ndarray: Grayscale image
    """
    if len(image.shape) == 2:
        return image
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def equalize_histogram(image):
    """
    Equalize the histogram of an image
    
    Args:
        image (numpy.ndarray): Image to equalize
        
    Returns:
        numpy.ndarray: Equalized image
    """
    gray = convert_to_grayscale(image)
    return cv2.equalizeHist(gray)


def save_image(image, path, filename):
    """
    Save an image to disk
    
    Args:
        image (numpy.ndarray): Image to save
        path (str): Directory to save the image
        filename (str): Filename for the image
        
    Returns:
        str: Path to the saved image
    """
    os.makedirs(path, exist_ok=True)
    file_path = os.path.join(path, filename)
    cv2.imwrite(file_path, image)
    return file_path


def load_image(path, grayscale=False):
    """
    Load an image from disk
    
    Args:
        path (str): Path to the image
        grayscale (bool): Whether to load the image in grayscale
        
    Returns:
        numpy.ndarray: Loaded image
    """
    if grayscale:
        return cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    return cv2.imread(path)


def draw_rectangle(image, rect, color=(0, 255, 0), thickness=2):
    """
    Draw a rectangle on an image
    
    Args:
        image (numpy.ndarray): Image to draw on
        rect (tuple): Rectangle coordinates (x, y, w, h)
        color (tuple): RGB color tuple
        thickness (int): Line thickness
        
    Returns:
        numpy.ndarray: Image with rectangle
    """
    x, y, w, h = rect
    return cv2.rectangle(image.copy(), (x, y), (x + w, y + h), color, thickness)


def validate_image(image_path):
    """
    Validate if an image file is valid and can be processed
    
    Args:
        image_path (str): Path to the image file
        
    Returns:
        bool: True if the image is valid, False otherwise
    """
    if not os.path.exists(image_path):
        return False
        
    try:
        img = Image.open(image_path)
        img.verify()  # Verify that it is a valid image
        
        # Check if OpenCV can read it too
        cv_img = cv2.imread(image_path)
        if cv_img is None or cv_img.size == 0:
            return False
            
        return True
    except Exception:
        return False


def optimize_image(image_path, quality=85, max_size=(800, 800)):
    """
    Optimize an image by reducing quality and/or resizing
    
    Args:
        image_path (str): Path to the image file
        quality (int): JPEG quality (0-100)
        max_size (tuple): Maximum width and height
        
    Returns:
        str: Path to the optimized image, same as input if optimization failed
    """
    try:
        img = Image.open(image_path)
        
        # Resize if needed
        if img.width > max_size[0] or img.height > max_size[1]:
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Save with optimization
        img.save(image_path, optimize=True, quality=quality)
        
        return image_path
    except Exception as e:
        print(f"Error optimizing image: {e}")
        return image_path