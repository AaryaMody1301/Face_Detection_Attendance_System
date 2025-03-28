# Placeholder image for logo
from PIL import Image, ImageDraw

# Create a blank image with white background
logo_image = Image.new('RGB', (100, 100), 'white')

# Draw a simple logo (e.g., a circle)
draw = ImageDraw.Draw(logo_image)
draw.ellipse((25, 25, 75, 75), fill='blue', outline='black')

# Save the image
logo_image.save('e:\Projects\Face_Detection_Attendance_System\Face_Detection_Attendance_System\src\ui\assets\logo.png')

# Placeholder image for login illustration
login_illustration = Image.new('RGB', (350, 350), 'white')

# Draw a simple illustration (e.g., a rectangle)
draw = ImageDraw.Draw(login_illustration)
draw.rectangle((50, 50, 300, 300), fill='green', outline='black')

# Save the image
login_illustration.save('e:\Projects\Face_Detection_Attendance_System\Face_Detection_Attendance_System\src\ui\assets\login_illustration.png')