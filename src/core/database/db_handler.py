"""
Unified Database Handler for Face Detection Attendance System
This module provides a single database interface to be used by both UI implementations.
"""
import os
import sqlite3
import pandas as pd
import csv
import datetime
import logging
from pathlib import Path

# Set up logger
logger = logging.getLogger(__name__)

class DatabaseHandler:
    """
    Handles all database operations for the Face Detection Attendance System
    using SQLite
    """
    
    def __init__(self, db_path=None):
        """
        Initialize the database handler
        
        Args:
            db_path (str, optional): Path to the SQLite database file
        """
        # Use provided path or default
        if db_path is None:
            db_path = os.path.join("Data", "attendance.db")
            
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        
        # Initialize database connection
        self._initialize_db()
    
    def _initialize_db(self):
        """Initialize database connection and create tables if they don't exist"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            
            # Create students table if it doesn't exist
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS students (
                    id INTEGER PRIMARY KEY,
                    enrollment TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create attendance table if it doesn't exist with consistent field names
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS attendance (
                    id INTEGER PRIMARY KEY,
                    student_id INTEGER,
                    subject TEXT NOT NULL,
                    date TEXT NOT NULL,
                    time TEXT NOT NULL,
                    FOREIGN KEY (student_id) REFERENCES students(id)
                )
            ''')
            
            # Check if we need to update the attendance table structure
            try:
                # Check if student_id column exists
                self.cursor.execute("SELECT student_id FROM attendance LIMIT 1")
            except sqlite3.OperationalError:
                # Column doesn't exist, need to recreate the table with proper structure
                logger.info("Updating attendance table structure...")
                
                # Get existing data
                try:
                    self.cursor.execute("SELECT * FROM attendance")
                    old_data = self.cursor.fetchall()
                except:
                    old_data = []
                
                # Drop old table
                self.cursor.execute("DROP TABLE IF EXISTS attendance")
                
                # Create new table with correct structure
                self.cursor.execute('''
                    CREATE TABLE attendance (
                        id INTEGER PRIMARY KEY,
                        student_id INTEGER,
                        subject TEXT NOT NULL,
                        date TEXT NOT NULL,
                        time TEXT NOT NULL,
                        FOREIGN KEY (student_id) REFERENCES students(id)
                    )
                ''')
                
                # If there was existing data, try to migrate it
                if old_data and len(old_data) > 0:
                    logger.info(f"Migrating {len(old_data)} attendance records...")
                    # Get column names from the first row's keys
                    old_column_names = [description[0] for description in self.cursor.description]
                    
                    # Check if we need to handle a different column name for student_id
                    student_id_index = None
                    for i, col_name in enumerate(old_column_names):
                        if col_name.lower() in ('student_id', 'studentid', 'student'):
                            student_id_index = i
                            break
                    
                    # Transfer data
                    if student_id_index is not None:
                        for row in old_data:
                            try:
                                self.cursor.execute(
                                    "INSERT INTO attendance (student_id, subject, date, time) VALUES (?, ?, ?, ?)",
                                    (row[student_id_index], row[old_column_names.index('subject')], 
                                     row[old_column_names.index('date')], row[old_column_names.index('time')])
                                )
                            except Exception as e:
                                logger.error(f"Error migrating attendance record: {e}")
                    
                logger.info("Attendance table structure updated successfully")
            
            # Create subjects table if it doesn't exist
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS subjects (
                    id INTEGER PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Commit changes
            self.conn.commit()
            
            # Import existing CSV data if tables are empty
            self._import_existing_data()
            
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}")
            raise
    
    def _import_existing_data(self):
        """Import existing data from CSV files if available"""
        # Check if students table is empty
        self.cursor.execute("SELECT COUNT(*) FROM students")
        if self.cursor.fetchone()[0] == 0:
            # Try to import from StudentDetails.csv if it exists
            student_csv = os.path.join("StudentDetails", "StudentDetails.csv")
            if os.path.isfile(student_csv):
                try:
                    df = pd.read_csv(student_csv)
                    for _, row in df.iterrows():
                        try:
                            enrollment = str(row.get('Enrollment', row.get('enrollment', '')))
                            name = str(row.get('Name', row.get('name', '')))
                            if enrollment and name:
                                self.add_student(enrollment, name)
                        except Exception as e:
                            logger.warning(f"Error importing student record: {e}")
                except Exception as e:
                    logger.warning(f"Error importing student data: {e}")
        
        # Import attendance records if attendance table is empty
        self.cursor.execute("SELECT COUNT(*) FROM attendance")
        if self.cursor.fetchone()[0] == 0:
            # Try to import from Attendance/*.csv
            attendance_dir = "Attendance"
            if os.path.isdir(attendance_dir):
                csv_files = [f for f in os.listdir(attendance_dir) 
                           if os.path.isfile(os.path.join(attendance_dir, f)) and
                           f.lower().endswith('.csv')]
                
                for csv_file in csv_files:
                    try:
                        # Extract subject from filename
                        file_parts = os.path.splitext(csv_file)[0].split('_')
                        subject = file_parts[0]
                        
                        # Read the CSV
                        df = pd.read_csv(os.path.join(attendance_dir, csv_file))
                        for _, row in df.iterrows():
                            try:
                                enrollment = str(row.get('Enrollment', row.get('enrollment', '')))
                                name = str(row.get('Name', row.get('name', '')))
                                date = str(row.get('Date', row.get('date', '')))
                                time = str(row.get('Time', row.get('time', '')))
                                
                                if enrollment and name and date and time:
                                    self.mark_attendance(enrollment, name, subject, date, time)
                            except Exception as e:
                                logger.warning(f"Error importing attendance record: {e}")
                    except Exception as e:
                        logger.warning(f"Error importing attendance file {csv_file}: {e}")
    
    def close(self):
        """Close the database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None
    
    def add_student(self, enrollment, name):
        """
        Add a student to the database
        
        Args:
            enrollment (str): Student enrollment/ID
            name (str): Student name
            
        Returns:
            bool: Success or failure
        """
        try:
            # Check if student already exists
            self.cursor.execute(
                "SELECT id FROM students WHERE enrollment = ?", 
                (enrollment,)
            )
            if self.cursor.fetchone():
                # Student already exists
                return False
                
            # Add student
            self.cursor.execute(
                "INSERT INTO students (enrollment, name) VALUES (?, ?)",
                (enrollment, name)
            )
            self.conn.commit()
            
            # Also add to StudentDetails.csv for backward compatibility
            self._update_student_csv(enrollment, name)
            
            return True
        except sqlite3.Error as e:
            logger.error(f"Error adding student: {e}")
            return False
    
    def _update_student_csv(self, enrollment, name):
        """Update StudentDetails.csv for backward compatibility"""
        try:
            # Ensure directory exists
            os.makedirs("StudentDetails", exist_ok=True)
            
            csv_file = os.path.join("StudentDetails", "StudentDetails.csv")
            file_exists = os.path.isfile(csv_file)
            
            # Append to CSV file
            with open(csv_file, 'a+', newline='') as f:
                writer = csv.writer(f)
                
                # Write header if file is new
                if not file_exists:
                    writer.writerow(['Enrollment', 'Name'])
                    
                # Write student data
                writer.writerow([enrollment, name])
                
        except Exception as e:
            logger.error(f"Error updating StudentDetails.csv: {e}")
    
    def get_student_details(self):
        """
        Get all student details
        
        Returns:
            pandas.DataFrame: DataFrame with student details
        """
        try:
            query = "SELECT enrollment as Enrollment, name as Name FROM students"
            return pd.read_sql_query(query, self.conn)
        except sqlite3.Error as e:
            logger.error(f"Error getting student details: {e}")
            return pd.DataFrame(columns=['Enrollment', 'Name'])
    
    def mark_attendance(self, enrollment, name, subject=None, date=None, time=None, file_path=None):
        """
        Mark attendance for a student
        
        Args:
            enrollment (str): Student enrollment/ID
            name (str): Student name
            subject (str, optional): Subject name
            date (str, optional): Date in YYYY-MM-DD format
            time (str, optional): Time in HH:MM:SS format
            file_path (str, optional): Path to CSV file for backward compatibility
            
        Returns:
            bool: Success or failure
        """
        try:
            # Use current date/time if not provided
            if not date:
                date = datetime.datetime.now().strftime("%Y-%m-%d")
            if not time:
                time = datetime.datetime.now().strftime("%H:%M:%S")
            
            # Get or create subject
            if not subject and file_path:
                # Try to extract subject from file path
                file_name = os.path.basename(file_path)
                subject = file_name.split('_')[0]
            
            if not subject:
                subject = "General"
            
            # Get student ID
            self.cursor.execute(
                "SELECT id FROM students WHERE enrollment = ?",
                (enrollment,)
            )
            result = self.cursor.fetchone()
            
            student_id = None
            if result:
                student_id = result[0]
            else:
                # Add student if not exists
                self.add_student(enrollment, name)
                
                # Get the new student ID
                self.cursor.execute(
                    "SELECT id FROM students WHERE enrollment = ?",
                    (enrollment,)
                )
                result = self.cursor.fetchone()
                if result:
                    student_id = result[0]
            
            if student_id is None:
                logger.error(f"Could not get or create student ID for {enrollment}")
                return False
            
            # Check if attendance already marked for this student/subject/date
            self.cursor.execute(
                "SELECT id FROM attendance WHERE student_id = ? AND subject = ? AND date = ?",
                (student_id, subject, date)
            )
            if self.cursor.fetchone():
                # Already marked
                logger.info(f"Attendance already marked for {name} ({enrollment}) in {subject} on {date}")
                return True
            
            # Mark attendance in database
            self.cursor.execute(
                "INSERT INTO attendance (student_id, subject, date, time) VALUES (?, ?, ?, ?)",
                (student_id, subject, date, time)
            )
            self.conn.commit()
            
            # Also update CSV for backward compatibility
            self._update_attendance_csv(enrollment, name, subject, date, time, file_path)
            
            return True
        except sqlite3.Error as e:
            logger.error(f"Error marking attendance: {e}")
            return False
    
    def _update_attendance_csv(self, enrollment, name, subject, date, time, file_path=None):
        """Update attendance CSV file for backward compatibility"""
        try:
            # Ensure directory exists
            os.makedirs("Attendance", exist_ok=True)
            
            # Determine file path if not provided
            if not file_path:
                # Format: Subject_YYYY-MM-DD_HH-MM-SS.csv
                now = datetime.datetime.now()
                date_str = now.strftime("%Y-%m-%d")
                time_str = now.strftime("%H-%M-%S")
                file_name = f"{subject}_{date_str}_{time_str}.csv"
                file_path = os.path.join("Attendance", file_name)
            
            file_exists = os.path.isfile(file_path)
            
            # Append to CSV file
            with open(file_path, 'a+', newline='') as f:
                writer = csv.writer(f)
                
                # Write header if file is new
                if not file_exists:
                    writer.writerow(['Enrollment', 'Name', 'Date', 'Time'])
                    
                # Write attendance data
                writer.writerow([enrollment, name, date, time])
                
            return file_path
                
        except Exception as e:
            logger.error(f"Error updating attendance CSV: {e}")
            return None
    
    def create_attendance_record(self, subject, date, time):
        """
        Create a new attendance record file
        
        Args:
            subject (str): Subject name
            date (str): Date string
            time (str): Time string
            
        Returns:
            str: Path to the created file or None on failure
        """
        try:
            # Create file name
            file_name = f"{subject}_{date}_{time}.csv"
            file_path = os.path.join("Attendance", file_name)
            
            # Ensure directory exists
            os.makedirs("Attendance", exist_ok=True)
            
            # Create file with header
            with open(file_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Enrollment', 'Name', 'Date', 'Time'])
            
            return file_path
        except Exception as e:
            logger.error(f"Error creating attendance record: {e}")
            return None
    
    def get_attendance_records(self, subject=None, start_date=None, end_date=None, student_id=None):
        """
        Get attendance records with optional filters
        
        Args:
            subject (str, optional): Filter by subject
            start_date (str, optional): Filter by start date (inclusive)
            end_date (str, optional): Filter by end date (inclusive)
            student_id (str, optional): Filter by student enrollment ID
            
        Returns:
            pandas.DataFrame: DataFrame with attendance records
        """
        try:
            # Build query
            query = """
                SELECT 
                    a.id, s.enrollment as Enrollment, s.name as Name, 
                    a.subject as Subject, a.date as Date, a.time as Time
                FROM 
                    attendance a
                JOIN 
                    students s ON a.student_id = s.id
                WHERE 1=1
            """
            params = []
            
            if subject:
                query += " AND a.subject = ?"
                params.append(subject)
                
            if start_date:
                query += " AND a.date >= ?"
                params.append(start_date)
                
            if end_date:
                query += " AND a.date <= ?"
                params.append(end_date)
                
            if student_id:
                query += " AND s.enrollment = ?"
                params.append(student_id)
                
            # Add order by
            query += " ORDER BY a.date DESC, a.time DESC"
            
            # Get records as a DataFrame directly
            df = pd.read_sql_query(query, self.conn, params=params)
            return df
            
        except sqlite3.Error as e:
            logger.error(f"Error getting attendance records: {e}")
            return pd.DataFrame()
    
    def get_all_attendance_records(self):
        """
        Get all attendance records
        
        Returns:
            pandas.DataFrame: DataFrame with all attendance records
        """
        return self.get_attendance_records()
    
    def add_subject(self, name):
        """
        Add a subject to the database
        
        Args:
            name (str): Subject name
            
        Returns:
            bool: Success or failure
        """
        try:
            # Check if subject already exists
            self.cursor.execute(
                "SELECT id FROM subjects WHERE name = ?", 
                (name,)
            )
            if self.cursor.fetchone():
                # Subject already exists
                return False
                
            # Add subject
            self.cursor.execute(
                "INSERT INTO subjects (name) VALUES (?)",
                (name,)
            )
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error adding subject: {e}")
            return False
    
    def get_subjects(self):
        """
        Get list of all subjects
        
        Returns:
            list: List of subject names
        """
        try:
            self.cursor.execute("SELECT name FROM subjects ORDER BY name")
            return [row[0] for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error getting subjects: {e}")
            return []
    
    def remove_subject(self, name):
        """
        Remove a subject from the database
        
        Args:
            name (str): Subject name
            
        Returns:
            bool: Success or failure
        """
        try:
            # Delete subject
            self.cursor.execute("DELETE FROM subjects WHERE name = ?", (name,))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error removing subject: {e}")
            return False
    
    def backup_database(self, backup_dir=None):
        """
        Create a backup of the database
        
        Args:
            backup_dir (str, optional): Directory to store the backup
            
        Returns:
            str: Path to the backup file or None on failure
        """
        try:
            # Use default backup directory if not provided
            if backup_dir is None:
                backup_dir = os.path.join("backups", "database")
            
            # Ensure directory exists
            os.makedirs(backup_dir, exist_ok=True)
            
            # Create backup file name with timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(backup_dir, f"attendance_backup_{timestamp}.db")
            
            # Close current connection
            self.conn.close()
            
            # Copy the database file
            import shutil
            shutil.copy2(self.db_path, backup_file)
            
            # Reopen the connection
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            
            return backup_file
        except Exception as e:
            logger.error(f"Error backing up database: {e}")
            
            # Try to reopen the connection if it was closed
            if not self.conn:
                self.conn = sqlite3.connect(self.db_path)
                self.cursor = self.conn.cursor()
                
            return None