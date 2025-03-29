"""
Backup Manager for Face Detection Attendance System
"""
import os
import shutil
import logging
import datetime
import sqlite3
import csv
from collections import namedtuple
from pathlib import Path

from src.utils.config_manager import ConfigManager

# Set up logging
logger = logging.getLogger(__name__)

# Define result type for backup operations
BackupResult = namedtuple('BackupResult', ['success', 'message'])

class BackupManager:
    """Manages backups of attendance data, student data and training images"""
    
    def __init__(self):
        """Initialize the backup manager"""
        # Load configuration
        config_manager = ConfigManager()
        self.config = config_manager.get_config()
        
        # Get backup settings
        self.auto_backup = self.config.get("backup", {}).get("auto_backup", True)
        self.frequency_days = self.config.get("backup", {}).get("frequency_days", 7)
        
        # Define backup directories
        self.attendance_backup_dir = os.path.join("backups", "attendance_backup")
        self.data_backup_dir = os.path.join("backups", "data_backup")
        self.training_backup_dir = os.path.join("backups", "training_image_backup")
        
        # Ensure backup directories exist
        for directory in [self.attendance_backup_dir, self.data_backup_dir, self.training_backup_dir]:
            os.makedirs(directory, exist_ok=True)
        
        logger.info("Backup manager initialized")
    
    def should_backup(self):
        """
        Check if a backup should be performed based on settings and last backup date
        
        Returns:
            bool: True if backup should be performed
        """
        if not self.auto_backup:
            return False
        
        # Check when last backup was performed
        last_backup_file = os.path.join(self.data_backup_dir, "last_backup_date.txt")
        
        if os.path.exists(last_backup_file):
            try:
                with open(last_backup_file, 'r') as f:
                    last_backup_date_str = f.read().strip()
                    last_backup_date = datetime.datetime.strptime(last_backup_date_str, "%Y-%m-%d")
                    
                    # Calculate days since last backup
                    days_since_backup = (datetime.datetime.now() - last_backup_date).days
                    
                    # Check if backup is due
                    return days_since_backup >= self.frequency_days
            except Exception as e:
                logger.error(f"Error checking last backup date: {e}")
                return True
        
        # No last backup date found, backup is needed
        return True
    
    def perform_backup(self):
        """
        Perform backup of all data
        
        Returns:
            BackupResult: Success status and message
        """
        try:
            results = []
            
            # Backup attendance data
            attendance_result = self._backup_attendance()
            results.append(attendance_result)
            
            # Backup database
            database_result = self._backup_database()
            results.append(database_result)
            
            # Backup training images
            training_result = self._backup_training_images()
            results.append(training_result)
            
            # Update last backup date
            self._update_last_backup_date()
            
            # Combine results
            success = all(result.success for result in results)
            message_parts = [result.message for result in results if result.message]
            message = "\n".join(message_parts)
            
            logger.info(f"Backup completed with status: {success}")
            
            return BackupResult(success=success, message=message)
        
        except Exception as e:
            error_message = f"Error performing backup: {e}"
            logger.error(error_message)
            return BackupResult(success=False, message=error_message)
    
    def _backup_attendance(self):
        """
        Backup attendance CSV files
        
        Returns:
            BackupResult: Success status and message
        """
        try:
            attendance_dir = "Attendance"
            if not os.path.exists(attendance_dir):
                return BackupResult(success=True, message="No attendance files found to backup")
            
            copied_files = 0
            
            # Copy each CSV file to backup directory
            for file in os.listdir(attendance_dir):
                if file.endswith(".csv"):
                    src = os.path.join(attendance_dir, file)
                    
                    # Only backup files newer than any existing backup
                    dest = os.path.join(self.attendance_backup_dir, file)
                    
                    # Check if file needs to be backed up (doesn't exist or source is newer)
                    if not os.path.exists(dest) or os.path.getmtime(src) > os.path.getmtime(dest):
                        shutil.copy2(src, dest)
                        copied_files += 1
            
            message = f"Successfully backed up {copied_files} attendance files"
            logger.info(message)
            
            return BackupResult(success=True, message=message)
        
        except Exception as e:
            error_message = f"Error backing up attendance: {e}"
            logger.error(error_message)
            return BackupResult(success=False, message=error_message)
    
    def _backup_database(self):
        """
        Backup SQLite database
        
        Returns:
            BackupResult: Success status and message
        """
        try:
            db_path = self.config.get("database", {}).get("path", "Data/attendance.db")
            
            if not os.path.exists(db_path):
                return BackupResult(success=True, message="No database found to backup")
            
            # Create backup filename with timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"attendance_db_backup_{timestamp}.db"
            backup_path = os.path.join(self.data_backup_dir, backup_filename)
            
            # Copy database file
            shutil.copy2(db_path, backup_path)
            
            # Create CSV export of tables
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get list of tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            for table_name in tables:
                table = table_name[0]
                csv_filename = f"{table}_{timestamp}.csv"
                csv_path = os.path.join(self.data_backup_dir, csv_filename)
                
                # Export table to CSV
                cursor.execute(f"SELECT * FROM {table};")
                rows = cursor.fetchall()
                
                # Get column names
                cursor.execute(f"PRAGMA table_info({table});")
                columns = [col[1] for col in cursor.fetchall()]
                
                with open(csv_path, 'w', newline='') as csv_file:
                    csv_writer = csv.writer(csv_file)
                    csv_writer.writerow(columns)
                    csv_writer.writerows(rows)
            
            conn.close()
            
            message = f"Successfully backed up database to {backup_path} with CSV exports"
            logger.info(message)
            
            return BackupResult(success=True, message=message)
        
        except Exception as e:
            error_message = f"Error backing up database: {e}"
            logger.error(error_message)
            return BackupResult(success=False, message=error_message)
    
    def _backup_training_images(self):
        """
        Backup training images
        
        Returns:
            BackupResult: Success status and message
        """
        try:
            training_dir = "TrainingImage"
            if not os.path.exists(training_dir):
                return BackupResult(success=True, message="No training images found to backup")
            
            # Create timestamp directory for organized backups
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = os.path.join(self.training_backup_dir, f"backup_{timestamp}")
            os.makedirs(backup_dir, exist_ok=True)
            
            # Count files
            file_count = 0
            
            # Copy all image files
            for file in os.listdir(training_dir):
                if file.lower().endswith((".jpg", ".jpeg", ".png")):
                    shutil.copy2(
                        os.path.join(training_dir, file),
                        os.path.join(backup_dir, file)
                    )
                    file_count += 1
            
            # Also backup label files
            label_dir = "TrainingImageLabel"
            if os.path.exists(label_dir):
                label_backup_dir = os.path.join(backup_dir, "labels")
                os.makedirs(label_backup_dir, exist_ok=True)
                
                for file in os.listdir(label_dir):
                    if file.lower().endswith((".yml", ".npz")):
                        shutil.copy2(
                            os.path.join(label_dir, file),
                            os.path.join(label_backup_dir, file)
                        )
            
            message = f"Successfully backed up {file_count} training images to {backup_dir}"
            logger.info(message)
            
            return BackupResult(success=True, message=message)
        
        except Exception as e:
            error_message = f"Error backing up training images: {e}"
            logger.error(error_message)
            return BackupResult(success=False, message=error_message)
    
    def _update_last_backup_date(self):
        """Update the last backup date file"""
        try:
            last_backup_file = os.path.join(self.data_backup_dir, "last_backup_date.txt")
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            
            with open(last_backup_file, 'w') as f:
                f.write(today)
            
            logger.info(f"Updated last backup date to {today}")
        
        except Exception as e:
            logger.error(f"Error updating last backup date: {e}")
    
    def clean_old_backups(self, max_days=30):
        """
        Remove backups older than specified number of days
        
        Args:
            max_days: Maximum age of backups in days
            
        Returns:
            BackupResult: Success status and message
        """
        try:
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=max_days)
            removed_files = 0
            
            # Clean database backups
            for file in os.listdir(self.data_backup_dir):
                if file.startswith("attendance_db_backup_") and file.endswith(".db"):
                    try:
                        # Extract timestamp from filename
                        timestamp_str = file[len("attendance_db_backup_"):-3]
                        timestamp = datetime.datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                        
                        if timestamp < cutoff_date:
                            os.remove(os.path.join(self.data_backup_dir, file))
                            removed_files += 1
                    except (ValueError, IndexError):
                        pass
            
            # Clean training image backups
            for dir_name in os.listdir(self.training_backup_dir):
                if dir_name.startswith("backup_"):
                    try:
                        # Extract timestamp from directory name
                        timestamp_str = dir_name[len("backup_"):]
                        timestamp = datetime.datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                        
                        if timestamp < cutoff_date:
                            shutil.rmtree(os.path.join(self.training_backup_dir, dir_name))
                            removed_files += 1
                    except (ValueError, IndexError):
                        pass
            
            message = f"Successfully removed {removed_files} old backup files (older than {max_days} days)"
            logger.info(message)
            
            return BackupResult(success=True, message=message)
        
        except Exception as e:
            error_message = f"Error cleaning old backups: {e}"
            logger.error(error_message)
            return BackupResult(success=False, message=error_message)