"""
Student Controller for the Face Detection Attendance System
"""
import os
import logging
from typing import Dict, List, Any, Optional, Tuple
import datetime
import shutil

from .base_controller import BaseController
from ..models.student_model import StudentModel
from ..database.db_manager import DatabaseManager
from ..face_recognition.detector import FaceDetector
from ..utils.exceptions import DatabaseError, ValidationError, ImageProcessingError
from ..utils.image_utils import validate_image, optimize_image
from ..utils.app_config import AppConfig

class StudentController(BaseController):
    """
    Controller for handling student operations
    
    Attributes:
        db: Database connection
        model: Student model instance
        face_detector: Face detection component
        config: Application configuration
    """
    
    def __init__(self, db_connection=None):
        """
        Initialize student controller
        
        Args:
            db_connection: Optional database connection to use
        """
        super().__init__()
        
        # Initialize database connection
        self.db = db_connection if db_connection else DatabaseManager()
        
        # Initialize model
        self.model = StudentModel(self.db)
        
        # Initialize face detector with None (lazy initialization)
        self._face_detector = None
        
        # Load configuration
        self.config = AppConfig()
        
        # Initialize paths from configuration
        self.training_images_path = self.config.get("training.images_directory", "TrainingImage")
        self.training_labels_path = self.config.get("training.labels_directory", "TrainingImageLabel")
        
    @property
    def face_detector(self) -> FaceDetector:
        """Lazy initialization of face detector"""
        if self._face_detector is None:
            self._face_detector = FaceDetector()
        return self._face_detector
        
    def initialize(self) -> bool:
        """Initialize the controller"""
        try:
            super().initialize()
            
            # Ensure model is initialized
            if not self.model.initialize():
                self.logger.error("Failed to initialize student model")
                return False
                
            # Ensure directories exist
            os.makedirs(self.training_images_path, exist_ok=True)
            os.makedirs(self.training_labels_path, exist_ok=True)
            
            self.logger.info("StudentController initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error initializing StudentController: {e}")
            return False
            
    def cleanup(self) -> bool:
        """Clean up resources"""
        try:
            super().cleanup()
            
            # Clean up face detector if initialized
            if self._face_detector:
                self._face_detector.cleanup()
                
            # Clean up model
            if self.model:
                self.model.cleanup()
                
            self.logger.info("StudentController cleaned up successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error cleaning up StudentController: {e}")
            return False
    
    def validate_student_data(self, data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate student data
        
        Args:
            data: Student data to validate
            
        Returns:
            Tuple containing (is_valid, error_message)
        """
        try:
            # Check required fields
            required_fields = ["enrollment", "name"]
            for field in required_fields:
                if field not in data or not data[field]:
                    return False, f"Missing required field: {field}"
            
            # Validate enrollment format (alphanumeric)
            if not data["enrollment"].isalnum():
                return False, "Enrollment ID must be alphanumeric"
            
            # Check if student already exists
            if self.model.student_exists(data["enrollment"]):
                return False, f"Student with enrollment {data['enrollment']} already exists"
            
            return True, None
        except Exception as e:
            self.logger.error(f"Error validating student data: {e}")
            return False, f"Validation error: {str(e)}"
    
    def add_student(self, enrollment: str, name: str) -> Dict[str, Any]:
        """
        Add a new student
        
        Args:
            enrollment: Student enrollment ID
            name: Student name
            
        Returns:
            Dict containing result of the operation
        """
        try:
            # Create student data
            student_data = {
                "enrollment": enrollment,
                "name": name
            }
            
            # Validate data
            is_valid, error_message = self.validate_student_data(student_data)
            if not is_valid:
                raise ValidationError(error_message)
            
            # Add student to database
            success = self.model.add_student(enrollment, name)
            
            if not success:
                raise DatabaseError("Failed to add student to the database")
            
            # Return success response
            return {
                "success": True,
                "data": {
                    "enrollment": enrollment,
                    "name": name
                },
                "message": f"Student {name} added successfully"
            }
        except ValidationError as e:
            self.logger.warning(f"Validation error when adding student: {e}")
            return self.handle_exception(e, {"enrollment": enrollment, "name": name})
        except DatabaseError as e:
            self.logger.error(f"Database error when adding student: {e}")
            return self.handle_exception(e, {"enrollment": enrollment, "name": name})
        except Exception as e:
            self.logger.error(f"Unexpected error when adding student: {e}")
            return self.handle_exception(e, {"enrollment": enrollment, "name": name})
    
    def capture_training_images(self, enrollment: str, name: str, frame) -> Dict[str, Any]:
        """
        Capture and save training images for face recognition
        
        Args:
            enrollment: Student enrollment ID
            name: Student name
            frame: Image frame from camera
            
        Returns:
            Dict containing result of the operation
        """
        try:
            # Validate the image
            if not validate_image(frame):
                raise ImageProcessingError("Invalid image frame")
            
            # Check if student exists
            if not self.model.student_exists(enrollment):
                # Add student if not exists
                self.add_student(enrollment, name)
            
            # Detect face in the image
            face_locations = self.face_detector.detect_faces(frame)
            if not face_locations:
                raise ImageProcessingError("No face detected in the image")
            
            # Get sample count from configuration
            samples_count = self.config.get("training.samples_per_person", 20)
            
            # Get existing image count
            existing_images = len([f for f in os.listdir(self.training_images_path) 
                                 if f.startswith(f"{enrollment}_")])
            
            # Save image with optimized quality
            image_index = existing_images + 1
            if image_index <= samples_count:
                image_path = os.path.join(
                    self.training_images_path, 
                    f"{enrollment}_{name.replace(' ', '_')}_{image_index}.jpg"
                )
                
                # Optimize and save the image
                optimized_image = optimize_image(frame, face_locations[0])
                optimized_image.save(image_path)
                
                return {
                    "success": True,
                    "data": {
                        "enrollment": enrollment,
                        "name": name,
                        "image_path": image_path,
                        "image_count": image_index,
                        "remaining": samples_count - image_index
                    },
                    "message": f"Image {image_index}/{samples_count} captured"
                }
            else:
                return {
                    "success": True,
                    "data": {
                        "enrollment": enrollment,
                        "name": name,
                        "image_count": existing_images,
                        "remaining": 0
                    },
                    "message": f"All {samples_count} images have been captured"
                }
                
        except ImageProcessingError as e:
            self.logger.warning(f"Image processing error: {e}")
            return self.handle_exception(e, {"enrollment": enrollment, "name": name})
        except Exception as e:
            self.logger.error(f"Error capturing training image: {e}")
            return self.handle_exception(e, {"enrollment": enrollment, "name": name})
    
    def train_recognition_model(self) -> Dict[str, Any]:
        """
        Train the face recognition model using captured images
        
        Returns:
            Dict containing result of the operation
        """
        try:
            # Check if training images exist
            if not os.path.exists(self.training_images_path) or not os.listdir(self.training_images_path):
                raise ValidationError("No training images found")
            
            # Train the model
            result = self.face_detector.train_model(
                training_images_path=self.training_images_path,
                training_labels_path=self.training_labels_path
            )
            
            if not result["success"]:
                raise Exception(f"Training failed: {result.get('message', 'Unknown error')}")
            
            return {
                "success": True,
                "data": result.get("data", {}),
                "message": "Face recognition model trained successfully"
            }
        except ValidationError as e:
            self.logger.warning(f"Validation error when training model: {e}")
            return self.handle_exception(e, {})
        except Exception as e:
            self.logger.error(f"Error training recognition model: {e}")
            return self.handle_exception(e, {})
    
    def get_all_students(self) -> Dict[str, Any]:
        """
        Get all students from the database
        
        Returns:
            Dict containing result of the operation
        """
        try:
            students = self.model.get_all_students()
            
            return {
                "success": True,
                "data": {
                    "students": students,
                    "count": len(students)
                }
            }
        except Exception as e:
            self.logger.error(f"Error getting all students: {e}")
            return self.handle_exception(e, {})
    
    def delete_student(self, enrollment: str) -> Dict[str, Any]:
        """
        Delete a student and their training images
        
        Args:
            enrollment: Student enrollment ID
            
        Returns:
            Dict containing result of the operation
        """
        try:
            # Check if student exists
            if not self.model.student_exists(enrollment):
                raise ValidationError(f"Student with enrollment {enrollment} not found")
            
            # Get student name before deletion
            student = self.model.get_student(enrollment)
            student_name = student.get('name', 'Unknown')
            
            # Delete student from database
            success = self.model.delete_student(enrollment)
            
            if not success:
                raise DatabaseError(f"Failed to delete student {enrollment} from the database")
            
            # Delete training images
            deleted_image_count = 0
            for filename in os.listdir(self.training_images_path):
                if filename.startswith(f"{enrollment}_"):
                    file_path = os.path.join(self.training_images_path, filename)
                    os.remove(file_path)
                    deleted_image_count += 1
            
            # Return success response
            return {
                "success": True,
                "data": {
                    "enrollment": enrollment,
                    "name": student_name,
                    "deleted_images": deleted_image_count
                },
                "message": f"Student {enrollment} ({student_name}) deleted successfully"
            }
        except ValidationError as e:
            self.logger.warning(f"Validation error when deleting student: {e}")
            return self.handle_exception(e, {"enrollment": enrollment})
        except DatabaseError as e:
            self.logger.error(f"Database error when deleting student: {e}")
            return self.handle_exception(e, {"enrollment": enrollment})
        except Exception as e:
            self.logger.error(f"Unexpected error when deleting student: {e}")
            return self.handle_exception(e, {"enrollment": enrollment})