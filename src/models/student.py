"""
Student model for representing student data
"""

class Student:
    """
    Class representing a student
    """
    
    def __init__(self, enrollment_id, name, images=None):
        """
        Initialize a student with an ID and name
        
        Args:
            enrollment_id (str): Student enrollment ID
            name (str): Student name
            images (list, optional): List of image paths for the student
        """
        self.enrollment_id = enrollment_id
        self.name = name
        self.images = images or []
    
    def add_image(self, image_path):
        """
        Add an image for the student
        
        Args:
            image_path (str): Path to the image
            
        Returns:
            bool: True if the image was added successfully
        """
        if image_path not in self.images:
            self.images.append(image_path)
            return True
        return False
    
    def get_images(self):
        """
        Get all images for the student
        
        Returns:
            list: List of image paths
        """
        return self.images
    
    def to_dict(self):
        """
        Convert student to dictionary
        
        Returns:
            dict: Dictionary representation of the student
        """
        return {
            'enrollment_id': self.enrollment_id,
            'name': self.name,
            'images': self.images
        }
    
    @classmethod
    def from_dict(cls, data):
        """
        Create a student from a dictionary
        
        Args:
            data (dict): Dictionary containing student data
            
        Returns:
            Student: Student object
        """
        return cls(
            enrollment_id=data.get('enrollment_id'),
            name=data.get('name'),
            images=data.get('images', [])
        ) 