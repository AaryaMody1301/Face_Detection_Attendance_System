"""
Custom exceptions for the Face Detection Attendance System

This module defines custom exceptions used throughout the application
for better error handling and debugging.
"""

class BaseException(Exception):
    """Base exception class for all custom exceptions"""
    def __init__(self, message="An error occurred", code=None, data=None):
        self.message = message
        self.code = code
        self.data = data or {}
        super().__init__(self.message)
    
    def to_dict(self):
        """Convert exception to dictionary for JSON response"""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "code": self.code,
            "data": self.data
        }


# Database Exceptions
class DatabaseError(BaseException):
    """Exception raised for database errors"""
    def __init__(self, message="Database operation failed", code="DB_ERROR", data=None):
        super().__init__(message, code, data)


class ConnectionPoolError(DatabaseError):
    """Exception raised for connection pool errors"""
    def __init__(self, message="Connection pool error", code="DB_CONN_POOL_ERROR", data=None):
        super().__init__(message, code, data)


class ValidationError(BaseException):
    """Exception raised for validation errors"""
    def __init__(self, message="Validation failed", code="VALIDATION_ERROR", data=None):
        super().__init__(message, code, data)


# Authentication Exceptions
class AuthenticationError(BaseException):
    """Exception raised for authentication errors"""
    def __init__(self, message="Authentication failed", code="AUTH_ERROR", data=None):
        super().__init__(message, code, data)


class AuthorizationError(BaseException):
    """Exception raised for authorization errors"""
    def __init__(self, message="Not authorized", code="AUTH_FORBIDDEN", data=None):
        super().__init__(message, code, data)


# Configuration Exceptions
class ConfigError(BaseException):
    """Exception raised for configuration errors"""
    def __init__(self, message="Configuration error", code="CONFIG_ERROR", data=None):
        super().__init__(message, code, data)


# Face Recognition Exceptions
class ImageProcessingError(BaseException):
    """Exception raised for image processing errors"""
    def __init__(self, message="Image processing failed", code="IMG_PROC_ERROR", data=None):
        super().__init__(message, code, data)


class RecognitionError(BaseException):
    """Exception raised for face recognition errors"""
    def __init__(self, message="Face recognition failed", code="RECOGNITION_ERROR", data=None):
        super().__init__(message, code, data)


class ModelError(BaseException):
    """Exception raised for model-related errors"""
    def __init__(self, message="Model error", code="MODEL_ERROR", data=None):
        super().__init__(message, code, data)


# File Operation Exceptions
class FileOperationError(BaseException):
    """Exception raised for file operation errors"""
    def __init__(self, message="File operation failed", code="FILE_ERROR", data=None):
        super().__init__(message, code, data)


class ImportExportError(BaseException):
    """Exception raised for import/export errors"""
    def __init__(self, message="Import/export operation failed", code="IMPORT_EXPORT_ERROR", data=None):
        super().__init__(message, code, data)


# Network Exceptions
class NetworkError(BaseException):
    """Exception raised for network-related errors"""
    def __init__(self, message="Network error", code="NETWORK_ERROR", data=None):
        super().__init__(message, code, data)


class APIError(BaseException):
    """Exception raised for API-related errors"""
    def __init__(self, message="API error", code="API_ERROR", data=None):
        super().__init__(message, code, data)


# UI Exceptions
class UIError(BaseException):
    """Exception raised for UI-related errors"""
    def __init__(self, message="UI error", code="UI_ERROR", data=None):
        super().__init__(message, code, data)


# Application Exceptions
class ApplicationError(BaseException):
    """Exception raised for general application errors"""
    def __init__(self, message="Application error", code="APP_ERROR", data=None):
        super().__init__(message, code, data)


class NotFoundError(BaseException):
    """Exception raised for resource not found errors"""
    def __init__(self, message="Resource not found", code="NOT_FOUND", data=None):
        super().__init__(message, code, data)


class ConflictError(BaseException):
    """Exception raised for conflict errors"""
    def __init__(self, message="Resource conflict", code="CONFLICT", data=None):
        super().__init__(message, code, data)


class TimeoutError(BaseException):
    """Exception raised for timeout errors"""
    def __init__(self, message="Operation timed out", code="TIMEOUT", data=None):
        super().__init__(message, code, data)
