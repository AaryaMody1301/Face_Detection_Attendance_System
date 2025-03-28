"""
Attendance Model for the Face Detection Attendance System
"""
import os
import datetime
import logging
from typing import Dict, List, Any, Optional

from ..utils.exceptions import DatabaseError
from ..database.enhanced_db import EnhancedDB

class AttendanceModel:
    """
    Model class for handling attendance data operations
    
    Attributes:
        db: Database connection
        logger: Logger instance
    """
    
    def __init__(self, db_connection: Optional[EnhancedDB] = None):
        """
        Initialize the attendance model
        
        Args:
            db_connection: Optional database connection to use
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize database connection
        self.db = db_connection if db_connection else EnhancedDB()
    
    def initialize(self) -> bool:
        """
        Initialize the model
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            self.logger.info("Initializing AttendanceModel")
            # Additional initialization if needed
            return True
        except Exception as e:
            self.logger.error(f"Error initializing AttendanceModel: {e}")
            return False
    
    def cleanup(self) -> bool:
        """
        Clean up resources
        
        Returns:
            bool: True if cleanup successful, False otherwise
        """
        try:
            self.logger.info("Cleaning up AttendanceModel")
            # Additional cleanup if needed
            return True
        except Exception as e:
            self.logger.error(f"Error cleaning up AttendanceModel: {e}")
            return False
    
    def create_session(self, subject: str, date: str, time: str) -> Optional[int]:
        """
        Create a new attendance session
        
        Args:
            subject: Subject name
            date: Date in YYYY-MM-DD format
            time: Time in HH:MM:SS format
            
        Returns:
            int: Session ID or None on failure
        """
        try:
            session_id = self.db.create_attendance_record(subject, date, time)
            if not session_id:
                self.logger.error("Failed to create attendance session")
                raise DatabaseError("Failed to create attendance session")
            return session_id
        except Exception as e:
            self.logger.error(f"Error creating attendance session: {e}")
            return None
    
    def mark_attendance(self, enrollment: str, name: str, subject: str, 
                        date: str, time: str, confidence: float = 1.0) -> bool:
        """
        Mark attendance for a student
        
        Args:
            enrollment: Student enrollment ID
            name: Student name
            subject: Subject name
            date: Date in YYYY-MM-DD format
            time: Time in HH:MM:SS format
            confidence: Recognition confidence score
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Mark attendance in the database
            success = self.db.mark_attendance(
                enrollment=enrollment,
                name=name,
                subject=subject,
                date=date,
                time=time,
                confidence=confidence
            )
            
            if not success:
                self.logger.error("Failed to mark attendance")
                return False
            
            self.logger.info(f"Attendance marked for {enrollment} in {subject}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error marking attendance: {e}")
            return False
    
    def get_attendance_records(self, subject: Optional[str] = None, 
                             date: Optional[str] = None, 
                             student_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get attendance records
        
        Args:
            subject: Optional subject filter
            date: Optional date filter
            student_id: Optional student ID filter
            
        Returns:
            List of attendance record dictionaries
        """
        try:
            records = self.db.get_attendance_records(
                subject=subject,
                date=date,
                student_id=student_id
            )
            
            return records
            
        except Exception as e:
            self.logger.error(f"Error getting attendance records: {e}")
            return []
    
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
            Dict containing attendance statistics
        """
        try:
            statistics = self.db.get_attendance_statistics(
                subject=subject,
                start_date=start_date,
                end_date=end_date
            )
            
            return statistics
            
        except Exception as e:
            self.logger.error(f"Error getting attendance statistics: {e}")
            return {
                "total_attendance": 0,
                "unique_students": 0,
                "attendance_by_date": {},
                "top_subjects": {}
            }
    
    def get_student_attendance_summary(self, student_id: str) -> Dict[str, Any]:
        """
        Get attendance summary for a specific student
        
        Args:
            student_id: Student enrollment ID
            
        Returns:
            Dict containing student attendance summary
        """
        try:
            # Get all attendance records for the student
            records = self.get_attendance_records(student_id=student_id)
            
            # Process records to create summary
            subjects = {}
            dates = []
            
            for record in records:
                subject = record["subject"]
                date = record["date"]
                
                # Track unique dates
                if date not in dates:
                    dates.append(date)
                
                # Count by subject
                if subject not in subjects:
                    subjects[subject] = 1
                else:
                    subjects[subject] += 1
            
            # Create summary
            summary = {
                "student_id": student_id,
                "total_attendance": len(records),
                "unique_dates": len(dates),
                "attendance_by_subject": subjects,
                "latest_record": records[0] if records else None
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error getting student attendance summary: {e}")
            return {
                "student_id": student_id,
                "total_attendance": 0,
                "unique_dates": 0,
                "attendance_by_subject": {},
                "latest_record": None
            }
    
    def export_attendance_report(self, subject: str, start_date: Optional[str] = None, 
                               end_date: Optional[str] = None, 
                               format: str = "csv") -> Optional[str]:
        """
        Export attendance report to a file
        
        Args:
            subject: Subject name
            start_date: Optional start date filter
            end_date: Optional end date filter
            format: Report format ("csv" or "json")
            
        Returns:
            str: Path to the generated report file or None on failure
        """
        try:
            # Get records
            records = self.get_attendance_records(
                subject=subject,
                date=start_date if start_date == end_date else None
            )
            
            # Filter by date range if needed
            if start_date and end_date and start_date != end_date:
                filtered_records = []
                for record in records:
                    if start_date <= record["date"] <= end_date:
                        filtered_records.append(record)
                records = filtered_records
            
            if not records:
                self.logger.warning(f"No records found for subject {subject}")
                return None
            
            # Create output directory if it doesn't exist
            os.makedirs("Reports", exist_ok=True)
            
            # Generate filename
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"Reports/{subject}_{timestamp}.{format}"
            
            if format == "csv":
                self._export_to_csv(records, filename)
            elif format == "json":
                self._export_to_json(records, filename)
            else:
                self.logger.error(f"Unsupported report format: {format}")
                return None
            
            self.logger.info(f"Attendance report exported to {filename}")
            return filename
            
        except Exception as e:
            self.logger.error(f"Error exporting attendance report: {e}")
            return None
    
    def _export_to_csv(self, records: List[Dict[str, Any]], filename: str) -> None:
        """
        Export records to CSV file
        
        Args:
            records: List of record dictionaries
            filename: Output filename
        """
        import csv
        
        with open(filename, "w", newline="") as file:
            if not records:
                return
                
            # Get field names from the first record
            fieldnames = list(records[0].keys())
            
            # Write CSV file
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)
    
    def _export_to_json(self, records: List[Dict[str, Any]], filename: str) -> None:
        """
        Export records to JSON file
        
        Args:
            records: List of record dictionaries
            filename: Output filename
        """
        import json
        
        with open(filename, "w") as file:
            json.dump(records, file, indent=4)