"""
Camera management utility class for Face Detection Attendance System
"""
import cv2
import logging
import time
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any, Callable

# Set up logging
logger = logging.getLogger(__name__)

@dataclass
class CameraResult:
    """Class to hold camera operation results"""
    success: bool
    camera_id: int = -1
    camera: Optional[cv2.VideoCapture] = None
    camera_info: str = ""
    error_message: str = ""
    width: int = 0
    height: int = 0
    fps: int = 0

class CameraStatus(Enum):
    """Camera connection status enum"""
    DISCONNECTED = 0
    CONNECTED = 1
    ERROR = 2
    BUSY = 3

class CameraInfo:
    """Class to store camera information"""
    def __init__(self, index: int, name: str = ""):
        self.index = index
        self.name = name if name else f"Camera {index}"
        self.is_available = False
        self.resolution = (0, 0)
        self.fps = 0
    
    def __str__(self) -> str:
        return f"{self.name} ({self.resolution[0]}x{self.resolution[1]}@{self.fps}fps)"

class CameraManager:
    """
    Class for managing camera connections and providing video feeds
    """
    
    def __init__(self, camera_id=0, resolution=(640, 480)):
        """
        Initialize the camera manager
        
        Args:
            camera_id (int or str): Camera identifier (index or path)
            resolution (tuple): Target resolution (width, height)
        """
        self.camera_id = camera_id
        self.resolution = resolution
        self.cap = None
        self.status = CameraStatus.DISCONNECTED
        self.last_error = None
        self._frame_processors = []
        self._available_cameras = []
        self.flip_horizontal = False
        
    def connect(self) -> bool:
        """
        Connect to the camera
        
        Returns:
            bool: True if connection was successful
        """
        # Close previous connection if any
        self.disconnect()
        
        try:
            # Try to connect to the camera
            self.cap = cv2.VideoCapture(self.camera_id)
            
            # Check if camera is opened successfully
            if not self.cap.isOpened():
                self.status = CameraStatus.ERROR
                self.last_error = "Failed to open camera connection"
                logger.error(f"Failed to connect to camera {self.camera_id}")
                return False
            
            # Set resolution if provided
            if self.resolution:
                width, height = self.resolution
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            
            self.status = CameraStatus.CONNECTED
            logger.info(f"Successfully connected to camera {self.camera_id}")
            return True
            
        except Exception as e:
            self.status = CameraStatus.ERROR
            self.last_error = str(e)
            logger.error(f"Error connecting to camera {self.camera_id}: {str(e)}")
            return False
            
    def disconnect(self) -> bool:
        """
        Disconnect from the camera
        
        Returns:
            bool: True if disconnection was successful
        """
        if self.cap is not None:
            try:
                self.cap.release()
                self.status = CameraStatus.DISCONNECTED
                return True
            except Exception as e:
                self.last_error = str(e)
                logger.error(f"Error disconnecting from camera: {str(e)}")
                return False
        return True
        
    def is_connected(self) -> bool:
        """
        Check if camera is connected
        
        Returns:
            bool: True if camera is connected and working
        """
        return self.status == CameraStatus.CONNECTED and self.cap is not None and self.cap.isOpened()
            
    def get_frame(self) -> Tuple[bool, Optional[cv2.typing.MatLike]]:
        """
        Get a frame from the camera
        
        Returns:
            tuple: (success, frame) where success is a boolean indicating if frame was captured
        """
        if not self.is_connected():
            return False, None
            
        try:
            ret, frame = self.cap.read()
            if not ret:
                return False, None
                
            # Flip horizontally if needed
            if self.flip_horizontal:
                frame = cv2.flip(frame, 1)  # 1 means horizontal flip
                
            # Apply any frame processors
            for processor in self._frame_processors:
                frame = processor(frame)
                
            return True, frame
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Error getting frame: {str(e)}")
            return False, None
            
    def add_frame_processor(self, processor: Callable[[cv2.typing.MatLike], cv2.typing.MatLike]):
        """
        Add a frame processor function that will be applied to each frame
        
        Args:
            processor: Function that takes a frame and returns a processed frame
        """
        self._frame_processors.append(processor)
        
    def remove_frame_processor(self, processor: Callable[[cv2.typing.MatLike], cv2.typing.MatLike]):
        """
        Remove a frame processor
        
        Args:
            processor: Function to remove
        """
        if processor in self._frame_processors:
            self._frame_processors.remove(processor)
            
    def clear_frame_processors(self):
        """Clear all frame processors"""
        self._frame_processors = []
        
    def get_camera_info(self) -> Dict:
        """
        Get information about the connected camera
        
        Returns:
            dict: Camera properties
        """
        if not self.is_connected():
            return {"status": "disconnected"}
            
        try:
            info = {
                "status": "connected",
                "id": self.camera_id,
                "resolution": (
                    int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                    int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                ),
                "fps": self.cap.get(cv2.CAP_PROP_FPS)
            }
            return info
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Error getting camera info: {str(e)}")
            return {"status": "error", "error": str(e)}
            
    def set_preferred_settings(self, camera_id=None, resolution=None, fps=None, flip=None):
        """
        Set preferred camera settings
        
        Args:
            camera_id (int, optional): Camera ID to use
            resolution (list, optional): [width, height]
            fps (int, optional): Frames per second
            flip (bool, optional): Whether to flip the image horizontally
            
        Returns:
            bool: True if settings were applied successfully
        """
        changes_made = False
        
        # Update camera ID if specified and different
        if camera_id is not None and camera_id != self.camera_id:
            self.camera_id = camera_id
            changes_made = True
        
        # Update resolution if specified and different
        if resolution is not None and resolution != self.resolution:
            self.resolution = tuple(resolution)
            changes_made = True
            
        # Update flip setting if specified and different
        if flip is not None and flip != self.flip_horizontal:
            self.flip_horizontal = flip
            changes_made = True
        
        # If we're connected and settings changed, reconnect to apply them
        if changes_made and self.is_connected():
            self.disconnect()
            self.connect()
            
            # Set FPS if specified
            if fps is not None and self.is_connected():
                try:
                    self.cap.set(cv2.CAP_PROP_FPS, fps)
                except Exception as e:
                    logger.warning(f"Could not set FPS to {fps}: {e}")
        
        return True
    
    def refresh_cameras(self):
        """Refresh the list of available cameras"""
        self._available_cameras = self._detect_cameras()
        return self._available_cameras
        
    def list_cameras(self) -> List[CameraInfo]:
        """
        List available cameras
        
        Returns:
            list: List of CameraInfo objects
        """
        if not self._available_cameras:
            self._available_cameras = self._detect_cameras()
        return self._available_cameras
            
    def _detect_cameras(self, max_cameras=10) -> List[CameraInfo]:
        """
        Detect available cameras
        
        Args:
            max_cameras (int): Maximum number of cameras to check
            
        Returns:
            list: List of CameraInfo objects
        """
        available_cameras = []
        
        # Try to detect cameras
        for i in range(max_cameras):
            try:
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    # Get camera info
                    camera = CameraInfo(i)
                    camera.is_available = True
                    camera.resolution = (
                        int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                        int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    )
                    camera.fps = int(cap.get(cv2.CAP_PROP_FPS))
                    
                    # Try to get camera name (unsupported on some systems)
                    try:
                        camera.name = f"Camera {i}"
                    except:
                        pass
                    
                    available_cameras.append(camera)
                    cap.release()
            except Exception as e:
                logger.debug(f"Error checking camera {i}: {str(e)}")
                
        return available_cameras
    
    def get_best_camera(self) -> CameraResult:
        """
        Get the best available camera
        
        Returns:
            CameraResult: Result of attempting to get the best camera
        """
        available_cameras = self.list_cameras()
        
        # If we have cameras, try to connect to the first one
        if available_cameras:
            camera = available_cameras[0]
            try:
                cap = cv2.VideoCapture(camera.index)
                if cap.isOpened():
                    return CameraResult(
                        success=True,
                        camera_id=camera.index,
                        camera=cap,
                        camera_info=str(camera),
                        width=camera.resolution[0],
                        height=camera.resolution[1],
                        fps=camera.fps
                    )
                else:
                    return CameraResult(
                        success=False,
                        error_message=f"Could not open camera {camera.index}"
                    )
            except Exception as e:
                return CameraResult(
                    success=False,
                    error_message=str(e)
                )
        else:
            # Try default camera as a fallback
            try:
                cap = cv2.VideoCapture(0)
                if cap.isOpened():
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    fps = int(cap.get(cv2.CAP_PROP_FPS))
                    return CameraResult(
                        success=True,
                        camera_id=0,
                        camera=cap,
                        camera_info=f"Default Camera (0)",
                        width=width,
                        height=height,
                        fps=fps
                    )
                else:
                    return CameraResult(
                        success=False,
                        error_message="No cameras available"
                    )
            except Exception as e:
                return CameraResult(
                    success=False,
                    error_message=f"Error connecting to default camera: {str(e)}"
                )
    
    def get_camera(self, camera_id) -> CameraResult:
        """
        Get a specific camera by ID
        
        Args:
            camera_id (int): Camera ID to connect to
            
        Returns:
            CameraResult: Result of attempting to get the camera
        """
        try:
            cap = cv2.VideoCapture(camera_id)
            if cap.isOpened():
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = int(cap.get(cv2.CAP_PROP_FPS))
                return CameraResult(
                    success=True,
                    camera_id=camera_id,
                    camera=cap,
                    camera_info=f"Camera {camera_id}",
                    width=width,
                    height=height,
                    fps=fps
                )
            else:
                return CameraResult(
                    success=False,
                    error_message=f"Could not open camera {camera_id}"
                )
        except Exception as e:
            return CameraResult(
                success=False,
                error_message=f"Error connecting to camera {camera_id}: {str(e)}"
            )
    
    def test_camera(self, camera_id=None, width=640, height=480, fps=30, flip=False) -> CameraResult:
        """
        Test camera with specific settings
        
        Args:
            camera_id (int, optional): Camera ID to test, or None to use current
            width (int, optional): Desired width
            height (int, optional): Desired height
            fps (int, optional): Desired FPS
            flip (bool, optional): Whether to flip the image horizontally
            
        Returns:
            CameraResult: Result of the camera test
        """
        # Use provided camera ID or fall back to current
        test_id = camera_id if camera_id is not None else self.camera_id
        
        try:
            # Open the camera
            cap = cv2.VideoCapture(test_id)
            if not cap.isOpened():
                return CameraResult(
                    success=False,
                    error_message=f"Could not open camera {test_id}"
                )
            
            # Set desired properties
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            cap.set(cv2.CAP_PROP_FPS, fps)
            
            # Try to get a frame to confirm it's working
            ret, frame = cap.read()
            if not ret:
                cap.release()
                return CameraResult(
                    success=False,
                    error_message=f"Could not read frame from camera {test_id}"
                )
            
            # Apply horizontal flip if requested
            if flip:
                frame = cv2.flip(frame, 1)
            
            # Get actual properties (may differ from requested)
            actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = int(cap.get(cv2.CAP_PROP_FPS))
            
            # Clean up
            cap.release()
            
            # Return success
            return CameraResult(
                success=True,
                camera_id=test_id,
                camera_info=f"Camera {test_id}",
                width=actual_width,
                height=actual_height,
                fps=actual_fps
            )
            
        except Exception as e:
            return CameraResult(
                success=False,
                error_message=f"Error testing camera {test_id}: {str(e)}"
            )
            
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()

