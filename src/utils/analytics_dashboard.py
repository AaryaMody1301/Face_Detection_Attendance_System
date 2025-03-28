"""
Attendance analytics dashboard with performance optimizations
"""
import os
import logging
import datetime
from typing import Dict, List, Tuple, Any
import threading

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AttendanceAnalyticsDashboard:
    """Analytics dashboard for attendance data visualization"""
    
    def __init__(self, db_handler):
        """
        Initialize the analytics dashboard
        
        Args:
            db_handler: Database handler instance
        """
        self.db = db_handler
        self.cache = {}
        self.cache_lock = threading.Lock()
        self.cache_expiry = {}
        self.cache_ttl = 300  # 5 minutes in seconds
    
    def get_attendance_overview(self, refresh=False) -> Dict[str, Any]:
        """
        Get an overview of attendance statistics
        
        Args:
            refresh (bool): Force refresh of data
            
        Returns:
            dict: Attendance overview statistics
        """
        cache_key = "attendance_overview"
        
        # Check cache if not refreshing
        if not refresh and self._check_cache(cache_key):
            return self.cache[cache_key]
        
        try:
            # Get current date for calculations
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            
            # Get 30 days ago for monthly statistics
            thirty_days_ago = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
            
            # Get statistics from database
            stats = self.db.get_attendance_statistics(
                start_date=thirty_days_ago,
                end_date=today
            )
            
            # Calculate additional metrics
            result = {
                "total_attendance": stats.get("total_attendance", 0),
                "unique_students": stats.get("unique_students", 0),
                "attendance_by_date": stats.get("attendance_by_date", {}),
                "top_subjects": stats.get("top_subjects", {})
            }
            
            # Add today's attendance count
            result["today_attendance"] = stats.get("attendance_by_date", {}).get(today, 0)
            
            # Calculate average daily attendance
            days_with_attendance = len(stats.get("attendance_by_date", {}))
            if days_with_attendance > 0:
                result["avg_daily_attendance"] = stats.get("total_attendance", 0) / days_with_attendance
            else:
                result["avg_daily_attendance"] = 0
            
            # Store in cache
            self._update_cache(cache_key, result)
            
            return result
        except Exception as e:
            logger.error(f"Error getting attendance overview: {e}")
            return {
                "total_attendance": 0,
                "unique_students": 0,
                "today_attendance": 0,
                "avg_daily_attendance": 0,
                "attendance_by_date": {},
                "top_subjects": {}
            }
    
    def get_subject_statistics(self, subject=None, refresh=False) -> Dict[str, Any]:
        """
        Get statistics for a specific subject or all subjects
        
        Args:
            subject (str, optional): Subject name or None for all subjects
            refresh (bool): Force refresh of data
            
        Returns:
            dict: Subject statistics
        """
        cache_key = f"subject_stats_{subject}" if subject else "subject_stats_all"
        
        # Check cache if not refreshing
        if not refresh and self._check_cache(cache_key):
            return self.cache[cache_key]
        
        try:
            # Get current date for calculations
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            
            # Get 30 days ago for monthly statistics
            thirty_days_ago = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
            
            # Get statistics from database
            stats = self.db.get_attendance_statistics(
                subject=subject,
                start_date=thirty_days_ago,
                end_date=today
            )
            
            # Format result
            result = {
                "subject": subject if subject else "All Subjects",
                "total_attendance": stats.get("total_attendance", 0),
                "unique_students": stats.get("unique_students", 0),
                "attendance_by_date": stats.get("attendance_by_date", {})
            }
            
            # Store in cache
            self._update_cache(cache_key, result)
            
            return result
        except Exception as e:
            logger.error(f"Error getting subject statistics: {e}")
            return {
                "subject": subject if subject else "All Subjects",
                "total_attendance": 0,
                "unique_students": 0,
                "attendance_by_date": {}
            }
    
    def get_attendance_trends(self, days=30, refresh=False) -> Dict[str, Any]:
        """
        Get attendance trends over time
        
        Args:
            days (int): Number of days to include
            refresh (bool): Force refresh of data
            
        Returns:
            dict: Attendance trend data
        """
        cache_key = f"attendance_trends_{days}"
        
        # Check cache if not refreshing
        if not refresh and self._check_cache(cache_key):
            return self.cache[cache_key]
        
        try:
            # Calculate date range
            end_date = datetime.datetime.now()
            start_date = end_date - datetime.timedelta(days=days)
            
            # Format dates for database query
            start_date_str = start_date.strftime("%Y-%m-%d")
            end_date_str = end_date.strftime("%Y-%m-%d")
            
            # Get statistics from database
            stats = self.db.get_attendance_statistics(
                start_date=start_date_str,
                end_date=end_date_str
            )
            
            # Get attendance by date
            attendance_by_date = stats.get("attendance_by_date", {})
            
            # Generate complete date range (including days with no attendance)
            complete_date_range = {}
            current_date = start_date
            while current_date <= end_date:
                date_str = current_date.strftime("%Y-%m-%d")
                complete_date_range[date_str] = attendance_by_date.get(date_str, 0)
                current_date += datetime.timedelta(days=1)
            
            # Calculate trend data
            dates = list(complete_date_range.keys())
            counts = list(complete_date_range.values())
            
            # Calculate moving average (7-day)
            moving_avg = []
            for i in range(len(counts)):
                start_idx = max(0, i - 6)
                end_idx = i + 1
                window = counts[start_idx:end_idx]
                avg = sum(window) / len(window) if window else 0
                moving_avg.append(avg)
            
            result = {
                "period_days": days,
                "dates": dates,
                "counts": counts,
                "moving_avg": moving_avg,
                "total_attendance": stats.get("total_attendance", 0),
                "avg_daily_attendance": stats.get("total_attendance", 0) / len(dates) if dates else 0
            }
            
            # Store in cache
            self._update_cache(cache_key, result)
            
            return result
        except Exception as e:
            logger.error(f"Error getting attendance trends: {e}")
            return {
                "period_days": days,
                "dates": [],
                "counts": [],
                "moving_avg": [],
                "total_attendance": 0,
                "avg_daily_attendance": 0
            }
    
    def get_student_attendance(self, student_id=None, refresh=False) -> Dict[str, Any]:
        """
        Get attendance data for a specific student
        
        Args:
            student_id (int, optional): Student ID or None for all students
            refresh (bool): Force refresh of data
            
        Returns:
            dict: Student attendance data
        """
        cache_key = f"student_attendance_{student_id}" if student_id else "student_attendance_all"
        
        # Check cache if not refreshing
        if not refresh and self._check_cache(cache_key):
            return self.cache[cache_key]
        
        try:
            # Get all attendance records for the student
            records = self.db.get_attendance_records(student_id=student_id)
            
            # Organize by subject
            attendance_by_subject = {}
            for record in records:
                subject = record.get("subject", "Unknown")
                if subject not in attendance_by_subject:
                    attendance_by_subject[subject] = []
                attendance_by_subject[subject].append(record)
            
            # Count by date
            attendance_by_date = {}
            for record in records:
                date = record.get("date", "Unknown")
                if date not in attendance_by_date:
                    attendance_by_date[date] = 0
                attendance_by_date[date] += 1
            
            result = {
                "student_id": student_id,
                "total_attendance": len(records),
                "subjects_attended": len(attendance_by_subject),
                "attendance_by_subject": {subject: len(records) for subject, records in attendance_by_subject.items()},
                "attendance_by_date": attendance_by_date
            }
            
            # Store in cache
            self._update_cache(cache_key, result)
            
            return result
        except Exception as e:
            logger.error(f"Error getting student attendance: {e}")
            return {
                "student_id": student_id,
                "total_attendance": 0,
                "subjects_attended": 0,
                "attendance_by_subject": {},
                "attendance_by_date": {}
            }
    
    def _check_cache(self, key: str) -> bool:
        """
        Check if a key is in cache and not expired
        
        Args:
            key (str): Cache key
            
        Returns:
            bool: True if key is in cache and not expired
        """
        with self.cache_lock:
            if key not in self.cache:
                return False
            
            # Check expiry
            if key in self.cache_expiry:
                expiry_time = self.cache_expiry[key]
                if datetime.datetime.now() > expiry_time:
                    # Expired
                    del self.cache[key]
                    del self.cache_expiry[key]
                    return False
            
            return True
    
    def _update_cache(self, key: str, value: Any) -> None:
        """
        Update cache with a new value
        
        Args:
            key (str): Cache key
            value (Any): Value to cache
        """
        with self.cache_lock:
            self.cache[key] = value
            expiry_time = datetime.datetime.now() + datetime.timedelta(seconds=self.cache_ttl)
            self.cache_expiry[key] = expiry_time
    
    def clear_cache(self) -> None:
        """Clear all cached data"""
        with self.cache_lock:
            self.cache.clear()
            self.cache_expiry.clear()
        logger.info("Analytics cache cleared")