"""
Enhanced cleanup utility for Attendance and TrainingImage folders
"""
import os
import shutil
import glob
import re
import hashlib
import pandas as pd
from datetime import datetime
from collections import defaultdict

def cleanup_attendance_folder():
    """
    Clean up and organize the Attendance folder:
    1. Move all CSV files to their respective subject folders
    2. Remove duplicate attendance records
    3. Create a backup of all files
    """
    print("=== Cleaning up Attendance folder ===")
    
    if not os.path.isdir("Attendance"):
        print("Attendance folder not found")
        return False
    
    # Create Exports directory if it doesn't exist
    exports_dir = os.path.join("Attendance", "Exports")
    os.makedirs(exports_dir, exist_ok=True)
    
    # Create Backup directory
    backup_dir = os.path.join("Attendance", "Backup")
    os.makedirs(backup_dir, exist_ok=True)
    
    # Get all CSV files in the Attendance directory (not in subdirectories)
    csv_files = [f for f in os.listdir("Attendance") 
               if os.path.isfile(os.path.join("Attendance", f)) and f.lower().endswith('.csv')]
    
    if not csv_files:
        print("No CSV files found in the root Attendance directory")
        return False
    
    # Track file hashes to avoid duplicates
    file_hashes = {}
    duplicates = []
    subject_files = defaultdict(list)
    
    # Regular expression to extract subject name
    pattern = r'(?:Attendance|Manually\s+Attendance)\s*(.*?)(?:_\d{4}[-_]\d{2}[-_]\d{2}|\.csv)'
    
    # Process each CSV file
    for file in csv_files:
        src_path = os.path.join("Attendance", file)
        
        # Skip special directories
        if file in ["Exports", "Backup"] or os.path.isdir(src_path):
            continue
            
        # Backup the file first
        backup_path = os.path.join(backup_dir, file)
        if not os.path.exists(backup_path):
            shutil.copy2(src_path, backup_path)
            
        # Calculate file hash to detect duplicates
        with open(src_path, 'rb') as f:
            file_content = f.read()
            file_hash = hashlib.md5(file_content).hexdigest()
            
        # Check if duplicate
        if file_hash in file_hashes:
            duplicates.append((file, file_hashes[file_hash]))
            continue
        else:
            file_hashes[file_hash] = file
            
        # Extract subject from filename
        match = re.search(pattern, file)
        subject = match.group(1) if match else "Unknown"
        subject = subject.strip()
        
        # Add to subject files list
        subject_files[subject].append(file)
        
        # Create subject directory if it doesn't exist
        subject_dir = os.path.join("Attendance", subject)
        os.makedirs(subject_dir, exist_ok=True)
        
        # Move file to subject directory
        dst_path = os.path.join(subject_dir, file)
        if not os.path.exists(dst_path):
            try:
                shutil.copy2(src_path, dst_path)
                print(f"  Moved: {file} → {subject}/{file}")
            except Exception as e:
                print(f"  Error moving {file}: {e}")
    
    # Report duplicates
    if duplicates:
        print("\nDuplicate files detected:")
        for dup, orig in duplicates:
            print(f"  Duplicate: {dup} (same as {orig})")
        
        # Create a duplicates directory
        duplicates_dir = os.path.join("Attendance", "Duplicates")
        os.makedirs(duplicates_dir, exist_ok=True)
        
        # Move duplicates to the duplicates directory
        for dup, _ in duplicates:
            src_path = os.path.join("Attendance", dup)
            if os.path.exists(src_path):
                dst_path = os.path.join(duplicates_dir, dup)
                try:
                    shutil.move(src_path, dst_path)
                    print(f"  Moved duplicate: {dup} → Duplicates/{dup}")
                except Exception as e:
                    print(f"  Error moving duplicate {dup}: {e}")
    
    # Create consolidated attendance files per subject
    for subject, files in subject_files.items():
        if len(files) > 1:
            print(f"\nConsolidating {len(files)} files for subject '{subject}'")
            
            # Read and combine all attendance records
            dfs = []
            for file in files:
                try:
                    src_path = os.path.join("Attendance", file)
                    df = pd.read_csv(src_path)
                    dfs.append(df)
                except Exception as e:
                    print(f"  Error reading {file}: {e}")
            
            if dfs:
                # Combine all dataframes
                combined_df = pd.concat(dfs, ignore_index=True)
                
                # Remove duplicates
                original_count = len(combined_df)
                combined_df = combined_df.drop_duplicates()
                
                # Save consolidated file
                consolidated_filename = f"{subject}_Consolidated_{datetime.now().strftime('%Y%m%d')}.csv"
                export_path = os.path.join(exports_dir, consolidated_filename)
                
                combined_df.to_csv(export_path, index=False)
                
                print(f"  Created: {consolidated_filename} with {len(combined_df)} records")
                if original_count > len(combined_df):
                    print(f"  Removed {original_count - len(combined_df)} duplicate records")
    
    # Once all files are processed, delete the original CSV files from the root directory
    for file in csv_files:
        src_path = os.path.join("Attendance", file)
        if os.path.exists(src_path) and os.path.isfile(src_path):
            try:
                os.remove(src_path)
                print(f"  Deleted original: {file}")
            except Exception as e:
                print(f"  Error deleting {file}: {e}")
    
    print("\nAttendance folder cleanup completed")
    return True

