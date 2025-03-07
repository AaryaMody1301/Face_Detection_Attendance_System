# Face Detection Attendance System

This project is a facial recognition-based attendance system developed as part of my B.Sc. thesis at Parul University. It automates attendance marking using computer vision techniques, achieving **95% accuracy** in facial recognition and a **40% reduction in processing time** for real-time performance. Built with Python, OpenCV, and SQLite, it highlights my expertise in machine learning, computer vision, and database management.

## Features
- **High Accuracy**: 95% face recognition accuracy with OpenCV and dlib.
- **Optimized Performance**: 40% faster processing for real-time applications.
- **Database Integration**: Stores attendance records in SQLite.
- **User-Friendly**: Simple process to add new faces and manage data.

## Technologies Used
- **Languages**: Python 3.x
- **Libraries**: OpenCV, dlib, NumPy
- **Database**: SQLite

## Installation
Follow these steps to set up the project locally:

1. **Clone the repository**:
   ```bash
   git clone https://github.com/AaryaMody1301/Face_Detection_Attendance_System.git
2. Navigate to the project directory:
   cd Face_Detection_Attendance_System
3. Ensure a webcam is connected for live detection.


**Usage**
Here’s how to use the system:

Add a new face:
1. Place the person’s image (e.g., john_doe.jpg) in the known_faces/ directory.
Run:
  python add_face.py --name "John Doe" --image "known_faces/john_doe.jpg"
2. Start the attendance system:
Run:
python main.py
The webcam will activate, detecting and recognizing faces in real time.
3. View attendance records:
Run:
python view_attendance.py
Alternatively, query attendance.db directly using SQLite tools.

**Project Structure**
Face_Detection_Attendance_System/
├── main.py               # Main script to run the attendance system
├── add_face.py           # Script to add new faces to the database
├── view_attendance.py    # Script to view attendance records
├── known_faces/          # Directory for images of known faces
├── data/                 # Directory for database files
│   └── attendance.db     # SQLite database for attendance records
├── requirements.txt      # List of dependencies
└── README.md             # Project documentation

Future Enhancements
Add a graphical user interface (GUI) for easier interaction.
Integrate cloud storage for data backup.
Support multi-face detection for group attendance.

### Notes
- **Setup**: Assumes you’ll include a `requirements.txt` with `opencv-python`, `dlib`, and `numpy`.
- **Customization**: Update file names or paths if your project structure differs.
- **Enhancements**: Add a screenshot or demo video for visual appeal (e.g., `![Demo](path/to/image.png)`).

This README provides a complete, professional overview of your project, making it easy to understand and use while highlighting your technical achievements. Upload it to your repository to enhance its appeal!
