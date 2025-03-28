"""
Database Manager for the Face Detection Attendance System

This module provides a centralized way to manage database connections
and operations using SQLite with connection pooling, prepared statements,
and comprehensive error handling.
"""
import os
import sqlite3
import logging
import threading
import time
import datetime
from typing import Dict, Any, Optional, List, Tuple, Union
from contextlib import contextmanager
import queue
import traceback

from ..utils.app_config import AppConfig
from ..utils.exceptions import DatabaseError, ConnectionPoolError

# Configure logging
logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Database Manager class for handling database connections and operations
    
    Features:
    - Connection pooling for improved performance
    - Prepared statements for security
    - Automatic retry on transient errors
    - Comprehensive error handling
    - Transaction support
    - Query result caching (optional)
    
    Attributes:
        db_path: Path to the database file
        pool_size: Size of the connection pool
        max_retries: Maximum number of query retries
        retry_delay: Delay between retries in seconds
        connection_pool: Queue of database connections
        query_cache: Cache for query results
        cache_ttl: Time-to-live for cached results in seconds
        pool_lock: Lock for thread-safe pool operations
        cache_lock: Lock for thread-safe cache operations
    """
    
    _instance = None
    _instance_lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """Singleton pattern implementation"""
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super(DatabaseManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self, db_path: Optional[str] = None, pool_size: int = 5,
                 max_retries: int = 3, retry_delay: float = 0.5,
                 enable_cache: bool = True, cache_ttl: int = 300):
        """
        Initialize the database manager
        
        Args:
            db_path: Path to the database file. If None, uses config value.
            pool_size: Size of the connection pool
            max_retries: Maximum number of query retries
            retry_delay: Delay between retries in seconds
            enable_cache: Whether to enable query caching
            cache_ttl: Time-to-live for cached results in seconds
        """
        # Only initialize once (singleton pattern)
        if self._initialized:
            return
            
        # Load configuration
        self.config = AppConfig()
        
        # Set database path
        if db_path is None:
            self.db_path = self.config.get("database.path", "Data/attendance.db")
        else:
            self.db_path = db_path
            
        # Ensure the database directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Connection pool settings
        self.pool_size = pool_size
        self.connection_pool = queue.Queue(maxsize=pool_size)
        self.pool_lock = threading.Lock()
        
        # Retry settings
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Cache settings
        self.enable_cache = enable_cache
        self.cache_ttl = cache_ttl
        self.query_cache = {}
        self.cache_expiry = {}
        self.cache_lock = threading.Lock()
        
        # Database optimization tracking
        self.last_optimize = datetime.datetime.now() - datetime.timedelta(days=30)  # Initialize as 30 days ago
        
        # Initialize the database
        self._init_database()
        
        # Fill the connection pool
        self._fill_pool()
        
        # Set up periodic cache cleaning
        if self.enable_cache:
            self._setup_cache_cleanup()
            
        # Mark as initialized
        self._initialized = True
        
        logger.info(f"DatabaseManager initialized: {self.db_path}")
    
    def _fill_pool(self):
        """Fill the connection pool with fresh connections"""
        try:
            while not self.connection_pool.full():
                conn = self._create_connection()
                self.connection_pool.put(conn)
        except Exception as e:
            logger.error(f"Error filling connection pool: {e}")
            raise ConnectionPoolError(f"Failed to fill connection pool: {e}")
    
    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection"""
        try:
            # Create connection with extended error handling
            conn = sqlite3.connect(
                self.db_path,
                timeout=60.0,  # Longer timeout for busy database
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
                isolation_level=None  # Autocommit mode
            )
            
            # Enable foreign keys
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Set busy timeout
            conn.execute("PRAGMA busy_timeout = 30000")  # 30 seconds
            
            # Use write-ahead logging for better concurrency
            conn.execute("PRAGMA journal_mode = WAL")
            
            # Return dictionary-like rows
            conn.row_factory = sqlite3.Row
            
            return conn
        except Exception as e:
            logger.error(f"Error creating database connection: {e}")
            raise ConnectionPoolError(f"Failed to create database connection: {e}")
    
    def _setup_cache_cleanup(self):
        """Set up periodic cache cleanup"""
        def cleanup_task():
            while True:
                try:
                    self._cleanup_cache()
                    time.sleep(self.cache_ttl / 2)  # Run cleanup at half TTL interval
                except Exception as e:
                    logger.error(f"Error in cache cleanup task: {e}")
                    time.sleep(60)  # Wait and try again
        
        cleanup_thread = threading.Thread(target=cleanup_task, daemon=True)
        cleanup_thread.start()
    
    def _cleanup_cache(self):
        """Remove expired items from cache"""
        if not self.enable_cache:
            return
            
        with self.cache_lock:
            current_time = datetime.datetime.now()
            expired_keys = []
            
            for key, expiry in self.cache_expiry.items():
                if current_time > expiry:
                    expired_keys.append(key)
            
            # Remove expired items
            for key in expired_keys:
                self.query_cache.pop(key, None)
                self.cache_expiry.pop(key, None)
                
            # Log cleanup results
            if expired_keys:
                logger.debug(f"Cache cleanup: removed {len(expired_keys)} expired items")
    
    def _get_connection(self) -> sqlite3.Connection:
        """
        Get a connection from the pool
        
        Returns:
            SQLite connection
        
        Raises:
            ConnectionPoolError: If no connections are available
        """
        try:
            # Try to get a connection from the pool
            return self.connection_pool.get(timeout=5)
        except queue.Empty:
            # Pool is empty, create a new connection as fallback
            logger.warning("Connection pool empty, creating new connection")
            return self._create_connection()
        except Exception as e:
            logger.error(f"Error getting connection from pool: {e}")
            raise ConnectionPoolError(f"Failed to get connection from pool: {e}")
    
    def _return_connection(self, conn: sqlite3.Connection):
        """
        Return a connection to the pool
        
        Args:
            conn: SQLite connection to return
        """
        try:
            if conn:
                try:
                    # Check if connection is valid
                    conn.execute("SELECT 1").fetchone()
                    # Put connection back in pool
                    self.connection_pool.put(conn, timeout=5)
                except (sqlite3.Error, queue.Full) as e:
                    # Connection is invalid or pool is full, close it
                    try:
                        conn.close()
                    except:
                        pass
                    logger.warning(f"Connection not returned to pool: {e}")
        except Exception as e:
            logger.error(f"Error returning connection to pool: {e}")
            try:
                conn.close()
            except:
                pass
    
    @contextmanager
    def get_connection(self):
        """
        Context manager for getting a database connection
        
        Example:
            with db_manager.get_connection() as conn:
                conn.execute("SELECT * FROM students")
        
        Yields:
            SQLite connection
        """
        conn = None
        try:
            conn = self._get_connection()
            yield conn
        except Exception as e:
            logger.error(f"Error in connection context manager: {e}")
            raise
        finally:
            if conn:
                self._return_connection(conn)
    
    @contextmanager
    def transaction(self):
        """
        Context manager for database transactions
        
        Example:
            with db_manager.transaction() as conn:
                conn.execute("INSERT INTO students VALUES (?, ?)", ("12345", "John Doe"))
                conn.execute("INSERT INTO attendance VALUES (?, ?, ?)", ("12345", "Math", "2023-03-28"))
        
        Yields:
            SQLite connection with active transaction
        """
        conn = None
        try:
            conn = self._get_connection()
            # Start transaction
            conn.execute("BEGIN")
            yield conn
            # Commit if no exceptions
            conn.execute("COMMIT")
        except Exception as e:
            # Rollback on error
            if conn:
                try:
                    conn.execute("ROLLBACK")
                except:
                    pass
            logger.error(f"Error in transaction: {e}")
            raise
        finally:
            if conn:
                self._return_connection(conn)
    
    def execute_query(self, query: str, params: tuple = (), fetch_all: bool = False,
                     fetch_one: bool = False, commit: bool = False, 
                     use_cache: bool = False) -> Union[List[Dict[str, Any]], Dict[str, Any], int, None]:
        """
        Execute a database query with retries
        
        Args:
            query: SQL query to execute

        Returns:
            Query result or affected row count
        """
        pass  # Placeholder for the rest of the method implementation
    
    def optimize_database(self, force: bool = False) -> bool:
        """
        Optimize the database using VACUUM
        
        Args:
            force: If True, optimize regardless of when last optimization occurred
            
        Returns:
            True if optimization was performed, False otherwise
        """
        try:
            # Check if optimization is needed (default: once per week)
            current_time = datetime.datetime.now()
            days_since_last = (current_time - self.last_optimize).days
            
            if not force and days_since_last < 7:
                logger.info(f"Database optimization skipped (last optimized {days_since_last} days ago)")
                return False
            
            logger.info("Starting database optimization (VACUUM)...")
            
            with self.get_connection() as conn:
                # Execute VACUUM
                conn.execute("VACUUM")
            
            # Update last optimize time
            self.last_optimize = current_time
            
            logger.info("Database optimization completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error during database optimization: {e}")
            traceback.print_exc()
            return False
    
    def _init_database(self):
        """Initialize the database schema if it doesn't exist"""
        try:
            logger.info(f"Initializing database schema at: {self.db_path}")
            
            # Create tables if they don't exist
            with self.get_connection() as conn:
                # Students table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS students (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        email TEXT,
                        phone TEXT,
                        enrollment_date TEXT DEFAULT CURRENT_DATE,
                        program TEXT,
                        profile_image TEXT,
                        active INTEGER DEFAULT 1,
                        last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Courses table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS courses (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        description TEXT,
                        instructor TEXT,
                        active INTEGER DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Attendance table - ensure student_id column exists before creating index
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS attendance (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        student_id TEXT NOT NULL,
                        course_id TEXT NOT NULL,
                        date TEXT NOT NULL,
                        time TEXT NOT NULL,
                        status TEXT DEFAULT 'present',
                        method TEXT DEFAULT 'auto',
                        FOREIGN KEY (student_id) REFERENCES students(id),
                        FOREIGN KEY (course_id) REFERENCES courses(id),
                        UNIQUE(student_id, course_id, date)
                    )
                ''')
                
                # Users table (for authentication)
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        role TEXT NOT NULL,
                        full_name TEXT,
                        email TEXT,
                        last_login TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        active INTEGER DEFAULT 1
                    )
                ''')
                
                # Only create indexes after tables are confirmed to exist
                try:
                    # Create indices for better performance
                    conn.execute('CREATE INDEX IF NOT EXISTS idx_attendance_student_id ON attendance(student_id)')
                    conn.execute('CREATE INDEX IF NOT EXISTS idx_attendance_course_id ON attendance(course_id)')
                    conn.execute('CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(date)')
                except Exception as idx_error:
                    logger.warning(f"Error creating indexes, but continuing: {idx_error}")
            
            # Create default admin user if none exists
            self._create_default_admin()
            
            logger.info("Database schema initialization completed")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing database schema: {e}")
            traceback.print_exc()
            raise DatabaseError(f"Failed to initialize database: {e}")
    
    def _create_default_admin(self):
        """Create a default admin user if no users exist"""
        try:
            with self.get_connection() as conn:
                # Check if any users exist
                result = conn.execute('SELECT COUNT(*) FROM users').fetchone()
                if result and result[0] > 0:
                    return
                
                # Create default admin user
                # Using a simple password hash for demo purposes
                # In production, use a proper password hashing library
                import hashlib
                default_password = "admin123"  # Change this in production
                password_hash = hashlib.sha256(default_password.encode()).hexdigest()
                
                conn.execute('''
                    INSERT INTO users (username, password_hash, role, full_name, email)
                    VALUES (?, ?, ?, ?, ?)
                ''', ('admin', password_hash, 'admin', 'Administrator', 'admin@example.com'))
                
                logger.info("Created default admin user")
        except Exception as e:
            logger.error(f"Error creating default admin user: {e}")
            traceback.print_exc()