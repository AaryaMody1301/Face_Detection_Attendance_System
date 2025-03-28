"""
Script to generate a simple app icon for the Face Detection Attendance System
"""
import os
from PIL import Image, ImageDraw, ImageFont

def create_simple_icon():
    """Create a simple app icon using PIL"""
    # Define paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    icons_dir = os.path.join(base_dir, "assets", "icons")
    ui_assets_dir = os.path.join(base_dir, "src", "ui", "assets")
    
    # Create directories if they don't exist
    os.makedirs(icons_dir, exist_ok=True)
    os.makedirs(ui_assets_dir, exist_ok=True)
    
    # Create a blank image with transparent background
    icon_size = 128
    icon = Image.new('RGBA', (icon_size, icon_size), (0, 0, 0, 0))
    
    # Create a drawing context
    draw = ImageDraw.Draw(icon)
    
    # Draw a blue rounded rectangle as background
    draw.rounded_rectangle(
        [(10, 10), (icon_size-10, icon_size-10)],
        fill=(0, 120, 212, 255),
        radius=20
    )
    
    # Draw a simple face outline in white
    center_x, center_y = icon_size // 2, icon_size // 2
    face_size = icon_size // 2
    
    # Face circle
    draw.ellipse(
        [(center_x - face_size//2, center_y - face_size//2),
         (center_x + face_size//2, center_y + face_size//2)],
        outline=(255, 255, 255, 255),
        width=3
    )
    
    # Eyes
    eye_size = face_size // 6
    eye_y = center_y - face_size//6
    
    # Left eye
    left_eye_x = center_x - face_size//4
    draw.ellipse(
        [(left_eye_x - eye_size//2, eye_y - eye_size//2),
         (left_eye_x + eye_size//2, eye_y + eye_size//2)],
        fill=(255, 255, 255, 255)
    )
    
    # Right eye
    right_eye_x = center_x + face_size//4
    draw.ellipse(
        [(right_eye_x - eye_size//2, eye_y - eye_size//2),
         (right_eye_x + eye_size//2, eye_y + eye_size//2)],
        fill=(255, 255, 255, 255)
    )
    
    # Smile
    draw.arc(
        [(center_x - face_size//3, center_y - face_size//8),
         (center_x + face_size//3, center_y + face_size//2)],
        start=0,
        end=180,
        fill=(255, 255, 255, 255),
        width=3
    )
    
    # Save the icon
    icon_path = os.path.join(icons_dir, 'app_icon.png')
    icon.save(icon_path)
    print(f"App icon created at: {icon_path}")
    
    # Create a login illustration (simplified version of the icon)
    login_image = Image.new('RGB', (512, 512), (240, 240, 240))
    draw = ImageDraw.Draw(login_image)
    
    # Background
    draw.rectangle([(0, 0), (512, 512)], fill=(240, 240, 240))
    
    # Draw a larger face with attendance elements
    draw.ellipse([(128, 96), (384, 352)], outline=(0, 120, 212), width=6)
    
    # Eyes
    draw.ellipse([(192, 176), (224, 208)], fill=(0, 120, 212))
    draw.ellipse([(288, 176), (320, 208)], fill=(0, 120, 212))
    
    # Smile
    draw.arc([(192, 192), (320, 280)], start=0, end=180, fill=(0, 120, 212), width=6)
    
    # Attendance text
    try:
        # Try to use a font if available
        font = ImageFont.truetype("arial.ttf", 40)
    except:
        # Fall back to default font
        font = ImageFont.load_default()
    
    draw.text((140, 380), "Attendance System", fill=(0, 120, 212), font=font)
    draw.text((180, 430), "Face Detection", fill=(0, 120, 212), font=font)
    
    # Save the login illustration
    login_path = os.path.join(ui_assets_dir, 'login_illustration.png')
    login_image.save(login_path)
    print(f"Login illustration created at: {login_path}")

if __name__ == "__main__":
    create_simple_icon()
    print("Assets created successfully!")
