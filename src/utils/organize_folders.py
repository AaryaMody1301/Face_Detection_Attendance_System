"""
Utility script to organize training images and attendance records
"""
import os
import shutil
import re
import pandas as pd
from datetime import datetime

def organize_training_images():
    """
    Organize training images into student-specific folders
    """
    print("Organizing training images...")
    
    # Check if the training directory exists
    if not os.path.isdir("TrainingImage"):
        print("TrainingImage directory not found.")
        return False
    
    # Get all image files
    image_files = [f for f in os.listdir("TrainingImage") 
                  if os.path.isfile(os.path.join("TrainingImage", f)) and
                  f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    
    if not image_files:
        print("No training images found.")
        return False
    
    # Create organized directory if it doesn't exist
    organized_dir = os.path.join("TrainingImage", "Organized")
    os.makedirs(organized_dir, exist_ok=True)
    
    # Dictionary to track students
    students = {}
    
    # Process each image file
    for file in image_files:
        # Skip if already in Organized directory
        if "Organized" in file:
            continue
            
        # Extract information from filename (format: Name.ID.sequence.jpg)
        parts = file.split('.')
        if len(parts) >= 3:
            try:
                name = parts[0]
                student_id = parts[1]
                
                # Create student directory if it doesn't exist
                student_dir = os.path.join(organized_dir, f"{name}_{student_id}")
                os.makedirs(student_dir, exist_ok=True)
                
                # Copy the file to the student directory
                src_path = os.path.join("TrainingImage", file)
                dst_path = os.path.join(student_dir, file)
                
                # Skip if destination file already exists
                if not os.path.exists(dst_path):
                    shutil.copy2(src_path, dst_path)
                
                # Track student
                if student_id not in students:
                    students[student_id] = {
                        'name': name,
                        'image_count': 0
                    }
                students[student_id]['image_count'] += 1
                
            except Exception as e:
                print(f"Error processing {file}: {e}")
        else:
            print(f"Invalid filename format: {file}")
    
    # Print summary
    print("\nTraining Images Organization Summary:")
    print(f"Total students: {len(students)}")
    for student_id, info in students.items():
        print(f"  {info['name']} (ID: {student_id}): {info['image_count']} images")
    
    return True

def organize_attendance_records():
    """
    Organize attendance records by subject and date
    """
    print("\nOrganizing attendance records...")
    
    # Check if the attendance directory exists
    if not os.path.isdir("Attendance"):
        print("Attendance directory not found.")
        return False
    
    # Get all CSV files
    csv_files = [f for f in os.listdir("Attendance") 
                if os.path.isfile(os.path.join("Attendance", f)) and
                f.lower().endswith('.csv')]
    
    if not csv_files:
        print("No attendance records found.")
        return False
    
    # Ensure exports directory exists
    exports_dir = os.path.join("Attendance", "Exports")
    os.makedirs(exports_dir, exist_ok=True)
    
    # Dictionary to track subjects
    subjects = {}
    
    # Regular expression to extract subject name and date
    pattern = r'(?:Attendance|Manually\s+Attendance)\s*(.*?)(?:_\d{4}[-_]\d{2}[-_]\d{2}|\.csv)'
    
    # Process each CSV file
    for file in csv_files:
        # Skip if in Exports directory
        if "Exports" in file:
            continue
            
        try:
            # Extract subject from filename
            match = re.search(pattern, file)
            subject = match.group(1) if match else "Unknown"
            
            # Create subject directory
            subject_dir = os.path.join("Attendance", subject.strip())
            os.makedirs(subject_dir, exist_ok=True)
            
            # Copy the file to the subject directory
            src_path = os.path.join("Attendance", file)
            dst_path = os.path.join(subject_dir, file)
            
            # Skip if destination file already exists
            if not os.path.exists(dst_path):
                shutil.copy2(src_path, dst_path)
            
            # Track subject
            if subject not in subjects:
                subjects[subject] = {
                    'record_count': 0,
                    'student_count': 0
                }
            subjects[subject]['record_count'] += 1
            
            # Try to read the attendance record to count students
            try:
                df = pd.read_csv(src_path)
                subjects[subject]['student_count'] = max(
                    subjects[subject]['student_count'], 
                    len(df['Enrollment'].unique()) if 'Enrollment' in df.columns else 0
                )
            except Exception as e:
                print(f"Error reading {file}: {e}")
            
        except Exception as e:
            print(f"Error processing {file}: {e}")
    
    # Print summary
    print("\nAttendance Records Organization Summary:")
    print(f"Total subjects: {len(subjects)}")
    for subject, info in subjects.items():
        print(f"  {subject}: {info['record_count']} records, {info['student_count']} students")
    
    return True

def main():
    """Main function"""
    print("===== Folder Organization Utility =====")
    organize_training_images()
    organize_attendance_records()
    print("\nFolder organization completed.")

if __name__ == "__main__":
    main() 