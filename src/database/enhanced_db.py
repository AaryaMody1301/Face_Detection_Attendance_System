"""
Enhanced database handler with connection pooling and optimized queries
"""
import os
import sqlite3
import logging
import threading
import time
import datetime
from typing import Dict, List, Any, Optional, Tuple
from queue import Queue, Empty

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedDB:
    """
    Enhanced database handler with connection pooling and optimized queries
    """
    
    def __init__(self, db_path=None, pool_size=5):
        """
        Initialize the database handler with connection pooling
        
        Args:
            db_path (str, optional): Path to the database file
            pool_size (int): Size of the connection pool
        """
        if db_path is None:
            db_path = os.path.join("Data", "attendance.db")
        
        self.db_path = db_path
        self.pool_size = pool_size
        
        # Connection pool
        self.connection_pool = Queue(maxsize=pool_size)
        self.active_connections = 0
        self.pool_lock = threading.Lock()
        
        # Connection management
        self.initialize_db()
        self.fill_pool()
        
        # Query cache
        self.query_cache = {}
        self.cache_lock = threading.Lock()
        self.cache_expiry = {}
        self.cache_ttl = 60  # 1 minute in seconds
    
    def initialize_db(self):
        """Initialize the database with required tables if they don't exist"""
        try:
            # Create Data directory if it doesn't exist
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            # Connect to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create students table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    enrollment TEXT UNIQUE,
                    name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create attendance table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    enrollment TEXT,
                    name TEXT,
                    subject TEXT,
                    date TEXT,
                    time TEXT,
                    confidence REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(enrollment, subject, date) ON CONFLICT REPLACE
                )
            ''')
            
            # Create attendance_sessions table for tracking sessions
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS AttendanceSessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject TEXT,
                    date TEXT,
                    time TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create index for faster queries
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_attendance_date ON Attendance(date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_attendance_subject ON Attendance(subject)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_attendance_enrollment ON Attendance(enrollment)')
            
            conn.commit()
            conn.close()
            
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
    
    def fill_pool(self):
        """Fill the connection pool with database connections"""
        with self.pool_lock:
            while not self.connection_pool.full() and self.active_connections < self.pool_size:
                try:
                    # Create a new connection
                    conn = sqlite3.connect(self.db_path, check_same_thread=False)
                    
                    # Enable foreign keys
                    cursor = conn.cursor()
                    cursor.execute('PRAGMA foreign_keys = ON')
                    conn.commit()
                    
                    # Add to pool
                    self.connection_pool.put(conn)
                    self.active_connections += 1
                    
                except Exception as e:
                    logger.error(f"Error creating database connection: {e}")
                    break
    
    def get_connection(self):
        """
        Get a connection from the pool
        
        Returns:
            sqlite3.Connection: Database connection
        """
        try:
            # Try to get connection from pool
            conn = self.connection_pool.get(block=True, timeout=5)
            return conn
        except Empty:
            # Create a new connection if pool is empty
            with self.pool_lock:
                if self.active_connections < self.pool_size:
                    try:
                        # Create a new connection
                        conn = sqlite3.connect(self.db_path, check_same_thread=False)
                        
                        # Enable foreign keys
                        cursor = conn.cursor()
                        cursor.execute('PRAGMA foreign_keys = ON')
                        conn.commit()
                        
                        self.active_connections += 1
                        return conn
                    except Exception as e:
                        logger.error(f"Error creating database connection: {e}")
                        raise
                else:
                    # Wait for a connection
                    conn = self.connection_pool.get(block=True)
                    return conn
    
    def release_connection(self, conn):
        """
        Release a connection back to the pool
        
        Args:
            conn (sqlite3.Connection): Database connection
        """
        try:
            # Return connection to pool
            self.connection_pool.put(conn, block=False)
        except:
            # Close connection if pool is full
            conn.close()
            with self.pool_lock:
                self.active_connections -= 1
    
    def execute_query(self, query, params=(), fetch_all=False, fetch_one=False, commit=False):
        """
        Execute a database query with connection pooling
        
        Args:
            query (str): SQL query
            params (tuple): Query parameters
            fetch_all (bool): Whether to return all results
            fetch_one (bool): Whether to return one result
            commit (bool): Whether to commit the transaction
            
        Returns:
            Any: Query results if fetch_all or fetch_one, else None
        """
        conn = None
        try:
            # Get a connection from the pool
            conn = self.get_connection()
            
            # Execute query
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            # Get results
            result = None
            if fetch_all:
                result = cursor.fetchall()
            elif fetch_one:
                result = cursor.fetchone()
            
            # Commit if needed
            if commit:
                conn.commit()
            
            return result
            
        except Exception as e:
            logger.error(f"Database error: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            # Return connection to pool
            if conn:
                self.release_connection(conn)
    
    def create_attendance_record(self, subject, date, time):
        """
        Create a new attendance session record
        
        Args:
            subject (str): Subject name
            date (str): Date in YYYY-MM-DD format
            time (str): Time in HH:MM:SS format
            
        Returns:
            int: Session ID or None on failure
        """
        try:
            # Insert record
            query = '''
                INSERT INTO AttendanceSessions (subject, date, time)
                VALUES (?, ?, ?)
            '''
            
            # Execute query
            self.execute_query(query, (subject, date, time), commit=True)
            
            # Get session ID
            query = '''
                SELECT id FROM AttendanceSessions
                WHERE subject = ? AND date = ? AND time = ?
                ORDER BY id DESC LIMIT 1
            '''
            
            # Execute query
            result = self.execute_query(query, (subject, date, time), fetch_one=True)
            
            if result:
                return result[0]
            return None
        
        except Exception as e:
            logger.error(f"Error creating attendance record: {e}")
            return None
    
    def mark_attendance(self, enrollment, name, subject, date, time, confidence=1.0):
        """
        Mark attendance for a student
        
        Args:
            enrollment (str): Student enrollment ID
            name (str): Student name
            subject (str): Subject name
            date (str): Date in YYYY-MM-DD format
            time (str): Time in HH:MM:SS format
            confidence (float): Recognition confidence score
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Ensure student exists in Students table
            query = '''
                INSERT OR IGNORE INTO Students (enrollment, name)
                VALUES (?, ?)
            '''
            
            # Execute query
            self.execute_query(query, (enrollment, name), commit=True)
            
            # Insert attendance record
            query = '''
                INSERT OR REPLACE INTO Attendance 
                (enrollment, name, subject, date, time, confidence)
                VALUES (?, ?, ?, ?, ?, ?)
            '''
            
            # Execute query
            self.execute_query(
                query, 
                (enrollment, name, subject, date, time, confidence),
                commit=True
            )
            
            # Clear cache for attendance queries
            with self.cache_lock:
                keys_to_remove = []
                for key in self.query_cache:
                    if 'attendance' in key.lower():
                        keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    del self.query_cache[key]
                    if key in self.cache_expiry:
                        del self.cache_expiry[key]
            
            return True
        
        except Exception as e:
            logger.error(f"Error marking attendance: {e}")
            return False
    
    def get_attendance_records(self, subject=None, date=None, student_id=None):
        """
        Get attendance records
        
        Args:
            subject (str, optional): Filter by subject
            date (str, optional): Filter by date
            student_id (str, optional): Filter by student ID
            
        Returns:
            list: List of attendance records
        """
        try:
            # Build query
            query = "SELECT * FROM Attendance WHERE 1=1"
            params = []
            
            if subject:
                query += " AND subject = ?"
                params.append(subject)
            
            if date:
                query += " AND date = ?"
                params.append(date)
            
            if student_id:
                query += " AND enrollment = ?"
                params.append(student_id)
            
            # Add ordering
            query += " ORDER BY date DESC, time DESC"
            
            # Generate cache key
            cache_key = f"attendance_records_{subject}_{date}_{student_id}"
            
            # Check cache
            if cache_key in self.query_cache:
                # Check expiry
                with self.cache_lock:
                    if cache_key in self.cache_expiry:
                        expiry_time = self.cache_expiry[cache_key]
                        if datetime.datetime.now() < expiry_time:
                            return self.query_cache[cache_key]
            
            # Execute query
            result = self.execute_query(query, tuple(params), fetch_all=True)
            
            # Convert to dictionaries
            records = []
            for row in result:
                records.append({
                    "id": row[0],
                    "enrollment": row[1],
                    "name": row[2],
                    "subject": row[3],
                    "date": row[4],
                    "time": row[5],
                    "confidence": row[6]
                })
            
            # Update cache
            with self.cache_lock:
                self.query_cache[cache_key] = records
                expiry_time = datetime.datetime.now() + datetime.timedelta(seconds=self.cache_ttl)
                self.cache_expiry[cache_key] = expiry_time
            
            return records
        
        except Exception as e:
            logger.error(f"Error getting attendance records: {e}")
            return []
    
    def get_attendance_statistics(self, subject=None, start_date=None, end_date=None):
        """
        Get attendance statistics
        
        Args:
            subject (str, optional): Filter by subject
            start_date (str, optional): Start date in YYYY-MM-DD format
            end_date (str, optional): End date in YYYY-MM-DD format
            
        Returns:
            dict: Attendance statistics
        """
        try:
            # Generate cache key
            cache_key = f"attendance_stats_{subject}_{start_date}_{end_date}"
            
            # Check cache
            if cache_key in self.query_cache:
                # Check expiry
                with self.cache_lock:
                    if cache_key in self.cache_expiry:
                        expiry_time = self.cache_expiry[cache_key]
                        if datetime.datetime.now() < expiry_time:
                            return self.query_cache[cache_key]
            
            # Build query for total attendance
            query = "SELECT COUNT(*) FROM Attendance WHERE 1=1"
            params = []
            
            if subject:
                query += " AND subject = ?"
                params.append(subject)
            
            if start_date:
                query += " AND date >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND date <= ?"
                params.append(end_date)
            
            # Execute query
            result = self.execute_query(query, tuple(params), fetch_one=True)
            total_attendance = result[0] if result else 0
            
            # Build query for unique students
            query = "SELECT COUNT(DISTINCT enrollment) FROM Attendance WHERE 1=1"
            
            if subject:
                query += " AND subject = ?"
            
            if start_date:
                query += " AND date >= ?"
            
            if end_date:
                query += " AND date <= ?"
            
            # Execute query
            result = self.execute_query(query, tuple(params), fetch_one=True)
            unique_students = result[0] if result else 0
            
            # Build query for attendance by date
            query = "SELECT date, COUNT(*) FROM Attendance WHERE 1=1"
            
            if subject:
                query += " AND subject = ?"
            
            if start_date:
                query += " AND date >= ?"
            
            if end_date:
                query += " AND date <= ?"
            
            query += " GROUP BY date ORDER BY date DESC"
            
            # Execute query
            result = self.execute_query(query, tuple(params), fetch_all=True)
            
            # Convert to dictionary
            attendance_by_date = {}
            for row in result:
                attendance_by_date[row[0]] = row[1]
            
            # Build query for top subjects
            if not subject:
                query = "SELECT subject, COUNT(*) FROM Attendance WHERE 1=1"
                params = []
                
                if start_date:
                    query += " AND date >= ?"
                    params.append(start_date)
                
                if end_date:
                    query += " AND date <= ?"
                    params.append(end_date)
                
                query += " GROUP BY subject ORDER BY COUNT(*) DESC LIMIT 5"
                
                # Execute query
                result = self.execute_query(query, tuple(params), fetch_all=True)
                
                # Convert to dictionary
                top_subjects = {}
                for row in result:
                    top_subjects[row[0]] = row[1]
            else:
                top_subjects = {}
            
            # Build result
            statistics = {
                "total_attendance": total_attendance,
                "unique_students": unique_students,
                "attendance_by_date": attendance_by_date,
                "top_subjects": top_subjects
            }
            
            # Update cache
            with self.cache_lock:
                self.query_cache[cache_key] = statistics
                expiry_time = datetime.datetime.now() + datetime.timedelta(seconds=self.cache_ttl)
                self.cache_expiry[cache_key] = expiry_time
            
            return statistics
        
        except Exception as e:
            logger.error(f"Error getting attendance statistics: {e}")
            return {
                "total_attendance": 0,
                "unique_students": 0,
                "attendance_by_date": {},
                "top_subjects": {}
            }
    
    def clear_cache(self):
        """Clear query cache"""
        with self.cache_lock:
            self.query_cache.clear()
            self.cache_expiry.clear()
        logger.info("Query cache cleared")
    
    def close(self):
        """Close all database connections"""
        try:
            with self.pool_lock:
                # Close connections in the pool
                while not self.connection_pool.empty():
                    conn = self.connection_pool.get_nowait()
                    conn.close()
                
                self.active_connections = 0
            
            logger.info("Database connections closed")
            
        except Exception as e:
            logger.error(f"Error closing database connections: {e}")
    
    def vacuum(self):
        """
        Optimize the database by running VACUUM
        
        This should be run periodically to optimize the database
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("VACUUM")
            conn.close()
            logger.info("Database optimized with VACUUM")
            return True
        except Exception as e:
            logger.error(f"Error optimizing database: {e}")
            return False