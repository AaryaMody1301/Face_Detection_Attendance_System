"""
Database Manager for the Face Detection Attendance System
"""
import os
import sqlite3
import logging
import threading
import time
import datetime
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
from contextlib import contextmanager

from ..utils.app_config import AppConfig
from ..utils.exceptions import DatabaseError

# Configure logging
logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Database manager for SQLite with advanced features
    
    Attributes:
        db_path: Path to the database file
        connection: SQLite connection
        config: Database configuration
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database manager
        
        Args:
            db_path: Path to the database file (optional)
        """
        # Load configuration
        self.config = AppConfig().get_database_config()
        
        # Set database path
        self.db_path = db_path if db_path else self.config.get("path", "Data/attendance.db")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Thread-local storage for connections
        self._local = threading.local()
        
        # Connection mutex
        self._connection_lock = threading.Lock()
        
        # Initialize database schema
        self.initialize_schema()
        
        # Set up periodic optimization if enabled
        optimize_interval = self.config.get("optimize_interval", 24)
        if optimize_interval > 0:
            self._setup_optimization_timer(optimize_interval)
    
    @contextmanager
    def connection(self):
        """
        Get a thread-local database connection
        
        Returns:
            SQLite connection
        """
        if not hasattr(self._local, "connection") or self._local.connection is None:
            with self._connection_lock:
                # Create new connection for this thread
                self._local.connection = sqlite3.connect(self.db_path)
                
                # Enable foreign keys
                self._local.connection.execute("PRAGMA foreign_keys = ON")
                
                # Set busy timeout
                self._local.connection.execute("PRAGMA busy_timeout = 30000")  # 30 seconds
                
                # Row factory
                self._local.connection.row_factory = sqlite3.Row
        
        try:
            # Return thread-local connection
            yield self._local.connection
        except sqlite3.Error as e:
            self._local.connection.rollback()
            logger.error(f"SQLite error: {e}")
            raise DatabaseError(f"Database error: {e}")
    
    def initialize_schema(self):
        """Initialize database schema with required tables"""
        try:
            with self.connection() as conn:
                cursor = conn.cursor()
                
                # Enable foreign keys
                cursor.execute("PRAGMA foreign_keys = ON")
                
                # Students table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS students (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        enrollment TEXT NOT NULL UNIQUE,
                        name TEXT NOT NULL,
                        email TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Subjects table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS subjects (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL UNIQUE,
                        code TEXT,
                        description TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Attendance sessions table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS attendance_sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        subject_id INTEGER NOT NULL,
                        date TEXT NOT NULL,
                        time TEXT NOT NULL,
                        notes TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (subject_id) REFERENCES subjects (id)
                    )
                ''')
                
                # Attendance records table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS attendance_records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        student_id INTEGER NOT NULL,
                        session_id INTEGER NOT NULL,
                        time TEXT NOT NULL,
                        confidence REAL NOT NULL DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (student_id) REFERENCES students (id),
                        FOREIGN KEY (session_id) REFERENCES attendance_sessions (id),
                        UNIQUE(student_id, session_id)
                    )
                ''')
                
                # Users table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL UNIQUE,
                        password_hash TEXT NOT NULL,
                        full_name TEXT,
                        email TEXT,
                        role TEXT NOT NULL DEFAULT 'user',
                        is_active BOOLEAN NOT NULL DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create indexes for better performance
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_students_enrollment ON students(enrollment)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_subjects_name ON subjects(name)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_date ON attendance_sessions(date)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_subject ON attendance_sessions(subject_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_attendance_student ON attendance_records(student_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_attendance_session ON attendance_records(session_id)')
                
                # Insert default data if needed
                self._insert_default_data(cursor)
                
                # Commit changes
                conn.commit()
                
                logger.info("Database schema initialized successfully")
                
        except Exception as e:
            logger.error(f"Error initializing database schema: {e}")
            raise DatabaseError(f"Failed to initialize database schema: {e}")
    
    def _insert_default_data(self, cursor):
        """
        Insert default data into the database
        
        Args:
            cursor: SQLite cursor
        """
        # Check if default admin user exists
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
        if cursor.fetchone()[0] == 0:
            # Create default admin user with password 'admin'
            # Note: In production, this should be a secure password hash
            cursor.execute('''
                INSERT INTO users (username, password_hash, full_name, role)
                VALUES ('admin', 'admin', 'Administrator', 'admin')
            ''')
            logger.info("Created default admin user")
        
        # Insert some default subjects if none exist
        cursor.execute("SELECT COUNT(*) FROM subjects")
        if cursor.fetchone()[0] == 0:
            subjects = [
                ('Python', 'PY101', 'Introduction to Python Programming'),
                ('Maths', 'MT101', 'Basic Mathematics'),
                ('Physics', 'PH101', 'Introduction to Physics'),
                ('Chemistry', 'CH101', 'Basic Chemistry'),
                ('Biology', 'BI101', 'Introduction to Biology')
            ]
            
            cursor.executemany('''
                INSERT INTO subjects (name, code, description)
                VALUES (?, ?, ?)
            ''', subjects)
            
            logger.info("Inserted default subjects")
    
    def _setup_optimization_timer(self, hours):
        """
        Set up periodic database optimization
        
        Args:
            hours: Interval in hours
        """
        def optimize_task():
            self.optimize_database()
            # Schedule next run
            threading.Timer(hours * 3600, optimize_task).start()
        
        # Start the timer
        threading.Timer(hours * 3600, optimize_task).start()
        logger.info(f"Database optimization scheduled every {hours} hours")
    
    def optimize_database(self):
        """Optimize the database"""
        try:
            # Create backup before optimization
            self.create_backup()
            
            with self.connection() as conn:
                cursor = conn.cursor()
                
                # Run VACUUM to rebuild the database file
                cursor.execute("VACUUM")
                
                # Run ANALYZE to collect statistics
                cursor.execute("ANALYZE")
                
                logger.info("Database optimized successfully")
                return True
                
        except Exception as e:
            logger.error(f"Error optimizing database: {e}")
            return False
    
    def create_backup(self):
        """Create a backup of the database"""
        try:
            # Get backup directory from config
            backup_dir = self.config.get("backup_dir", "backups/data_backup")
            
            # Ensure directory exists
            os.makedirs(backup_dir, exist_ok=True)
            
            # Create backup filename with timestamp
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            backup_path = os.path.join(backup_dir, f"db_backup_{timestamp}.db")
            
            # Close all connections
            self.close_all_connections()
            
            # Copy database file
            shutil.copy2(self.db_path, backup_path)
            
            logger.info(f"Database backup created at {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"Error creating database backup: {e}")
            return None
    
    def close_all_connections(self):
        """Close all database connections"""
        # Close the thread-local connection if it exists
        if hasattr(self._local, "connection") and self._local.connection is not None:
            try:
                self._local.connection.close()
                self._local.connection = None
            except Exception as e:
                logger.error(f"Error closing database connection: {e}")
    
    def execute_query(self, query, params=None, fetch_all=False, fetch_one=False):
        """
        Execute a SQL query
        
        Args:
            query: SQL query
            params: Query parameters
            fetch_all: Whether to return all results
            fetch_one: Whether to return one result
            
        Returns:
            Query results or row count
        """
        params = params or []
        
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            if fetch_all:
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
            elif fetch_one:
                row = cursor.fetchone()
                return dict(row) if row else None
            else:
                # For INSERT, UPDATE, DELETE, return number of affected rows
                conn.commit()
                return cursor.rowcount
    
    def execute_batch(self, query, params_list):
        """
        Execute a batch of SQL queries
        
        Args:
            query: SQL query with placeholders
            params_list: List of parameter tuples
            
        Returns:
            Number of affected rows
        """
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            conn.commit()
            return cursor.rowcount
    
    def begin_transaction(self):
        """Begin a transaction"""
        if not hasattr(self._local, "connection") or self._local.connection is None:
            with self._connection_lock:
                # Create new connection for this thread
                self._local.connection = sqlite3.connect(self.db_path)
                
                # Enable foreign keys
                self._local.connection.execute("PRAGMA foreign_keys = ON")
                
                # Set busy timeout
                self._local.connection.execute("PRAGMA busy_timeout = 30000")  # 30 seconds
                
                # Row factory
                self._local.connection.row_factory = sqlite3.Row
        
        # Begin transaction
        self._local.connection.execute("BEGIN TRANSACTION")
    
    def commit_transaction(self):
        """Commit the current transaction"""
        if hasattr(self._local, "connection") and self._local.connection is not None:
            self._local.connection.commit()
    
    def rollback_transaction(self):
        """Rollback the current transaction"""
        if hasattr(self._local, "connection") and self._local.connection is not None:
            self._local.connection.rollback()
    
    def get_student_by_enrollment(self, enrollment):
        """
        Get a student by enrollment ID
        
        Args:
            enrollment: Student enrollment ID
            
        Returns:
            Student data or None if not found
        """
        query = "SELECT * FROM students WHERE enrollment = ?"
        return self.execute_query(query, (enrollment,), fetch_one=True)
    
    def get_subject_by_name(self, subject_name):
        """
        Get a subject by name
        
        Args:
            subject_name: Subject name
            
        Returns:
            Subject data or None if not found
        """
        query = "SELECT * FROM subjects WHERE name = ?"
        return self.execute_query(query, (subject_name,), fetch_one=True)
    
    def create_or_get_subject(self, subject_name):
        """
        Get a subject by name or create it if not exists
        
        Args:
            subject_name: Subject name
            
        Returns:
            Subject ID
        """
        subject = self.get_subject_by_name(subject_name)
        if subject:
            return subject["id"]
        
        # Create new subject
        query = "INSERT INTO subjects (name) VALUES (?)"
        self.execute_query(query, (subject_name,))
        
        # Get the newly created subject
        subject = self.get_subject_by_name(subject_name)
        return subject["id"]
    
    def create_or_get_student(self, enrollment, name):
        """
        Get a student by enrollment or create if not exists
        
        Args:
            enrollment: Student enrollment ID
            name: Student name
            
        Returns:
            Student ID
        """
        student = self.get_student_by_enrollment(enrollment)
        if student:
            return student["id"]
        
        # Create new student
        query = "INSERT INTO students (enrollment, name) VALUES (?, ?)"
        self.execute_query(query, (enrollment, name))
        
        # Get the newly created student
        student = self.get_student_by_enrollment(enrollment)
        return student["id"]
    
    def create_attendance_session(self, subject_name, date=None, time=None, notes=None):
        """
        Create a new attendance session
        
        Args:
            subject_name: Subject name
            date: Date string (YYYY-MM-DD)
            time: Time string (HH:MM:SS)
            notes: Optional notes
            
        Returns:
            Session ID
        """
        # Use current date/time if not provided
        if date is None:
            date = datetime.datetime.now().strftime("%Y-%m-%d")
        
        if time is None:
            time = datetime.datetime.now().strftime("%H:%M:%S")
        
        # Get or create subject
        subject_id = self.create_or_get_subject(subject_name)
        
        # Create session
        query = """
            INSERT INTO attendance_sessions (subject_id, date, time, notes)
            VALUES (?, ?, ?, ?)
        """
        self.execute_query(query, (subject_id, date, time, notes))
        
        # Get the newly created session
        query = """
            SELECT id FROM attendance_sessions 
            WHERE subject_id = ? AND date = ? AND time = ? 
            ORDER BY id DESC LIMIT 1
        """
        session = self.execute_query(query, (subject_id, date, time), fetch_one=True)
        
        return session["id"]
    
    def mark_attendance(self, enrollment, name, subject_name, date=None, time=None, confidence=1.0):
        """
        Mark attendance for a student
        
        Args:
            enrollment: Student enrollment ID
            name: Student name
            subject_name: Subject name
            date: Date string (YYYY-MM-DD)
            time: Time string (HH:MM:SS)
            confidence: Recognition confidence
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Use current date/time if not provided
            if date is None:
                date = datetime.datetime.now().strftime("%Y-%m-%d")
            
            if time is None:
                time = datetime.datetime.now().strftime("%H:%M:%S")
            
            # Start transaction
            self.begin_transaction()
            
            # Get or create student
            student_id = self.create_or_get_student(enrollment, name)
            
            # Get or create subject
            subject_id = self.create_or_get_subject(subject_name)
            
            # Get existing session or create new one
            query = """
                SELECT id FROM attendance_sessions 
                WHERE subject_id = ? AND date = ? 
                ORDER BY id DESC LIMIT 1
            """
            session = self.execute_query(query, (subject_id, date), fetch_one=True)
            
            if session:
                session_id = session["id"]
            else:
                # Create new session
                session_id = self.create_attendance_session(subject_name, date, time)
            
            # Check if attendance already exists
            query = """
                SELECT id FROM attendance_records 
                WHERE student_id = ? AND session_id = ?
            """
            existing = self.execute_query(query, (student_id, session_id), fetch_one=True)
            
            if existing:
                # Update existing record
                query = """
                    UPDATE attendance_records 
                    SET time = ?, confidence = ?, created_at = CURRENT_TIMESTAMP 
                    WHERE id = ?
                """
                self.execute_query(query, (time, confidence, existing["id"]))
            else:
                # Create new record
                query = """
                    INSERT INTO attendance_records (student_id, session_id, time, confidence)
                    VALUES (?, ?, ?, ?)
                """
                self.execute_query(query, (student_id, session_id, time, confidence))
            
            # Commit transaction
            self.commit_transaction()
            
            return True
            
        except Exception as e:
            # Rollback transaction on error
            self.rollback_transaction()
            logger.error(f"Error marking attendance: {e}")
            return False
    
    def get_attendance_records(self, subject_name=None, date=None, student_enrollment=None):
        """
        Get attendance records
        
        Args:
            subject_name: Filter by subject name
            date: Filter by date
            student_enrollment: Filter by student enrollment ID
            
        Returns:
            List of attendance records
        """
        query = """
            SELECT 
                ar.id, 
                s.enrollment, 
                s.name, 
                sub.name as subject, 
                sess.date, 
                ar.time, 
                ar.confidence 
            FROM attendance_records ar
            JOIN students s ON ar.student_id = s.id
            JOIN attendance_sessions sess ON ar.session_id = sess.id
            JOIN subjects sub ON sess.subject_id = sub.id
            WHERE 1=1
        """
        params = []
        
        if subject_name:
            query += " AND sub.name = ?"
            params.append(subject_name)
        
        if date:
            query += " AND sess.date = ?"
            params.append(date)
        
        if student_enrollment:
            query += " AND s.enrollment = ?"
            params.append(student_enrollment)
        
        query += " ORDER BY sess.date DESC, ar.time DESC"
        
        return self.execute_query(query, params, fetch_all=True)
    
    def get_attendance_statistics(self, subject_name=None, start_date=None, end_date=None):
        """
        Get attendance statistics
        
        Args:
            subject_name: Filter by subject name
            start_date: Start date filter
            end_date: End date filter
            
        Returns:
            Dictionary with statistics
        """
        # Build base query for total attendance
        query = """
            SELECT COUNT(*) as total_attendance
            FROM attendance_records ar
            JOIN attendance_sessions sess ON ar.session_id = sess.id
            JOIN subjects sub ON sess.subject_id = sub.id
            WHERE 1=1
        """
        params = []
        
        if subject_name:
            query += " AND sub.name = ?"
            params.append(subject_name)
        
        if start_date:
            query += " AND sess.date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND sess.date <= ?"
            params.append(end_date)
        
        # Get total attendance
        result = self.execute_query(query, params, fetch_one=True)
        total_attendance = result["total_attendance"] if result else 0
        
        # Build query for unique students
        query = """
            SELECT COUNT(DISTINCT ar.student_id) as unique_students
            FROM attendance_records ar
            JOIN attendance_sessions sess ON ar.session_id = sess.id
            JOIN subjects sub ON sess.subject_id = sub.id
            WHERE 1=1
        """
        params = []
        
        if subject_name:
            query += " AND sub.name = ?"
            params.append(subject_name)
        
        if start_date:
            query += " AND sess.date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND sess.date <= ?"
            params.append(end_date)
        
        # Get unique students
        result = self.execute_query(query, params, fetch_one=True)
        unique_students = result["unique_students"] if result else 0
        
        # Build query for attendance by date
        query = """
            SELECT sess.date, COUNT(*) as count
            FROM attendance_records ar
            JOIN attendance_sessions sess ON ar.session_id = sess.id
            JOIN subjects sub ON sess.subject_id = sub.id
            WHERE 1=1
        """
        params = []
        
        if subject_name:
            query += " AND sub.name = ?"
            params.append(subject_name)
        
        if start_date:
            query += " AND sess.date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND sess.date <= ?"
            params.append(end_date)
        
        query += " GROUP BY sess.date ORDER BY sess.date DESC"
        
        # Get attendance by date
        result = self.execute_query(query, params, fetch_all=True)
        attendance_by_date = {r["date"]: r["count"] for r in result} if result else {}
        
        # Build query for top subjects
        top_subjects = {}
        if not subject_name:
            query = """
                SELECT sub.name, COUNT(*) as count
                FROM attendance_records ar
                JOIN attendance_sessions sess ON ar.session_id = sess.id
                JOIN subjects sub ON sess.subject_id = sub.id
                WHERE 1=1
            """
            params = []
            
            if start_date:
                query += " AND sess.date >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND sess.date <= ?"
                params.append(end_date)
            
            query += " GROUP BY sub.name ORDER BY count DESC LIMIT 5"
            
            # Get top subjects
            result = self.execute_query(query, params, fetch_all=True)
            top_subjects = {r["name"]: r["count"] for r in result} if result else {}
        
        # Return combined statistics
        return {
            "total_attendance": total_attendance,
            "unique_students": unique_students,
            "attendance_by_date": attendance_by_date,
            "top_subjects": top_subjects
        }