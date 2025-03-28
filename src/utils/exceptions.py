"""
Custom exceptions for the Face Detection Attendance System
"""

class BaseAppException(Exception):
    """Base exception class for the application"""
    
    def __init__(self, message="An error occurred in the application"):
        self.message = message
        super().__init__(self.message)


class DatabaseError(BaseAppException):
    """Exception raised for database errors"""
    
    def __init__(self, message="An error occurred while accessing the database"):
        self.message = message
        super().__init__(self.message)


class RecognitionError(BaseAppException):
    """Exception raised for face recognition errors"""
    
    def __init__(self, message="An error occurred during face recognition"):
        self.message = message
        super().__init__(self.message)


class ValidationError(BaseAppException):
    """Exception raised for data validation errors"""
    
    def __init__(self, message="Data validation failed"):
        self.message = message
        super().__init__(self.message)


class AuthenticationError(BaseAppException):
    """Exception raised for authentication errors"""
    
    def __init__(self, message="Authentication failed"):
        self.message = message
        super().__init__(self.message)


class ConfigurationError(BaseAppException):
    """Exception raised for configuration errors"""
    
    def __init__(self, message="Configuration error"):
        self.message = message
        super().__init__(self.message)


class FileOperationError(BaseAppException):
    """Exception raised for file operation errors"""
    
    def __init__(self, message="File operation failed"):
        self.message = message
        super().__init__(self.message)


class NetworkError(BaseAppException):
    """Exception raised for network-related errors"""
    
    def __init__(self, message="Network operation failed"):
        self.message = message
        super().__init__(self.message)


class ResourceNotFoundError(BaseAppException):
    """Exception raised when a required resource is not found"""
    
    def __init__(self, message="Required resource not found"):
        self.message = message
        super().__init__(self.message)