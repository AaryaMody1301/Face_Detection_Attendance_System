# Face Detection Attendance System - Restructured Project

This document explains the restructured project organization for the Face Detection Attendance System which now uses a shared core module for both UI versions.

## Project Structure

The project has been restructured to use a unified core system that's shared between both Classic and Modern UIs:

```
Face_Detection_Attendance_System/
├── main.py                    # Main entry point
├── requirements.txt           # Project dependencies
├── run.bat                    # Run script for Windows
├── README.md                  # Project documentation
├── src/                       # Source code
│   ├── core/                  # Shared core functionality
│   │   ├── face_recognition/  # Face detection/recognition
│   │   │   ├── face_detector.py  # Unified face detector
│   │   │   └── ...
│   │   ├── database/         # Database handling
│   │   │   ├── db_handler.py # Unified database handler
│   │   │   └── ...
│   │   ├── utils/            # Shared utilities
│   │   │   ├── config_manager.py  # Configuration management
│   │   │   ├── video_processor.py # Video processing
│   │   │   └── ...
│   │   └── __init__.py
│   ├── ui/                    # User interface components
│   │   ├── modern_app.py      # Modern UI implementation
│   │   ├── app.py             # Classic UI implementation
│   │   ├── ui_selector.py     # UI selection dialog
│   │   └── ...
│   ├── models/                # Data models
│   └── utils/                 # Additional utilities
├── Data/                      # Database files
├── Attendance/                # Attendance records
├── TrainingImage/             # Training images
├── TrainingImageLabel/        # Face recognition models
└── ...
```

## Core Components

The restructured project now uses shared core components to reduce code duplication and ensure consistent functionality across both UI variants.

### Face Detection/Recognition

Both UIs now use the same face detection and recognition system:

```python
from src.core.face_recognition.face_detector import FaceDetector

# Initialize the detector
detector = FaceDetector(
    detection_method="auto",
    recognition_method="hybrid",
    scale_factor=0.5,
    confidence_threshold=0.6
)

# Use the detector
face_locations = detector.detect_faces(frame)
recognized_faces = detector.recognize_faces(frame)
```

### Database Handling

Both UIs now use the same database handler:

```python
from src.core.database.db_handler import DatabaseHandler

# Initialize the database handler
db = DatabaseHandler()

# Use the database handler
db.add_student("12345", "John Doe")
db.mark_attendance("12345", "John Doe", "Python")
```

### Configuration Management

The system now uses a unified configuration system:

```python
from src.core.utils.config_manager import ConfigManager

# Initialize the configuration manager
config = ConfigManager()

# Get configuration values
ui_type = config.get("ui.type", "modern")
confidence = config.get("face_detection.confidence_threshold", 0.6)

# Set configuration values
config.set("ui.theme", "dark")
```

### Video Processing

Video capture and processing is now handled by a shared component:

```python
from src.core.utils.video_processor import VideoProcessor

# Initialize the video processor
video_processor = VideoProcessor(face_detector, db_handler)

# Start video processing
video_processor.start()

# Set mode for attendance tracking
video_processor.set_attendance_mode(True, "Python Class")

# Get the processed frame
frame = video_processor.get_frame()
```

## UI Selection

The system allows users to choose between the Modern and Classic UI. This preference can be saved and remembered for future sessions:

```python
from src.ui.ui_selector import select_ui

# Let the user select a UI
ui_type = select_ui()

# Launch the appropriate UI
if ui_type == "modern":
    from src.ui.modern_launcher import launch_modern_ui
    launch_modern_ui()
else:
    from src.ui.classic_launcher import launch_classic_ui
    launch_classic_ui()
```

## Benefits of the New Structure

1. **Reduced Code Duplication**: Core functionality is shared between UIs
2. **Improved Maintenance**: Bug fixes in core components benefit both UIs
3. **Consistent Behavior**: Both UIs behave the same way for core functionality
4. **Better Extensibility**: Easier to add new features or a third UI type
5. **Enhanced Configuration**: Unified configuration system with reasonable defaults

## Migration Notes

When migrating from the old structure to the new one:

1. Update imports to use core components
2. Replace face detection code with the unified FaceDetector
3. Replace database code with the unified DatabaseHandler
4. Use the ConfigManager for configuration options
5. Use the VideoProcessor for video capture and processing

Example of migrating a UI component:

```python
# Old code
from src.face_recognition.detector import FaceDetector
from src.database.sqlite_handler import SQLiteHandler

# New code
from src.core.face_recognition.face_detector import FaceDetector
from src.core.database.db_handler import DatabaseHandler
from src.core.utils.config_manager import ConfigManager
from src.core.utils.video_processor import VideoProcessor
```

## Future Improvements

The new structure enables several future improvements:

1. More UI themes and customization options
2. Additional face detection models
3. Enhanced reporting and analytics
4. Cloud synchronization of attendance data
5. Mobile companion app

For any issues or questions about the new structure, please refer to the project documentation or contact the development team. 