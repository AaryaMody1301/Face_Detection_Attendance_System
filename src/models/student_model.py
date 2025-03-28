"""
Student Model for the Face Detection Attendance System
"""
import logging
from typing import Dict, List, Any, Optional, Tuple
import sqlite3

class StudentModel:
    """
    Model class for handling student data operations
    
    Attributes:
        db: Database connection
        logger: Logger instance
    """
    
    def __init__(self, db_connection):
        """
        Initialize student model
        
        Args:
            db_connection: Database connection to use
        """
        self.db = db_connection
        self.logger = logging.getLogger(__name__)
    
    def initialize(self) -> bool:
        """
        Initialize the model
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            # Ensure database has required tables
            self._ensure_tables_exist()
            self.logger.info("StudentModel initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error initializing StudentModel: {e}")
            return False
    
    def cleanup(self) -> bool:
        """
        Clean up resources
        
        Returns:
            bool: True if cleanup successful, False otherwise
        """
        # No specific cleanup needed for this model
        return True
    
    def _ensure_tables_exist(self):
        """Ensure the necessary tables exist in the database"""
        try:
            # Create students table if it doesn't exist
            query = '''
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                enrollment TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                email TEXT,
                department TEXT,
                year TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
            '''
            self.db.execute_query(query)
        except Exception as e:
            self.logger.error(f"Error ensuring tables exist: {e}")
            raise
    
    def add_student(self, enrollment: str, name: str, 
                    email: str = None, department: str = None, 
                    year: str = None) -> bool:
        """
        Add a new student to the database
        
        Args:
            enrollment: Student enrollment ID
            name: Student name
            email: Student email address
            department: Student department
            year: Student year
            
        Returns:
            bool: True if student added successfully, False otherwise
        """
        try:
            # Check if student already exists
            if self.student_exists(enrollment):
                self.logger.warning(f"Student with enrollment {enrollment} already exists")
                return False
                
            # Insert new student
            query = '''
            INSERT INTO students (enrollment, name, email, department, year)
            VALUES (?, ?, ?, ?, ?)
            '''
            params = (enrollment, name, email, department, year)
            self.db.execute_query(query, params, commit=True)
            
            self.logger.info(f"Student {enrollment} ({name}) added successfully")
            return True
        except sqlite3.IntegrityError as e:
            self.logger.error(f"Database integrity error when adding student: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error adding student: {e}")
            return False
    
    def update_student(self, enrollment: str, name: str = None, 
                       email: str = None, department: str = None, 
                       year: str = None, is_active: bool = None) -> bool:
        """
        Update an existing student
        
        Args:
            enrollment: Student enrollment ID
            name: Student name
            email: Student email address
            department: Student department
            year: Student year
            is_active: Student active status
            
        Returns:
            bool: True if student updated successfully, False otherwise
        """
        try:
            # Check if student exists
            if not self.student_exists(enrollment):
                self.logger.warning(f"Student with enrollment {enrollment} does not exist")
                return False
                
            # Build update query
            query_parts = []
            params = []
            
            if name is not None:
                query_parts.append("name = ?")
                params.append(name)
                
            if email is not None:
                query_parts.append("email = ?")
                params.append(email)
                
            if department is not None:
                query_parts.append("department = ?")
                params.append(department)
                
            if year is not None:
                query_parts.append("year = ?")
                params.append(year)
                
            if is_active is not None:
                query_parts.append("is_active = ?")
                params.append(1 if is_active else 0)
                
            # Add last_updated timestamp
            query_parts.append("last_updated = CURRENT_TIMESTAMP")
            
            # No fields to update
            if not query_parts:
                self.logger.warning("No fields provided for update")
                return False
                
            # Build and execute query
            query = f'''
            UPDATE students
            SET {', '.join(query_parts)}
            WHERE enrollment = ?
            '''
            params.append(enrollment)
            
            self.db.execute_query(query, tuple(params), commit=True)
            
            self.logger.info(f"Student {enrollment} updated successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error updating student: {e}")
            return False
    
    def delete_student(self, enrollment: str) -> bool:
        """
        Delete a student
        
        Args:
            enrollment: Student enrollment ID
            
        Returns:
            bool: True if student deleted successfully, False otherwise
        """
        try:
            # Check if student exists
            if not self.student_exists(enrollment):
                self.logger.warning(f"Student with enrollment {enrollment} does not exist")
                return False
                
            # Delete student
            query = 'DELETE FROM students WHERE enrollment = ?'
            self.db.execute_query(query, (enrollment,), commit=True)
            
            self.logger.info(f"Student {enrollment} deleted successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error deleting student: {e}")
            return False
    
    def get_student(self, enrollment: str) -> Dict[str, Any]:
        """
        Get student details
        
        Args:
            enrollment: Student enrollment ID
            
        Returns:
            Dict containing student details or empty dict if not found
        """
        try:
            query = '''
            SELECT id, enrollment, name, email, department, year,
                   created_at, last_updated, is_active
            FROM students
            WHERE enrollment = ?
            '''
            result = self.db.execute_query(query, (enrollment,), fetch_one=True)
            
            if result:
                # Convert to dictionary
                student = {
                    "id": result[0],
                    "enrollment": result[1],
                    "name": result[2],
                    "email": result[3],
                    "department": result[4],
                    "year": result[5],
                    "created_at": result[6],
                    "last_updated": result[7],
                    "is_active": bool(result[8])
                }
                return student
            else:
                return {}
        except Exception as e:
            self.logger.error(f"Error getting student: {e}")
            return {}
    
    def get_all_students(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get all students
        
        Args:
            active_only: If True, return only active students
            
        Returns:
            List of dictionaries containing student details
        """
        try:
            query = '''
            SELECT id, enrollment, name, email, department, year,
                   created_at, last_updated, is_active
            FROM students
            '''
            
            if active_only:
                query += ' WHERE is_active = 1'
                
            query += ' ORDER BY name ASC'
            
            results = self.db.execute_query(query, fetch_all=True)
            
            students = []
            for row in results:
                student = {
                    "id": row[0],
                    "enrollment": row[1],
                    "name": row[2],
                    "email": row[3],
                    "department": row[4],
                    "year": row[5],
                    "created_at": row[6],
                    "last_updated": row[7],
                    "is_active": bool(row[8])
                }
                students.append(student)
                
            return students
        except Exception as e:
            self.logger.error(f"Error getting all students: {e}")
            return []
    
    def student_exists(self, enrollment: str) -> bool:
        """
        Check if a student exists
        
        Args:
            enrollment: Student enrollment ID
            
        Returns:
            bool: True if student exists, False otherwise
        """
        try:
            query = 'SELECT COUNT(*) FROM students WHERE enrollment = ?'
            result = self.db.execute_query(query, (enrollment,), fetch_one=True)
            
            return result[0] > 0
        except Exception as e:
            self.logger.error(f"Error checking if student exists: {e}")
            return False
    
    def search_students(self, search_term: str) -> List[Dict[str, Any]]:
        """
        Search for students by name or enrollment ID
        
        Args:
            search_term: Search term
            
        Returns:
            List of dictionaries containing student details
        """
        try:
            # Add wildcards for partial matching
            search_pattern = f"%{search_term}%"
            
            query = '''
            SELECT id, enrollment, name, email, department, year,
                   created_at, last_updated, is_active
            FROM students
            WHERE enrollment LIKE ? OR name LIKE ?
            ORDER BY name ASC
            '''
            
            results = self.db.execute_query(query, (search_pattern, search_pattern), fetch_all=True)
            
            students = []
            for row in results:
                student = {
                    "id": row[0],
                    "enrollment": row[1],
                    "name": row[2],
                    "email": row[3],
                    "department": row[4],
                    "year": row[5],
                    "created_at": row[6],
                    "last_updated": row[7],
                    "is_active": bool(row[8])
                }
                students.append(student)
                
            return students
        except Exception as e:
            self.logger.error(f"Error searching students: {e}")
            return []
    
    def count_students(self, active_only: bool = True) -> int:
        """
        Get the total number of students
        
        Args:
            active_only: If True, count only active students
            
        Returns:
            int: Number of students
        """
        try:
            query = 'SELECT COUNT(*) FROM students'
            
            if active_only:
                query += ' WHERE is_active = 1'
                
            result = self.db.execute_query(query, fetch_one=True)
            
            return result[0]
        except Exception as e:
            self.logger.error(f"Error counting students: {e}")
            return 0