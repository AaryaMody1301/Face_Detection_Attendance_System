"""
Script to generate icon files for the Face Detection Attendance System
"""
import os
from PIL import Image, ImageDraw, ImageFont

def create_directory(path):
    """Create directory if it doesn't exist"""
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"Created directory: {path}")

def create_icon(name, color, size=(64, 64)):
    """Create a simple icon with text"""
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw rounded rectangle background
    radius = 10
    draw.rounded_rectangle([2, 2, size[0]-2, size[1]-2], radius, fill=color)
    
    # Add text (first letter of icon name)
    letter = name[0].upper()
    
    # Try to use a specific font, fall back to default
    try:
        font = ImageFont.truetype("arial.ttf", size[0]//3)
    except IOError:
        font = ImageFont.load_default()
    
    # Get text size to center it
    text_width, text_height = draw.textbbox((0, 0), letter, font=font)[2:4]
    position = ((size[0] - text_width) // 2, (size[1] - text_height) // 2)
    
    # Draw the letter in white
    draw.text(position, letter, fill="white", font=font)
    
    return img

def main():
    """Generate all needed icons"""
    # Ensure directories exist
    icon_dir = os.path.join("assets", "icons")
    create_directory(icon_dir)
    
    # Define icons to create with their colors
    icons = {
        "home": "#3498db",  # Blue
        "check": "#2ecc71",  # Green
        "analytics": "#9b59b6",  # Purple
        "user": "#e67e22",  # Orange
        "train": "#f1c40f",  # Yellow
        "settings": "#34495e",  # Dark blue
        "logout": "#e74c3c",  # Red
        "fullscreen": "#1abc9c",  # Teal
        "theme": "#8e44ad",  # Violet
    }
    
    # Create each icon
    for name, color in icons.items():
        img = create_icon(name, color)
        output_path = os.path.join(icon_dir, f"{name}.png")
        img.save(output_path)
        print(f"Created icon: {output_path}")
    
    # Create app icon (special case)
    app_icon = create_icon("app", "#3498db", size=(128, 128))
    app_icon_path = os.path.join(icon_dir, "app_icon.png")
    app_icon.save(app_icon_path)
    print(f"Created app icon: {app_icon_path}")
    
    print("All icons generated successfully!")

if __name__ == "__main__":
    main() 