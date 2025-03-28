"""
Base controller class for the Face Detection Attendance System
"""
import logging
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='logs/app.log'
)

class BaseController:
    """
    Base controller class that defines the interface for all controllers
    
    Attributes:
        logger: Logger instance for this controller
        model_instance: Associated model instance
    """
    
    def __init__(self):
        """Initialize the base controller"""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.model_instance = None
    
    def initialize(self) -> bool:
        """
        Initialize the controller with necessary resources
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            self.logger.info(f"Initializing {self.__class__.__name__}")
            return True
        except Exception as e:
            self.logger.error(f"Error initializing {self.__class__.__name__}: {e}")
            return False
    
    def cleanup(self) -> bool:
        """
        Clean up resources used by the controller
        
        Returns:
            bool: True if cleanup successful, False otherwise
        """
        try:
            self.logger.info(f"Cleaning up {self.__class__.__name__}")
            return True
        except Exception as e:
            self.logger.error(f"Error cleaning up {self.__class__.__name__}: {e}")
            return False
    
    def handle_exception(self, exception: Exception, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Handle exceptions in a standardized way
        
        Args:
            exception: The exception to handle
            context: Additional context for the exception
            
        Returns:
            Dict containing error information
        """
        error_type = type(exception).__name__
        error_message = str(exception)
        
        # Log the error with context
        if context:
            self.logger.error(
                f"Error in {self.__class__.__name__}: {error_type}: {error_message} - Context: {context}"
            )
        else:
            self.logger.error(f"Error in {self.__class__.__name__}: {error_type}: {error_message}")
        
        # Return standardized error response
        return {
            "success": False,
            "error": {
                "type": error_type,
                "message": error_message,
                "context": context
            }
        }