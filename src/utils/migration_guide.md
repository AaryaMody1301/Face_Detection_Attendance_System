# Migration Guide: Moving to the Core Module Structure

This guide is intended to help developers migrate their code to use the new core module structure in the Face Detection Attendance System.

## Overview of Changes

The Face Detection Attendance System has been restructured to use a shared core module for common functionality. This improves code reuse between the classic and modern UIs and standardizes key components.

### Key Changes

1. **Core Module Structure**: Common functionality is now in `src/core/`
2. **Unified Face Detection**: Consolidated face detection in `src/core/face_recognition/face_detector.py`
3. **Unified Database**: Common database operations in `src/core/database/db_handler.py`
4. **Centralized Configuration**: Shared configuration in `src/core/utils/config_manager.py`
5. **Compatibility Layer**: To ease migration, a compatibility layer was added in `src/core/utils/compatibility.py`

## Updating Import Statements

### Old Import Style
```python
from src.utils.config_manager import ConfigManager
from src.face_recognition.detector import Detector
from src.database.sqlite_handler import SQLiteHandler
```

### New Import Style
```python
from src.core.utils.config_manager import ConfigManager
from src.core.face_recognition.face_detector import FaceDetector
from src.core.database.db_handler import DatabaseHandler
```

## Compatibility Layer

To make the migration smoother, a compatibility layer is provided that will redirect old imports to the new locations and issue deprecation warnings. This allows you to update your code gradually.

The compatibility layer is automatically set up when the application starts. For example, if your code imports from `src.utils.config_manager`, it will still work but will show a deprecation warning.

## Specific Migration Steps

### Configuration Management

**Old Code:**
```python
from src.utils.config_manager import ConfigManager
config = ConfigManager()
value = config.get_config().get('section', {}).get('key', default)
```

**New Code:**
```python
from src.core.utils.config_manager import ConfigManager
config = ConfigManager()
value = config.get('section.key', default)
```

### Face Detection/Recognition

**Old Code:**
```python
from src.face_recognition.detector import Detector
detector = Detector(method='haar_cascade')
faces = detector.detect_faces(frame)
```

**New Code:**
```python
from src.core.face_recognition.face_detector import FaceDetector
detector = FaceDetector(method='hybrid')
faces_with_info = detector.detect_and_recognize(frame)
```

### Database Operations

**Old Code:**
```python
from src.database.sqlite_handler import SQLiteHandler
db = SQLiteHandler('attendance.db')
db.add_student('12345', 'John Doe')
```

**New Code:**
```python
from src.core.database.db_handler import DatabaseHandler
db = DatabaseHandler()  # Default location is Data/attendance.db
db.add_student('12345', 'John Doe')
```

## API Changes

### ConfigManager

- Added `get(key, default=None)` method for dot-notation access to nested config
- Added `set(key, value)` method for dot-notation updates to nested config
- Added `reset(key=None)` method to reset config to defaults
- Added `export()` and `import_config()` methods for backup/restore

### FaceDetector

- Renamed `detect_faces()` to `detect_faces_only()`
- Added `detect_and_recognize()` for combined detection and recognition
- Added support for multiple detection methods with the `method` parameter
- Added confidence threshold control with the `threshold` parameter

### DatabaseHandler

- Unified student management and attendance tracking
- Added automatic CSV compatibility for backward compatibility
- Added analytics support with `get_attendance_statistics()`
- Added improved backup and restore capabilities

## Common Migration Issues

1. **Import Errors**: Update your import statements to use the new module structure.
2. **API Changes**: Update method calls to use the new unified APIs.
3. **Configuration Access**: Use dot notation with `get()` instead of nested dictionary access.
4. **Class Name Changes**: Update class names (e.g., `Detector` → `FaceDetector`).
5. **Thread Safety**: SQLite connections should be managed carefully in threaded code.

## Testing Your Migration

It's recommended to test your code thoroughly after migration:

1. Run the application with both UI types to verify functionality
2. Check for deprecation warnings in the console
3. Verify that attendance tracking works properly
4. Test database operations
5. Test configuration changes

## Getting Help

If you encounter issues during migration, consult:

1. Core module docstrings for detailed API documentation
2. The compatibility layer in `src/core/utils/compatibility.py` 
3. The README_NEW_STRUCTURE.md file for design overview

## Timeline

The compatibility layer will be maintained for the next three releases, after which the old module structure will be removed entirely. It's recommended to complete your migration before that time. 