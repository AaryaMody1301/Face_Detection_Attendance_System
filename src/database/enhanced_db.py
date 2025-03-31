"""
Enhanced Database Handler for Face Detection Attendance System

This module provides a robust SQLite database interface for the attendance system.
"""
import os
import sqlite3
import pandas as pd
import logging
import csv
import datetime
import shutil
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

class EnhancedDB:
    """
    Enhanced SQLite database handler for Face Detection Attendance System
    
    Provides functions to manage students, attendance records, and subjects
    """
    
    def __init__(self, db_path="Data/attendance.db"):
        """
        Initialize the database handler
        
        Args:
            db_path (str): Path to SQLite database file
        """
        # Ensure directories exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.db_path = db_path
        self.connection = None
        self.cursor = None
        
        # Initialize the database
        self._connect()
        self._create_tables()
    
    def _connect(self):
        """Establish connection to the database"""
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row  # Return rows as dictionaries
            self.cursor = self.connection.cursor()
            logger.info(f"Connected to database: {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Database connection error: {e}")
            raise
    
    def _create_tables(self):
        """Create necessary tables if they don't exist"""
        try:
            # Create students table
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS students (
                enrollment TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Create attendance table
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                enrollment TEXT,
                name TEXT,
                subject TEXT,
                date TEXT,
                time TEXT,
                file_path TEXT,
                FOREIGN KEY (enrollment) REFERENCES students(enrollment)
            )
            ''')
            
            # Create subjects table
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
            ''')
            
            # Add default subjects if there aren't any
            self.cursor.execute('SELECT COUNT(*) FROM subjects')
            count = self.cursor.fetchone()[0]
            
            if count == 0:
                default_subjects = [
                    ("Python",),
                    ("Java",),
                    ("Web Dev",),
                    ("Data Science",)
                ]
                self.cursor.executemany(
                    'INSERT INTO subjects (name) VALUES (?)',
                    default_subjects
                )
            
            # Commit changes
            self.connection.commit()
            logger.info("Database tables initialized")
        except sqlite3.Error as e:
            logger.error(f"Error creating tables: {e}")
            raise
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
            self.cursor = None
            logger.info("Database connection closed")
    
    def __del__(self):
        """Destructor to ensure connection is closed"""
        self.close()
    
    def add_student(self, enrollment, name):
        """
        Add a new student
        
        Args:
            enrollment (str): Student enrollment ID
            name (str): Student name
            
        Returns:
            bool: True if successful, False if the student already exists
        """
        try:
            # Check if student already exists
            self.cursor.execute(
                'SELECT * FROM students WHERE enrollment = ?',
                (enrollment,)
            )
            if self.cursor.fetchone():
                # Student already exists, update if name is different
                self.cursor.execute(
                    'SELECT name FROM students WHERE enrollment = ?',
                    (enrollment,)
                )
                current_name = self.cursor.fetchone()[0]
                
                if current_name != name:
                    # Update the student's name
                    self.cursor.execute(
                        'UPDATE students SET name = ?, updated_at = CURRENT_TIMESTAMP WHERE enrollment = ?',
                        (name, enrollment)
                    )
                    self.connection.commit()
                    logger.info(f"Updated student: {enrollment} - {name}")
                return True  # Student exists, consider it a success
            
            # Add new student
            self.cursor.execute(
                'INSERT INTO students (enrollment, name) VALUES (?, ?)',
                (enrollment, name)
            )
            self.connection.commit()
            logger.info(f"Added new student: {enrollment} - {name}")
            
            # Import to CSV as well for backwards compatibility
            self._update_student_csv(enrollment, name)
            
            return True
        except sqlite3.Error as e:
            logger.error(f"Error adding student: {e}")
            return False
    
    def _update_student_csv(self, enrollment, name):
        """
        Update the StudentDetails.csv file for backwards compatibility
        
        Args:
            enrollment (str): Student enrollment ID
            name (str): Student name
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs("StudentDetails", exist_ok=True)
            
            csv_path = os.path.join("StudentDetails", "StudentDetails.csv")
            
            # Check if file exists
            file_exists = os.path.isfile(csv_path)
            
            # Read existing data if file exists
            existing_data = []
            if file_exists:
                with open(csv_path, 'r', newline='') as f:
                    reader = csv.reader(f)
                    existing_data = list(reader)
                
                # Check header row
                if not existing_data:
                    existing_data.append(["Enrollment", "Name"])
                elif existing_data[0] != ["Enrollment", "Name"]:
                    # Fix header if it's incorrect
                    existing_data[0] = ["Enrollment", "Name"]
                
                # Check if student already exists
                for i, row in enumerate(existing_data):
                    if i > 0 and len(row) >= 2 and row[0] == enrollment:
                        # Update name if different
                        if row[1] != name:
                            existing_data[i][1] = name
                        # Student found, no need to add
                        break
                else:
                    # Student not found, add them
                    existing_data.append([enrollment, name])
            else:
                # Create new file with header and student
                existing_data = [["Enrollment", "Name"], [enrollment, name]]
            
            # Write back to file
            with open(csv_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerows(existing_data)
                
            logger.info(f"Updated StudentDetails.csv with student: {enrollment} - {name}")
        except Exception as e:
            logger.error(f"Error updating StudentDetails.csv: {e}")
            # Don't raise - this is just for backwards compatibility
    
    def get_student_details(self, enrollment=None):
        """
        Get student details
        
        Args:
            enrollment (str, optional): Student enrollment ID. If None, returns all students
            
        Returns:
            pandas.DataFrame: Student details
        """
        try:
            if enrollment:
                # Get specific student
                self.cursor.execute(
                    'SELECT * FROM students WHERE enrollment = ?',
                    (enrollment,)
                )
            else:
                # Get all students
                self.cursor.execute('SELECT * FROM students')
            
            # Get column names
            columns = [desc[0] for desc in self.cursor.description]
            
            # Fetch all rows
            rows = self.cursor.fetchall()
            
            # Convert to DataFrame
            df = pd.DataFrame([dict(row) for row in rows])
            
            # If DataFrame is empty, return an empty DataFrame with the right columns
            if df.empty:
                return pd.DataFrame(columns=columns)
            
            return df
        except sqlite3.Error as e:
            logger.error(f"Error getting student details: {e}")
            # Return an empty DataFrame
            return pd.DataFrame()
    
    def mark_attendance(self, enrollment, name, subject=None, date=None, time_str=None, file_path=None):
        """
        Mark attendance for a student
        
        Args:
            enrollment (str): Student enrollment ID
            name (str): Student name
            subject (str, optional): Subject name
            date (str, optional): Date string (YYYY-MM-DD). If None, uses current date
            time_str (str, optional): Time string (HH:MM:SS). If None, uses current time
            file_path (str, optional): Path to attendance CSV file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get current date and time if not provided
            now = datetime.datetime.now()
            if not date:
                date = now.strftime("%Y-%m-%d")
            if not time_str:
                time_str = now.strftime("%H:%M:%S")
            
            if not subject:
                subject = "General"
            
            # Generate attendance file path if not provided
            if not file_path:
                time_for_filename = now.strftime("%Y-%m-%d_%H-%M-%S")
                file_name = f"{subject}_{time_for_filename}.csv"
                file_path = os.path.join("Attendance", file_name)
                
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                # Create file with header if it doesn't exist
                if not os.path.exists(file_path):
                    with open(file_path, 'w', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow(["Enrollment", "Name", "Date", "Time"])
            
            # Check if attendance already marked for this student/subject/date
            self.cursor.execute(
                'SELECT * FROM attendance WHERE enrollment = ? AND subject = ? AND date = ?',
                (enrollment, subject, date)
            )
            if self.cursor.fetchone():
                logger.info(f"Attendance already marked for student {name} ({enrollment}) in {subject} on {date}")
                return True  # Already marked, consider it a success
            
            # Mark attendance in database
            self.cursor.execute(
                'INSERT INTO attendance (enrollment, name, subject, date, time, file_path) VALUES (?, ?, ?, ?, ?, ?)',
                (enrollment, name, subject, date, time_str, file_path)
            )
            self.connection.commit()
            
            # Also write to CSV file for backwards compatibility
            with open(file_path, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([enrollment, name, date, time_str])
            
            logger.info(f"Marked attendance for student {name} ({enrollment}) in {subject} on {date}")
            return True
        except (sqlite3.Error, IOError) as e:
            logger.error(f"Error marking attendance: {e}")
            return False
    
    def get_attendance_records(self, subject=None, date=None, enrollment=None):
        """
        Get attendance records
        
        Args:
            subject (str, optional): Filter by subject
            date (str, optional): Filter by date (YYYY-MM-DD)
            enrollment (str, optional): Filter by student enrollment ID
            
        Returns:
            dict: Dictionary of attendance records by file path
        """
        try:
            # Build query based on filters
            query = 'SELECT * FROM attendance'
            params = []
            
            filters = []
            if subject:
                filters.append('subject = ?')
                params.append(subject)
            if date:
                filters.append('date = ?')
                params.append(date)
            if enrollment:
                filters.append('enrollment = ?')
                params.append(enrollment)
                
            if filters:
                query += ' WHERE ' + ' AND '.join(filters)
            
            # Execute query
            self.cursor.execute(query, params)
            
            # Get column names
            columns = [desc[0] for desc in self.cursor.description]
            
            # Fetch all rows
            rows = self.cursor.fetchall()
            
            # Organize records by file path
            attendance_records = {}
            for row in rows:
                row_dict = dict(row)
                file_path = row_dict.get('file_path', 'Unknown')
                
                if file_path not in attendance_records:
                    attendance_records[file_path] = []
                
                attendance_records[file_path].append(row_dict)
            
            # Convert to DataFrames
            for file_path, records in attendance_records.items():
                attendance_records[file_path] = pd.DataFrame(records)
            
            return attendance_records
        except sqlite3.Error as e:
            logger.error(f"Error getting attendance records: {e}")
            return {}
    
    def get_all_attendance_records(self):
        """
        Get all attendance records
        
        Returns:
            dict: Dictionary of attendance records by file path
        """
        return self.get_attendance_records()
    
    def create_attendance_record(self, subject, date, time_str):
        """
        Create a new attendance record file
        
        Args:
            subject (str): Subject name
            date (str): Date string (YYYY-MM-DD)
            time_str (str): Time string (HH:MM:SS)
            
        Returns:
            str: Path to the created file, or None if failed
        """
        try:
            # Generate file path
            file_name = f"{subject}_{date}_{time_str}.csv"
            file_path = os.path.join("Attendance", file_name)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Create file with header
            with open(file_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Enrollment", "Name", "Date", "Time"])
            
            logger.info(f"Created attendance record file: {file_path}")
            return file_path
        except IOError as e:
            logger.error(f"Error creating attendance record file: {e}")
            return None
    
    def add_subject(self, subject_name):
        """
        Add a new subject
        
        Args:
            subject_name (str): Subject name
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if subject already exists
            self.cursor.execute(
                'SELECT * FROM subjects WHERE name = ?',
                (subject_name,)
            )
            if self.cursor.fetchone():
                logger.info(f"Subject already exists: {subject_name}")
                return True  # Already exists, consider it a success
            
            # Add new subject
            self.cursor.execute(
                'INSERT INTO subjects (name) VALUES (?)',
                (subject_name,)
            )
            self.connection.commit()
            logger.info(f"Added new subject: {subject_name}")
            
            # Update subjects.txt for backwards compatibility
            self._update_subjects_file()
            
            return True
        except sqlite3.Error as e:
            logger.error(f"Error adding subject: {e}")
            return False
    
    def _update_subjects_file(self):
        """Update the subjects.txt file for backwards compatibility"""
        try:
            # Get all subjects
            self.cursor.execute('SELECT name FROM subjects ORDER BY name')
            subjects = [row[0] for row in self.cursor.fetchall()]
            
            # Create config directory if it doesn't exist
            os.makedirs("config", exist_ok=True)
            
            # Write to file
            with open(os.path.join("config", "subjects.txt"), 'w') as f:
                for subject in subjects:
                    f.write(f"{subject}\n")
                    
            logger.info("Updated subjects.txt file")
        except (sqlite3.Error, IOError) as e:
            logger.error(f"Error updating subjects.txt file: {e}")
    
    def get_subjects(self):
        """
        Get all subjects
        
        Returns:
            list: List of subject names
        """
        try:
            self.cursor.execute('SELECT name FROM subjects ORDER BY name')
            return [row[0] for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error getting subjects: {e}")
            return []
    
    def remove_subject(self, subject_name):
        """
        Remove a subject
        
        Args:
            subject_name (str): Subject name
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Delete the subject
            self.cursor.execute(
                'DELETE FROM subjects WHERE name = ?',
                (subject_name,)
            )
            self.connection.commit()
            
            # Check if any rows were affected
            if self.cursor.rowcount > 0:
                logger.info(f"Removed subject: {subject_name}")
                
                # Update subjects.txt for backwards compatibility
                self._update_subjects_file()
                
                return True
            else:
                logger.warning(f"Subject not found: {subject_name}")
                return False
        except sqlite3.Error as e:
            logger.error(f"Error removing subject: {e}")
            return False
    
    def backup_database(self, backup_dir="backups/data_backup"):
        """
        Create a backup of the database
        
        Args:
            backup_dir (str): Directory to store backups
            
        Returns:
            str: Path to backup file if successful, None otherwise
        """
        try:
            # Create backup directory if it doesn't exist
            os.makedirs(backup_dir, exist_ok=True)
            
            # Generate backup file name with timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(backup_dir, f"attendance_db_backup_{timestamp}.db")
            
            # Close current connection to ensure all data is written
            if self.connection:
                self.connection.close()
                self.connection = None
                self.cursor = None
            
            # Copy the database file
            shutil.copy2(self.db_path, backup_file)
            
            # Reconnect to database
            self._connect()
            
            logger.info(f"Database backed up to: {backup_file}")
            return backup_file
        except Exception as e:
            logger.error(f"Error backing up database: {e}")
            
            # Ensure connection is reestablished even if backup fails
            if not self.connection:
                self._connect()
                
            return None