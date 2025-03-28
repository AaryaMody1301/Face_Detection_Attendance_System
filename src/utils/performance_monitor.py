"""
System performance monitoring utilities
"""
import os
import time
import threading
import logging
import platform
import datetime
from collections import deque

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import platform-specific modules
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    logger.warning("psutil not installed - limited performance monitoring available")
    HAS_PSUTIL = False

try:
    import GPUtil
    HAS_GPUTIL = True
except ImportError:
    logger.warning("GPUtil not installed - GPU monitoring not available")
    HAS_GPUTIL = False


class PerformanceMonitor:
    """
    System performance monitoring for tracking CPU, memory, disk, and GPU usage
    """
    
    def __init__(self, interval=1.0, history_size=60):
        """
        Initialize performance monitor
        
        Args:
            interval (float): Monitoring interval in seconds
            history_size (int): Number of data points to keep in history
        """
        self.interval = max(0.1, interval)
        self.history_size = max(10, history_size)
        
        # Performance metrics history
        self.cpu_history = deque(maxlen=self.history_size)
        self.memory_history = deque(maxlen=self.history_size)
        self.disk_history = deque(maxlen=self.history_size)
        self.gpu_history = deque(maxlen=self.history_size)
        self.frame_rate_history = deque(maxlen=self.history_size)
        self.face_detection_time_history = deque(maxlen=self.history_size)
        
        # Current values
        self.cpu_percent = 0.0
        self.memory_percent = 0.0
        self.memory_used = 0
        self.memory_total = 0
        self.disk_percent = 0.0
        self.gpu_percent = 0.0
        self.gpu_memory_percent = 0.0
        self.frame_rate = 0.0
        self.face_detection_time = 0.0
        
        # Timestamps
        self.last_update = time.time()
        self.start_time = time.time()
        
        # Thread control
        self.running = False
        self.thread = None
        self._lock = threading.Lock()
    
    def start(self):
        """Start the monitoring thread"""
        if self.running:
            logger.warning("Performance monitor is already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        logger.info("Performance monitoring started")
    
    def stop(self):
        """Stop the monitoring thread"""
        self.running = False
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        
        logger.info("Performance monitoring stopped")
    
    def update_frame_rate(self, fps):
        """
        Update the frame rate metric
        
        Args:
            fps (float): Current frames per second
        """
        with self._lock:
            self.frame_rate = fps
            self.frame_rate_history.append((time.time(), fps))
    
    def update_face_detection_time(self, detection_time):
        """
        Update the face detection time metric
        
        Args:
            detection_time (float): Time taken for face detection in seconds
        """
        with self._lock:
            self.face_detection_time = detection_time
            self.face_detection_time_history.append((time.time(), detection_time))
    
    def get_current_metrics(self):
        """
        Get current performance metrics
        
        Returns:
            dict: Dictionary of current performance metrics
        """
        with self._lock:
            return {
                "cpu_percent": self.cpu_percent,
                "memory_percent": self.memory_percent,
                "memory_used": self.memory_used,
                "memory_total": self.memory_total,
                "disk_percent": self.disk_percent,
                "gpu_percent": self.gpu_percent,
                "gpu_memory_percent": self.gpu_memory_percent,
                "frame_rate": self.frame_rate,
                "face_detection_time": self.face_detection_time,
                "uptime": time.time() - self.start_time
            }
    
    def get_history(self, metric, time_range=None):
        """
        Get historical data for a specific metric
        
        Args:
            metric (str): Metric name
            time_range (tuple, optional): Time range (start, end) in seconds
            
        Returns:
            list: List of (timestamp, value) tuples
        """
        history_map = {
            "cpu": self.cpu_history,
            "memory": self.memory_history,
            "disk": self.disk_history,
            "gpu": self.gpu_history,
            "frame_rate": self.frame_rate_history,
            "face_detection_time": self.face_detection_time_history
        }
        
        if metric not in history_map:
            return []
        
        with self._lock:
            history = list(history_map[metric])
        
        if time_range:
            start_time, end_time = time_range
            now = time.time()
            history = [(t, v) for t, v in history if now - t >= start_time and now - t <= end_time]
        
        return history
    
    def get_system_info(self):
        """
        Get system information
        
        Returns:
            dict: System information
        """
        info = {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "processor": platform.processor(),
            "hostname": platform.node()
        }
        
        if HAS_PSUTIL:
            try:
                # CPU info
                info["cpu_count"] = psutil.cpu_count(logical=True)
                info["cpu_physical_count"] = psutil.cpu_count(logical=False)
                
                # Memory info
                memory = psutil.virtual_memory()
                info["total_memory"] = memory.total
                
                # Disk info
                disk = psutil.disk_usage('/')
                info["total_disk"] = disk.total
                
                # System uptime
                info["system_uptime"] = datetime.timedelta(seconds=int(time.time() - psutil.boot_time()))
            except Exception as e:
                logger.error(f"Error getting system info: {e}")
        
        if HAS_GPUTIL:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    info["gpu_name"] = gpus[0].name
                    info["gpu_memory"] = gpus[0].memoryTotal
                    info["gpu_driver"] = gpus[0].driver
            except Exception as e:
                logger.error(f"Error getting GPU info: {e}")
        
        return info
    
    def generate_report(self):
        """
        Generate a performance report
        
        Returns:
            dict: Performance report
        """
        current = self.get_current_metrics()
        
        # Calculate averages
        avg_cpu = sum(v for _, v in self.cpu_history) / max(1, len(self.cpu_history))
        avg_memory = sum(v for _, v in self.memory_history) / max(1, len(self.memory_history))
        avg_frame_rate = sum(v for _, v in self.frame_rate_history) / max(1, len(self.frame_rate_history))
        avg_face_time = sum(v for _, v in self.face_detection_time_history) / max(1, len(self.face_detection_time_history))
        
        # Calculate peaks
        peak_cpu = max([v for _, v in self.cpu_history] or [0])
        peak_memory = max([v for _, v in self.memory_history] or [0])
        
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "uptime": datetime.timedelta(seconds=int(current["uptime"])),
            "current": current,
            "averages": {
                "cpu_percent": avg_cpu,
                "memory_percent": avg_memory,
                "frame_rate": avg_frame_rate,
                "face_detection_time": avg_face_time
            },
            "peaks": {
                "cpu_percent": peak_cpu,
                "memory_percent": peak_memory
            },
            "system_info": self.get_system_info()
        }
        
        return report
    
    def _monitor_loop(self):
        """Main monitoring loop running in a separate thread"""
        while self.running:
            try:
                self._update_metrics()
                time.sleep(self.interval)
            except Exception as e:
                logger.error(f"Error in performance monitoring loop: {e}")
                time.sleep(self.interval)
    
    def _update_metrics(self):
        """Update all performance metrics"""
        now = time.time()
        
        try:
            # Update CPU usage
            if HAS_PSUTIL:
                self.cpu_percent = psutil.cpu_percent(interval=None)
                
                # Update memory usage
                memory = psutil.virtual_memory()
                self.memory_percent = memory.percent
                self.memory_used = memory.used
                self.memory_total = memory.total
                
                # Update disk usage
                disk = psutil.disk_usage('/')
                self.disk_percent = disk.percent
            else:
                # Fallback if psutil not available
                self.cpu_percent = 0.0
                self.memory_percent = 0.0
                self.disk_percent = 0.0
            
            # Update GPU usage
            if HAS_GPUTIL:
                try:
                    gpus = GPUtil.getGPUs()
                    if gpus:
                        self.gpu_percent = gpus[0].load * 100
                        self.gpu_memory_percent = (gpus[0].memoryUsed / gpus[0].memoryTotal) * 100
                except Exception:
                    self.gpu_percent = 0.0
                    self.gpu_memory_percent = 0.0
            else:
                self.gpu_percent = 0.0
                self.gpu_memory_percent = 0.0
            
            # Add to history
            with self._lock:
                self.cpu_history.append((now, self.cpu_percent))
                self.memory_history.append((now, self.memory_percent))
                self.disk_history.append((now, self.disk_percent))
                self.gpu_history.append((now, self.gpu_percent))
            
        except Exception as e:
            logger.error(f"Error updating performance metrics: {e}")


# Singleton instance for global access
_monitor_instance = None

def get_performance_monitor():
    """
    Get global performance monitor instance
    
    Returns:
        PerformanceMonitor: Global performance monitor instance
    """
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = PerformanceMonitor()
    return _monitor_instance