class VideoDisplayWidget:
    """
    Class for displaying video in a tkinter widget
    """
    
    def __init__(self, label_widget, camera_manager=None, update_interval=33):
        """
        Initialize the video display widget
        
        Args:
            label_widget: Tkinter Label widget to display video
            camera_manager: Optional CameraManager instance
            update_interval: Frame update interval in milliseconds (default 33 ms ~= 30 fps)
        """
        self.label_widget = label_widget
        self.camera_manager = camera_manager
        self.update_interval = update_interval
        self.running = False
        self.after_id = None
        
    def set_camera_manager(self, camera_manager):
        """Set the camera manager instance"""
        self.camera_manager = camera_manager
        
    def start(self):
        """Start displaying video frames"""
        if self.camera_manager and not self.running:
            if not self.camera_manager.is_connected():
                self.camera_manager.connect()
                
            self.running = True
            self._update_frame()
            
    def stop(self):
        """Stop displaying video frames"""
        self.running = False
        if self.after_id:
            self.label_widget.after_cancel(self.after_id)
            self.after_id = None
            
    def _update_frame(self):
        """Update the frame in the widget"""
        if self.running and self.camera_manager:
            # Get a frame from the camera
            success, frame = self.camera_manager.get_frame()
            
            if success:
                try:
                    # Convert OpenCV BGR image to RGB for tkinter
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    
                    # Get widget dimensions
                    width = self.label_widget.winfo_width()
                    height = self.label_widget.winfo_height()
                    
                    # Resize the frame to fit the widget if needed
                    if width > 1 and height > 1:  # Ensure widget has been drawn
                        rgb_frame = cv2.resize(rgb_frame, (width, height))
                        
                    # Convert to PhotoImage format
                    from PIL import Image, ImageTk
                    image = Image.fromarray(rgb_frame)
                    photo_image = ImageTk.PhotoImage(image=image)
                    
                    # Update the label with the new image
                    self.label_widget.config(image=photo_image)
                    
                    # Keep a reference to prevent garbage collection
                    self.label_widget.image = photo_image
                except Exception as e:
                    logger.error(f"Error updating video frame: {str(e)}")
                    
            # Schedule the next update
            self.after_id = self.label_widget.after(self.update_interval, self._update_frame)
        
    def is_running(self):
        """Check if video display is running"""
        return self.running

def list_available_cameras(max_cameras=10) -> List[int]:
    """
    List available camera devices by testing connections
    
    Args:
        max_cameras: Maximum number of cameras to check
        
    Returns:
        list: List of available camera indices
    """
    available_cameras = []
    
    for i in range(max_cameras):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            available_cameras.append(i)
            cap.release()
    
    return available_cameras