def cleanup_training_images():
    """
    Clean up and organize TrainingImage folder:
    1. Move all images to student-specific folders in Organized
    2. Optimize student folders by keeping a reasonable number of images
    3. Remove low-quality or duplicate images
    """
    print("\n=== Cleaning up TrainingImage folder ===")
    
    if not os.path.isdir("TrainingImage"):
        print("TrainingImage folder not found")
        return False
    
    # Create Organized directory if it doesn't exist
    organized_dir = os.path.join("TrainingImage", "Organized")
    os.makedirs(organized_dir, exist_ok=True)
    
    # Create Backup directory
    backup_dir = os.path.join("TrainingImage", "Backup")
    os.makedirs(backup_dir, exist_ok=True)
    
    # Get all image files in the TrainingImage directory
    image_files = [f for f in os.listdir("TrainingImage") 
                 if os.path.isfile(os.path.join("TrainingImage", f)) and
                 f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    
    if not image_files:
        print("No image files found in the TrainingImage directory")
        return False
    
    # Track students and their images
    students = defaultdict(list)
    
    # Process each image file
    for file in image_files:
        # Skip if it's not in the correct format
        if not is_valid_training_filename(file):
            print(f"  Skipping invalid filename: {file}")
            continue
        
        # Extract student information
        parts = file.split('.')
        name = parts[0]
        student_id = parts[1]
        student_key = f"{name}_{student_id}"
        
        # Track this file with the student
        students[student_key].append(file)
        
        # Create student directory in Organized
        student_dir = os.path.join(organized_dir, student_key)
        os.makedirs(student_dir, exist_ok=True)
        
        # Copy file to backup
        src_path = os.path.join("TrainingImage", file)
        backup_path = os.path.join(backup_dir, file)
        
        if not os.path.exists(backup_path):
            try:
                shutil.copy2(src_path, backup_path)
            except Exception as e:
                print(f"  Error backing up {file}: {e}")
        
        # Copy file to organized directory
        dst_path = os.path.join(student_dir, file)
        if not os.path.exists(dst_path):
            try:
                shutil.copy2(src_path, dst_path)
                print(f"  Organized: {file} → Organized/{student_key}/{file}")
            except Exception as e:
                print(f"  Error organizing {file}: {e}")
    
    # Optimize student folders (limit to MAX_IMAGES per student)
    MAX_IMAGES = 25  # Set a reasonable maximum number of images per student
    
    print("\nOptimizing student training data:")
    for student_key, files in students.items():
        if len(files) > MAX_IMAGES:
            # Sort files by number to get a range of expressions/angles
            files.sort(key=lambda f: int(f.split('.')[-2]))
            
            # Select a subset of images that are well-distributed
            step = len(files) // MAX_IMAGES
            selected_files = files[::step][:MAX_IMAGES]  # Take every 'step' image, up to MAX_IMAGES
            
            # Identify files to move to a redundant folder
            redundant_files = [f for f in files if f not in selected_files]
            
            if redundant_files:
                # Create redundant directory
                redundant_dir = os.path.join(organized_dir, student_key, "Redundant")
                os.makedirs(redundant_dir, exist_ok=True)
                
                # Move redundant files
                for file in redundant_files:
                    src_path = os.path.join(organized_dir, student_key, file)
                    if os.path.exists(src_path):
                        dst_path = os.path.join(redundant_dir, file)
                        try:
                            shutil.move(src_path, dst_path)
                        except Exception as e:
                            print(f"  Error moving redundant file {file}: {e}")
                
                print(f"  Optimized {student_key}: Kept {len(selected_files)} images, moved {len(redundant_files)} to Redundant/")
            
    # Create an optimized dataset with selected images
    optimized_dir = os.path.join("TrainingImage", "Optimized")
    os.makedirs(optimized_dir, exist_ok=True)
    
    # Copy the selected images to the optimized directory
    for student_key in students.keys():
        student_dir = os.path.join(organized_dir, student_key)
        # Get files in the student directory (excluding the Redundant subdirectory)
        optimized_files = [f for f in os.listdir(student_dir) 
                         if os.path.isfile(os.path.join(student_dir, f)) and
                         f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        
        # Create student directory in optimized
        opt_student_dir = os.path.join(optimized_dir, student_key)
        os.makedirs(opt_student_dir, exist_ok=True)
        
        # Copy files to optimized directory
        for file in optimized_files:
            src_path = os.path.join(student_dir, file)
            dst_path = os.path.join(opt_student_dir, file)
            if not os.path.exists(dst_path):
                try:
                    shutil.copy2(src_path, dst_path)
                except Exception as e:
                    print(f"  Error copying to optimized directory {file}: {e}")
        
        print(f"  Created optimized dataset for {student_key} with {len(optimized_files)} images")
    
    # Once all files are processed and backed up, we can delete the originals from the root directory
    for file in image_files:
        src_path = os.path.join("TrainingImage", file)
        if os.path.exists(src_path) and os.path.isfile(src_path):
            try:
                os.remove(src_path)
                print(f"  Deleted original: {file}")
            except Exception as e:
                print(f"  Error deleting {file}: {e}")
    
    print("\nTrainingImage folder cleanup completed")
    return True

def is_valid_training_filename(filename):
    """Check if a filename matches the expected format for training images"""
    pattern = r'^[A-Za-z\s]+\.\d+\.\d+\.(jpg|jpeg|png)$'
    return bool(re.match(pattern, filename))

def main():
    """Main function to clean up attendance and training image folders"""
    print("===== Enhanced Folder Cleanup Utility =====")
    
    cleanup_attendance_folder()
    cleanup_training_images()
    
    print("\nEnhanced folder cleanup completed.")

if __name__ == "__main__":
    main() 