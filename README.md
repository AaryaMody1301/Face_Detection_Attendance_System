# Face Detection Attendance System

A facial recognition-based attendance management system built with Python, OpenCV, and customtkinter.

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![OpenCV](https://img.shields.io/badge/OpenCV-4.x-red)

## Features

- **Facial Recognition Attendance**: Automatically mark attendance using face detection and recognition
- **Student Registration**: Register new students with their facial data
- **Attendance Management**: View, filter, and export attendance records
- **Modern UI**: Clean, intuitive user interface with both light and dark mode support
- **Analytics Dashboard**: Visualize attendance statistics and patterns
- **Multi-platform**: Works on Windows, macOS, and Linux

## Screenshots

<p align="center">
  <img src="assets/screenshots/dashboard.png" alt="Dashboard" width="45%">
  <img src="assets/screenshots/attendance.png" alt="Attendance Module" width="45%">
</p>

## Installation

### Prerequisites

- Python 3.8 or higher
- Webcam (built-in or external)
- The following Python packages (installed automatically via requirements.txt):
  - opencv-contrib-python (not regular opencv-python)
  - customtkinter
  - Pillow (PIL Fork)
  - NumPy
  - Pandas
  - face-recognition
  - dlib

### Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/face-detection-attendance-system.git
   cd face-detection-attendance-system
   ```

2. Create a virtual environment (optional but recommended):
   ```bash
   # On Windows
   python -m venv venv
   venv\Scripts\activate
   
   # On macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the application:
   ```bash
   # On Windows
   python main.py
   
   # On macOS/Linux
   python3 main.py
   ```

## GitHub Setup

To setup this project on your own GitHub repository:

1. Create a new repository on GitHub without initializing with README, license, or gitignore files

2. Initialize git in your local project folder (if not already done):
   ```bash
   git init
   ```

3. Add all files to git:
   ```bash
   git add .
   ```

4. Commit the files:
   ```bash
   git commit -m "Initial commit"
   ```

5. Add your GitHub repository as a remote:
   ```bash
   git remote add origin https://github.com/yourusername/your-repo-name.git
   ```

6. Push to GitHub:
   ```bash
   git push -u origin main
   ```

## Usage

### Dashboard

The dashboard provides an overview of attendance statistics and quick access to main functions.

### Student Registration

1. Navigate to the Students tab
2. Click "Add New Student"
3. Enter student details (ID and Name)
4. Capture facial images using the webcam
5. Save the student record

### Mark Attendance

1. Navigate to the Attendance tab
2. Select the relevant subject/class
3. Start the camera
4. The system will automatically detect and mark attendance for recognized students
5. Manual attendance can also be recorded if needed

### Reports

1. Navigate to the Reports tab
2. Filter by date, subject, or student
3. View attendance records in the table
4. Export data to CSV for further analysis

## Structure

```
face-detection-attendance-system/
├── src/
│   ├── face_recognition/  # Face detection and recognition modules
│   ├── ui/                # User interface components
│   ├── resources/         # Application resources
│   │   ├── icons/         # UI icons
│   │   └── haarcascades/  # OpenCV cascade files
│   ├── utils/             # Utility functions
│   └── main.py            # Application entry point
├── Data/                  # Data storage
├── Attendance/            # Attendance records
├── TrainingImage/         # Student facial images
├── TrainingImageLabel/    # Face recognition models
├── StudentDetails/        # Student information
├── requirements.txt       # Python dependencies
├── LICENSE                # MIT License
└── README.md              # Project documentation
```

## Troubleshooting

- **Camera not working**: Ensure your webcam is properly connected and not being used by another application
- **Face not detected**: Adjust lighting conditions and ensure the face is clearly visible
- **Recognition issues**: Try re-registering the student with more varied facial images
- **OpenCV errors**: Make sure you've installed `opencv-contrib-python` (not regular `opencv-python`)
- **Missing face module**: If you get `module 'cv2' has no attribute 'face'` error, uninstall `opencv-python` and install `opencv-contrib-python`

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgements

- [OpenCV](https://opencv.org/) for computer vision capabilities
- [face_recognition](https://github.com/ageitgey/face_recognition) for facial recognition
- [customtkinter](https://github.com/TomSchimansky/CustomTkinter) for modern UI components
