"""
Utility script to create a simple screenshot for documentation
"""
import os
from PIL import Image, ImageDraw, ImageFont

def create_simple_screenshot(output_path="docs/img/screenshot.png"):
    """
    Create a simple screenshot of the application for documentation
    
    Args:
        output_path (str): Path to save the screenshot
    """
    print(f"Creating simple screenshot at {output_path}...")
    
    # Create a blank image
    img_width, img_height = 1280, 720
    background_color = (240, 240, 240)  # Light gray
    
    img = Image.new('RGB', (img_width, img_height), background_color)
    draw = ImageDraw.Draw(img)
    
    # Try to use a nice font, fallback to default if not available
    try:
        title_font = ImageFont.truetype("arial.ttf", 36)
        heading_font = ImageFont.truetype("arial.ttf", 24)
        regular_font = ImageFont.truetype("arial.ttf", 18)
        small_font = ImageFont.truetype("arial.ttf", 14)
    except IOError:
        # Use default font if custom font fails
        title_font = ImageFont.load_default()
        heading_font = ImageFont.load_default()
        regular_font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    
    # Add title
    title = "Face Recognition Attendance System"
    title_width = draw.textlength(title, font=title_font)
    draw.text(((img_width - title_width) // 2, 30), title, fill=(50, 50, 50), font=title_font)
    
    # Create video frame area (left side)
    video_width, video_height = 640, 480
    video_x, video_y = 50, 100
    
    # Draw video frame border
    draw.rectangle([video_x, video_y, video_x + video_width, video_y + video_height], 
                 outline=(0, 0, 0), width=2, fill=(30, 30, 30))
    
    # Simulate face detection
    face_x, face_y = video_x + 250, video_y + 150
    face_width, face_height = 140, 180
    
    # Draw a face detection box
    draw.rectangle([face_x, face_y, face_x + face_width, face_y + face_height], 
                 outline=(0, 255, 0), width=3)
    
    # Add name under the face detection box
    name_text = "John Doe (ID: 12345)"
    name_width = draw.textlength(name_text, font=regular_font)
    draw.text((face_x + (face_width - name_width) // 2, face_y + face_height + 10), 
             name_text, fill=(0, 200, 0), font=regular_font)
    
    # Add counter on the video feed
    counter_text = "Attendance Count: 1"
    draw.text((video_x + 20, video_y + 20), counter_text, fill=(255, 50, 50), font=regular_font)
    
    # Add subject on the video feed
    subject_text = "Subject: Computer Science"
    draw.text((video_x + 20, video_y + 50), subject_text, fill=(255, 50, 50), font=regular_font)
    
    # Draw control buttons below video
    button_y = video_y + video_height + 50
    button_width, button_height = 180, 60
    
    # Take Images button
    take_x = video_x
    draw.rectangle([take_x, button_y, take_x + button_width, button_y + button_height], 
                 fill=(76, 175, 80), outline=(0, 0, 0), width=1)
    button_text = "Take Images"
    text_width = draw.textlength(button_text, font=heading_font)
    draw.text((take_x + (button_width - text_width) // 2, button_y + 15), 
             button_text, fill=(255, 255, 255), font=heading_font)
    
    # Train Images button
    train_x = take_x + button_width + 20
    draw.rectangle([train_x, button_y, train_x + button_width, button_y + button_height], 
                 fill=(33, 150, 243), outline=(0, 0, 0), width=1)
    button_text = "Train Images"
    text_width = draw.textlength(button_text, font=heading_font)
    draw.text((train_x + (button_width - text_width) // 2, button_y + 15), 
             button_text, fill=(255, 255, 255), font=heading_font)
    
    # Track Images button
    track_x = train_x + button_width + 20
    draw.rectangle([track_x, button_y, track_x + button_width, button_y + button_height], 
                 fill=(255, 152, 0), outline=(0, 0, 0), width=1)
    button_text = "Track Images"
    text_width = draw.textlength(button_text, font=heading_font)
    draw.text((track_x + (button_width - text_width) // 2, button_y + 15), 
             button_text, fill=(255, 255, 255), font=heading_font)
    
    # Right side for student registration
    right_x = video_x + video_width + 50
    right_width = img_width - right_x - 50
    
    # Student Registration section
    reg_y = video_y
    reg_height = 150
    draw.rectangle([right_x, reg_y, right_x + right_width, reg_y + reg_height], 
                 fill=(245, 245, 245), outline=(200, 200, 200), width=1)
    
    # Registration header
    header_text = "Student Registration"
    draw.text((right_x + 15, reg_y + 15), header_text, fill=(100, 100, 100), font=heading_font)
    
    # Registration fields
    field_x = right_x + 20
    field_y = reg_y + 60
    
    # ID Field
    draw.text((field_x, field_y), "Enrollment ID:", fill=(100, 100, 100), font=regular_font)
    draw.rectangle([field_x + 150, field_y, field_x + 300, field_y + 30], 
                 fill=(255, 255, 255), outline=(200, 200, 200), width=1)
    draw.text((field_x + 160, field_y + 5), "12345", fill=(0, 0, 0), font=regular_font)
    
    # Name Field
    draw.text((field_x, field_y + 40), "Student Name:", fill=(100, 100, 100), font=regular_font)
    draw.rectangle([field_x + 150, field_y + 40, field_x + 300, field_y + 70], 
                 fill=(255, 255, 255), outline=(200, 200, 200), width=1)
    draw.text((field_x + 160, field_y + 45), "John Doe", fill=(0, 0, 0), font=regular_font)
    
    # Attendance section
    att_y = reg_y + reg_height + 30
    att_height = 250
    draw.rectangle([right_x, att_y, right_x + right_width, att_y + att_height], 
                 fill=(245, 245, 245), outline=(200, 200, 200), width=1)
    
    # Attendance header
    header_text = "Attendance"
    draw.text((right_x + 15, att_y + 15), header_text, fill=(100, 100, 100), font=heading_font)
    
    # Subject field
    field_y = att_y + 60
    draw.text((field_x, field_y), "Subject:", fill=(100, 100, 100), font=regular_font)
    draw.rectangle([field_x + 150, field_y, field_x + 300, field_y + 30], 
                 fill=(255, 255, 255), outline=(200, 200, 200), width=1)
    draw.text((field_x + 160, field_y + 5), "Computer Science", fill=(0, 0, 0), font=regular_font)
    
    # Quick subject buttons
    sub_y = field_y + 40
    sub_width = 75
    sub_height = 30
    
    subjects = ["Python", "Java", "Web Dev", "Data Sci"]
    for i, subject in enumerate(subjects):
        sub_x = field_x + (sub_width + 5) * i
        draw.rectangle([sub_x, sub_y, sub_x + sub_width, sub_y + sub_height], 
                     fill=(103, 58, 183), outline=(0, 0, 0), width=1)
        text_width = draw.textlength(subject, font=small_font)
        draw.text((sub_x + (sub_width - text_width) // 2, sub_y + 5), 
                 subject, fill=(255, 255, 255), font=small_font)
    
    # Mark Attendance button
    mark_y = sub_y + 50
    draw.rectangle([field_x, mark_y, field_x + 200, mark_y + 50], 
                 fill=(103, 58, 183), outline=(0, 0, 0), width=1)
    button_text = "Mark Attendance"
    text_width = draw.textlength(button_text, font=regular_font)
    draw.text((field_x + (200 - text_width) // 2, mark_y + 12), 
             button_text, fill=(255, 255, 255), font=regular_font)
    
    # View Attendance button
    view_y = mark_y + 60
    draw.rectangle([field_x, view_y, field_x + 200, view_y + 50], 
                 fill=(0, 150, 136), outline=(0, 0, 0), width=1)
    button_text = "View Attendance"
    text_width = draw.textlength(button_text, font=regular_font)
    draw.text((field_x + (200 - text_width) // 2, view_y + 12), 
             button_text, fill=(255, 255, 255), font=regular_font)
    
    # Status bar at the bottom
    status_height = 30
    status_y = img_height - status_height
    draw.rectangle([0, status_y, img_width, img_height], fill=(240, 240, 240), outline=(200, 200, 200), width=1)
    status_text = "Status: Ready"
    draw.text((20, status_y + 5), status_text, fill=(100, 100, 100), font=regular_font)
    
    # Camera status on right side of status bar
    camera_text = "Camera: Active"
    text_width = draw.textlength(camera_text, font=regular_font)
    draw.text((img_width - text_width - 20, status_y + 5), camera_text, fill=(0, 128, 0), font=regular_font)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Save the image
    img.save(output_path)
    print(f"Screenshot saved to {output_path}")
    return output_path

if __name__ == "__main__":
    create_simple_screenshot() 