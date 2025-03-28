"""
Attendance Controller for the Face Detection Attendance System
"""
import os
import datetime
from typing import Dict, List, Any, Optional, Tuple
import logging

from .base_controller import BaseController
from ..models.attendance_model import AttendanceModel
from ..database.enhanced_db import EnhancedDB
from ..face_recognition.detector import FaceDetector
from ..utils.exceptions import (
    DatabaseError, 
    RecognitionError, 
    ValidationError
)

class AttendanceController(BaseController):
    """
    Controller for handling attendance operations
    
    Attributes:
        db: Database connection
        model: Attendance model instance
        face_detector: Face detection component
    """
    
    def __init__(self, db_connection: Optional[EnhancedDB] = None):
        """
        Initialize attendance controller
        
        Args:
            db_connection: Optional database connection to use
        """
        super().__init__()
        
        # Initialize database connection
        self.db = db_connection if db_connection else EnhancedDB()
        
        # Initialize model
        self.model = AttendanceModel(self.db)
        self.model_instance = self.model
        
        # Initialize face detector with None (lazy initialization)
        self._face_detector = None
    
    @property
    def face_detector(self) -> FaceDetector:
        """
        Lazy initialization of face detector
        
        Returns:
            FaceDetector instance
        """
        if self._face_detector is None:
            self._face_detector = FaceDetector()
        return self._face_detector
    
    def initialize(self) -> bool:
        """
        Initialize the controller
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            super().initialize()
            
            # Ensure model is initialized
            if not self.model.initialize():
                self.logger.error("Failed to initialize attendance model")
                return False
            
            self.logger.info("AttendanceController initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error initializing AttendanceController: {e}")
            return False
    
    def cleanup(self) -> bool:
        """
        Clean up resources
        
        Returns:
            bool: True if cleanup successful, False otherwise
        """
        try:
            super().cleanup()
            
            # Clean up face detector if initialized
            if self._face_detector:
                self._face_detector.cleanup()
            
            # Clean up model
            if self.model:
                self.model.cleanup()
            
            self.logger.info("AttendanceController cleaned up successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error cleaning up AttendanceController: {e}")
            return False
    
    def validate_attendance_data(self, data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate attendance data
        
        Args:
            data: Attendance data to validate
            
        Returns:
            Tuple containing (is_valid, error_message)
        """
        try:
            # Check required fields
            required_fields = ["enrollment", "name", "subject"]
            for field in required_fields:
                if field not in data or not data[field]:
                    return False, f"Missing required field: {field}"
            
            # Validate enrollment format (alphanumeric)
            if not data["enrollment"].isalnum():
                return False, "Enrollment ID must be alphanumeric"
            
            # Validate subject (non-empty string)
            if not isinstance(data["subject"], str) or len(data["subject"]) < 1:
                return False, "Subject must be a non-empty string"
            
            return True, None
        except Exception as e:
            self.logger.error(f"Error validating attendance data: {e}")
            return False, f"Validation error: {str(e)}"
    
    def mark_attendance(self, enrollment: str, name: str, subject: str, 
                       confidence: float = 1.0) -> Dict[str, Any]:
        """
        Mark attendance for a student
        
        Args:
            enrollment: Student enrollment ID
            name: Student name
            subject: Subject name
            confidence: Recognition confidence score
            
        Returns:
            Dict containing result of the operation
        """
        try:
            # Create attendance data
            attendance_data = {
                "enrollment": enrollment,
                "name": name,
                "subject": subject,
                "confidence": confidence
            }
            
            # Validate data
            is_valid, error_message = self.validate_attendance_data(attendance_data)
            if not is_valid:
                raise ValidationError(error_message)
            
            # Get current date and time
            now = datetime.datetime.now()
            date = now.strftime("%Y-%m-%d")
            time = now.strftime("%H:%M:%S")
            
            # Mark attendance in the database
            success = self.model.mark_attendance(
                enrollment=enrollment,
                name=name,
                subject=subject,
                date=date,
                time=time,
                confidence=confidence
            )
            
            if not success:
                raise DatabaseError("Failed to mark attendance in the database")
            
            # Return success response
            return {
                "success": True,
                "data": {
                    "enrollment": enrollment,
                    "name": name,
                    "subject": subject,
                    "date": date,
                    "time": time,
                    "confidence": confidence
                }
            }
        except ValidationError as e:
            self.logger.warning(f"Validation error when marking attendance: {e}")
            return self.handle_exception(e, {"enrollment": enrollment, "subject": subject})
        except DatabaseError as e:
            self.logger.error(f"Database error when marking attendance: {e}")
            return self.handle_exception(e, {"enrollment": enrollment, "subject": subject})
        except Exception as e:
            self.logger.error(f"Unexpected error when marking attendance: {e}")
            return self.handle_exception(e, {"enrollment": enrollment, "subject": subject})
    
    def recognize_and_mark_attendance(self, image_array, subject: str) -> Dict[str, Any]:
        """
        Recognize face in image and mark attendance
        
        Args:
            image_array: Numpy array containing the image
            subject: Subject name
            
        Returns:
            Dict containing result of the operation
        """
        try:
            # Recognize face
            recognition_result = self.face_detector.recognize_face(image_array)
            
            if not recognition_result:
                raise RecognitionError("No face recognized in the image")
            
            # Use student_id instead of enrollment
            enrollment = recognition_result["student_id"]
            name = recognition_result["name"]
            confidence = recognition_result["confidence"]
            
            # Check confidence threshold
            if confidence < 0.65:  # Configurable threshold
                raise RecognitionError(f"Recognition confidence too low: {confidence:.2f}")
            
            # Mark attendance
            return self.mark_attendance(
                enrollment=enrollment,
                name=name,
                subject=subject,
                confidence=confidence
            )
        except RecognitionError as e:
            self.logger.warning(f"Recognition error: {e}")
            return self.handle_exception(e, {"subject": subject})
        except Exception as e:
            self.logger.error(f"Error in recognize_and_mark_attendance: {e}")
            return self.handle_exception(e, {"subject": subject})
    
    def get_attendance_records(self, subject: Optional[str] = None, 
                              date: Optional[str] = None, 
                              student_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get attendance records
        
        Args:
            subject: Optional subject filter
            date: Optional date filter
            student_id: Optional student ID filter
            
        Returns:
            Dict containing result of the operation
        """
        try:
            # Get records from model
            records = self.model.get_attendance_records(
                subject=subject,
                date=date,
                student_id=student_id
            )
            
            return {
                "success": True,
                "data": {
                    "records": records,
                    "count": len(records),
                    "filters": {
                        "subject": subject,
                        "date": date,
                        "student_id": student_id
                    }
                }
            }
        except Exception as e:
            self.logger.error(f"Error getting attendance records: {e}")
            return self.handle_exception(e, {
                "subject": subject,
                "date": date,
                "student_id": student_id
            })
    
    def get_attendance_statistics(self, subject: Optional[str] = None, 
                                start_date: Optional[str] = None, 
                                end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Get attendance statistics
        
        Args:
            subject: Optional subject filter
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            Dict containing result of the operation
        """
        try:
            # Get statistics from model
            statistics = self.model.get_attendance_statistics(
                subject=subject,
                start_date=start_date,
                end_date=end_date
            )
            
            return {
                "success": True,
                "data": statistics
            }
        except Exception as e:
            self.logger.error(f"Error getting attendance statistics: {e}")
            return self.handle_exception(e, {
                "subject": subject,
                "start_date": start_date,
                "end_date": end_date
            })