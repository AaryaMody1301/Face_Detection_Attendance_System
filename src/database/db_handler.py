"""
Database handler for storing and retrieving attendance data
"""
import os
import csv
import datetime
import pandas as pd
import shutil


class AttendanceDB:
    """
    Class for handling attendance database operations
    """
    
    def __init__(self, base_dir="./"):
        """
        Initialize the database handler
        
        Args:
            base_dir (str): Base directory for database storage
        """
        self.base_dir = base_dir
        self.student_details_dir = os.path.join(base_dir, "StudentDetails")
        self.attendance_dir = os.path.join(base_dir, "Attendance")
        
        # Create directories if they don't exist
        for directory in [self.student_details_dir, self.attendance_dir]:
            os.makedirs(directory, exist_ok=True)
    
    def get_student_details(self):
        """
        Get student details from the database
        
        Returns:
            pandas.DataFrame: DataFrame containing student details
        """
        student_details_file = os.path.join(self.student_details_dir, "StudentDetails.csv")
        
        if not os.path.isfile(student_details_file):
            # Create a new file with headers if it doesn't exist
            with open(student_details_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Enrollment', 'Name', 'Date', 'Time'])
            return pd.DataFrame(columns=['Enrollment', 'Name', 'Date', 'Time'])
        
        return pd.read_csv(student_details_file)
    
    def add_student(self, enrollment, name):
        """
        Add a new student to the database
        
        Args:
            enrollment (str): Student enrollment number
            name (str): Student name
            
        Returns:
            bool: True if student was added successfully
        """
        student_details_file = os.path.join(self.student_details_dir, "StudentDetails.csv")
        
        # Get current timestamp
        now = datetime.datetime.now()
        date = now.strftime("%Y-%m-%d")
        time = now.strftime("%H:%M:%S")
        
        # Check if the file exists
        file_exists = os.path.isfile(student_details_file)
        
        try:
            with open(student_details_file, 'a', newline='') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(['Enrollment', 'Name', 'Date', 'Time'])
                writer.writerow([enrollment, name, date, time])
            return True
        except Exception as e:
            print(f"Error adding student: {e}")
            return False
    
    def create_attendance_record(self, subject, date=None, time=None):
        """
        Create a new attendance record
        
        Args:
            subject (str): Subject name
            date (str, optional): Date in YYYY-MM-DD format
            time (str, optional): Time in HH-MM-SS format
            
        Returns:
            str: Path to the created attendance file
        """
        if date is None or time is None:
            now = datetime.datetime.now()
            date = now.strftime("%Y-%m-%d")
            time = now.strftime("%H-%M-%S")
        
        filename = f"{subject}_{date}_{time}.csv"
        file_path = os.path.join(self.attendance_dir, filename)
        
        try:
            with open(file_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Enrollment', 'Name', 'Date', 'Time', 'Status'])
            return file_path
        except Exception as e:
            print(f"Error creating attendance record: {e}")
            return None
    
    def mark_attendance(self, enrollment, name, subject=None, date=None, time=None, file_path=None, status="Present"):
        """
        Mark attendance for a student
        
        Args:
            enrollment (str): Student enrollment number
            name (str): Student name
            subject (str, optional): Subject name
            date (str, optional): Date in YYYY-MM-DD format
            time (str, optional): Time in HH-MM-SS format
            file_path (str, optional): Path to attendance file
            status (str, optional): Attendance status (Present, Late, etc.)
            
        Returns:
            bool: True if attendance was marked successfully
        """
        if file_path is None:
            if subject is None:
                return False
                
            if date is None or time is None:
                now = datetime.datetime.now()
                date = now.strftime("%Y-%m-%d")
                time = now.strftime("%H-%M-%S")
            
            filename = f"{subject}_{date}_{time}.csv"
            file_path = os.path.join(self.attendance_dir, filename)
        
        # Get current timestamp if not provided
        now = datetime.datetime.now()
        if date is None:
            date = now.strftime("%Y-%m-%d")
        if time is None:
            time = now.strftime("%H:%M:%S")
        
        try:
            # Check if the file exists
            file_exists = os.path.isfile(file_path)
            
            with open(file_path, 'a', newline='') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(['Enrollment', 'Name', 'Date', 'Time', 'Status'])
                writer.writerow([enrollment, name, date, time, status])
            return True
        except Exception as e:
            print(f"Error marking attendance: {e}")
            return False
    
    def get_attendance_records(self, subject=None, date=None):
        """
        Get attendance records
        
        Args:
            subject (str, optional): Filter by subject
            date (str, optional): Filter by date
            
        Returns:
            dict: Dictionary of attendance records
        """
        attendance_files = os.listdir(self.attendance_dir)
        attendance_records = {}
        
        for file in attendance_files:
            if file.endswith('.csv'):
                file_path = os.path.join(self.attendance_dir, file)
                try:
                    # Filter by subject and date if provided
                    if subject is not None and subject not in file:
                        continue
                    if date is not None and date not in file:
                        continue
                        
                    attendance_records[file] = pd.read_csv(file_path)
                except Exception as e:
                    print(f"Error reading {file}: {e}")
        
        return attendance_records
        
    def get_attendance_record(self, file_path):
        """
        Get a specific attendance record
        
        Args:
            file_path (str): Path to attendance file
            
        Returns:
            pandas.DataFrame: DataFrame containing attendance record
        """
        try:
            if os.path.isfile(file_path):
                return pd.read_csv(file_path)
            return None
        except Exception as e:
            print(f"Error reading attendance record: {e}")
            return None
            
    def update_attendance_record(self, file_path, attendance_df):
        """
        Update the attendance record with the provided DataFrame
        
        Args:
            file_path (str): Path to attendance file
            attendance_df (pandas.DataFrame): DataFrame containing updated attendance record
            
        Returns:
            bool: True if attendance record was updated successfully
        """
        try:
            # Create backup of original file
            backup_file = file_path + '.bak'
            if os.path.isfile(file_path):
                shutil.copy2(file_path, backup_file)
                
            # Write updated DataFrame to file
            attendance_df.to_csv(file_path, index=False)
            return True
        except Exception as e:
            print(f"Error updating attendance record: {e}")
            # Try to restore from backup if update failed
            if os.path.isfile(backup_file):
                shutil.copy2(backup_file, file_path)
            return False
            
    def add_student_to_attendance(self, file_path, enrollment, name, status="Present"):
        """
        Add a student to an existing attendance record
        
        Args:
            file_path (str): Path to attendance file
            enrollment (str): Student enrollment number
            name (str): Student name
            status (str): Attendance status
            
        Returns:
            bool: True if student was added successfully
        """
        # Get current timestamp
        now = datetime.datetime.now()
        date = now.strftime("%Y-%m-%d")
        time = now.strftime("%H:%M:%S")
        
        return self.mark_attendance(enrollment, name, file_path=file_path, 
                                   date=date, time=time, status=status)
                                   
    def remove_student_from_attendance(self, file_path, enrollment):
        """
        Remove a student from an attendance record
        
        Args:
            file_path (str): Path to attendance file
            enrollment (str): Student enrollment number
            
        Returns:
            bool: True if student was removed successfully
        """
        try:
            # Read existing attendance record
            attendance_df = self.get_attendance_record(file_path)
            if attendance_df is None:
                return False
                
            # Filter out the student
            updated_df = attendance_df[attendance_df['Enrollment'] != enrollment]
            
            # Update the file
            return self.update_attendance_record(file_path, updated_df)
        except Exception as e:
            print(f"Error removing student from attendance: {e}")
            return False
            
    def update_student_status(self, file_path, enrollment, status):
        """
        Update a student's attendance status
        
        Args:
            file_path (str): Path to attendance file
            enrollment (str): Student enrollment number
            status (str): New attendance status
            
        Returns:
            bool: True if status was updated successfully
        """
        try:
            # Read existing attendance record
            attendance_df = self.get_attendance_record(file_path)
            if attendance_df is None:
                return False
                
            # Check if the student exists
            if 'Status' not in attendance_df.columns:
                attendance_df['Status'] = 'Present'
                
            # Update the status
            attendance_df.loc[attendance_df['Enrollment'] == enrollment, 'Status'] = status
            
            # Update the file
            return self.update_attendance_record(file_path, attendance_df)
        except Exception as e:
            print(f"Error updating student status: {e}")
            return False