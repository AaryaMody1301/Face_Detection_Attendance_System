"""
Command-line script for taking attendance using face recognition.
"""
import os
import cv2
import argparse
import datetime
import time
import pandas as pd
import logging
import numpy as np

from src.face_recognition.detector import FaceDetector
from src.database.db_handler import AttendanceDB

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def take_attendance(subject, model_path="TrainingImageLabel/Trainner.yml",
                  confidence_threshold=60, show_window=True, timeout=60):
    """
    Take attendance using face recognition.
    
    Args:
        subject (str): Subject name for the attendance record
        model_path (str): Path to the trained model
        confidence_threshold (int): Threshold for face recognition confidence
        show_window (bool): Whether to show the video window
        timeout (int): Timeout in seconds (0 for no timeout)
        
    Returns:
        str: Path to the attendance file
    """
    # Check if model exists
    if not os.path.isfile(model_path):
        logger.error(f"Model file {model_path} does not exist.")
        return None
    
    # Initialize components
    detector = FaceDetector()
    db = AttendanceDB()
    
    # Load the model
    if not detector.load_model(model_path):
        logger.error(f"Failed to load model from {model_path}.")
        return None
    
    # Create attendance record
    now = datetime.datetime.now()
    date = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H-%M-%S")
    attendance_file = db.create_attendance_record(subject, date, time_str)
    
    if not attendance_file:
        logger.error("Failed to create attendance record.")
        return None
    
    logger.info(f"Attendance file created: {attendance_file}")
    
    # Get student details
    students_df = db.get_student_details()
    
    if students_df.empty:
        logger.warning("No students found in database. Please register students first.")
    
    # Open video capture
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        logger.error("Failed to open video capture.")
        return None
    
    # Set camera properties for better quality
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)
    
    logger.info("Started capturing video. Press 'q' to stop.")
    
    # Dictionary to keep track of recognized students
    recognized_students = {}
    late_students = {}  # Dictionary to track students arriving late
    start_time = time.time()
    
    # Define late threshold (in seconds, e.g., 5 minutes = 300 seconds)
    late_threshold = 300  # Can be made configurable
    
    # Face recognition stabilizer to reduce false positives
    recognition_buffer = {}  # Format: {face_id: [sequence of confidences]}
    buffer_size = 5          # Number of consecutive frames needed for stable recognition
    min_recognized_frames = 3 # Minimum number of frames needed to consider recognition valid
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                logger.error("Failed to read frame from video capture.")
                break
            
            # Create a copy of the frame for display
            display_frame = frame.copy()
            
            # Detect faces
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = detector.detect_faces(gray)
            
            # Process each detected face
            for (x, y, w, h) in faces:
                # Draw rectangle around face
                cv2.rectangle(display_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                
                # Extract face region
                face_roi = gray[y:y+h, x:x+w]
                
                # Try to recognize the face
                face_id, conf = detector.recognizer.predict(face_roi)
                
                # Process recognition result
                if str(face_id) not in recognition_buffer:
                    recognition_buffer[str(face_id)] = []
                
                # Add current confidence to buffer (lower is better for OpenCV LBPH)
                if conf < 100:  # Only add reasonable confidences
                    recognition_buffer[str(face_id)].append(conf)
                    
                    # Limit buffer size
                    if len(recognition_buffer[str(face_id)]) > buffer_size:
                        recognition_buffer[str(face_id)] = recognition_buffer[str(face_id)][-buffer_size:]
                
                # Check if we have enough frames with good confidence for this face
                good_frames = sum(1 for c in recognition_buffer[str(face_id)] if c < confidence_threshold)
                
                # If we have enough good frames, mark attendance
                if good_frames >= min_recognized_frames:
                    # Find student name from ID
                    student_data = students_df[students_df['Enrollment'] == str(face_id)]
                    if not student_data.empty:
                        student_name = student_data.iloc[0]['Name']
                        
                        # Mark attendance if not already marked
                        student_key = f"{face_id}_{student_name}"
                        current_elapsed = time.time() - start_time
                        
                        if student_key not in recognized_students:
                            db.mark_attendance(str(face_id), student_name, file_path=attendance_file)
                            
                            # Check if student is late
                            if current_elapsed > late_threshold:
                                late_students[student_key] = True
                                logger.info(f"Marked LATE attendance for {student_name} (ID: {face_id})")
                            else:
                                logger.info(f"Marked attendance for {student_name} (ID: {face_id})")
                                
                            recognized_students[student_key] = True
                        
                        # Display name on frame
                        label = f"{student_name} ({face_id})"
                        if student_key in late_students:
                            label += " (LATE)"
                            color = (0, 0, 255)  # Red for late students
                        else:
                            color = (0, 255, 0)  # Green for good match
                    else:
                        # Unknown student ID
                        label = f"Unknown ID: {face_id}"
                        color = (0, 165, 255)  # Orange for unknown ID
                else:
                    # Not enough good frames yet
                    label = "Processing..."
                    if len(recognition_buffer[str(face_id)]) > 0:
                        avg_conf = sum(recognition_buffer[str(face_id)]) / len(recognition_buffer[str(face_id)])
                        label = f"Processing... ({good_frames}/{min_recognized_frames}, conf: {avg_conf:.1f})"
                    color = (255, 120, 0)  # Light blue for processing
                
                # Calculate position for label (handle if on top edge)
                y_pos = y - 10 if y - 10 > 10 else y + h + 20
                cv2.putText(display_frame, label, (x, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 
                          0.7, color, 2)
            
            # Display attendance count and subject on the frame
            attendance_count = len(recognized_students)
            attendance_text = f"Attendance Count: {attendance_count}"
            cv2.putText(display_frame, attendance_text, (10, 30),
                      cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            subject_text = f"Subject: {subject}"
            cv2.putText(display_frame, subject_text, (10, 60),
                      cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Display elapsed time
            elapsed_time = time.time() - start_time
            time_text = f"Time: {int(elapsed_time)}s"
            if timeout > 0:
                time_text = f"Time: {int(elapsed_time)}s / {timeout}s"
            cv2.putText(display_frame, time_text, (10, 90),
                      cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Display list of present students on the right side
            y_offset = 30
            cv2.putText(display_frame, "Students Present:", (display_frame.shape[1] - 250, y_offset),
                      cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
            y_offset += 30
            
            # Sort students alphabetically for consistent display
            present_students = sorted([key.split('_', 1)[1] for key in recognized_students.keys()])
            
            for i, student_name in enumerate(present_students):
                # Highlight late students in red
                student_key = next((k for k in recognized_students if k.split('_', 1)[1] == student_name), None)
                if student_key in late_students:
                    color = (0, 0, 255)  # Red for late
                    text = f"{i+1}. {student_name} (LATE)"
                else:
                    color = (0, 255, 0)  # Green for on time
                    text = f"{i+1}. {student_name}"
                
                cv2.putText(display_frame, text, (display_frame.shape[1] - 250, y_offset),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                y_offset += 25
                
                # Check if we're running out of vertical space
                if y_offset > display_frame.shape[0] - 10:
                    cv2.putText(display_frame, "... more", (display_frame.shape[1] - 250, y_offset),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                    break
            
            # Show frame
            if show_window:
                cv2.imshow("Attendance System", display_frame)
                
                # Check for 'q' key press to exit
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    logger.info("User pressed 'q' to exit.")
                    break
            
            # Check timeout
            if timeout > 0 and elapsed_time > timeout:
                logger.info(f"Timeout reached ({timeout} seconds).")
                break
    
    except KeyboardInterrupt:
        logger.info("Attendance taking interrupted by user.")
    except Exception as e:
        logger.error(f"Error taking attendance: {e}")
    finally:
        # Release resources
        cap.release()
        if show_window:
            cv2.destroyAllWindows()
    
    # Print summary
    logger.info("\nAttendance Summary:")
    logger.info(f"Subject: {subject}")
    logger.info(f"Date: {date}, Time: {time_str}")
    logger.info(f"Students present: {len(recognized_students)}")
    
    if recognized_students:
        logger.info("Students present:")
        for student_key in recognized_students:
            student_id, student_name = student_key.split("_", 1)
            status = "LATE" if student_key in late_students else "ON TIME"
            logger.info(f"  - {student_name} (ID: {student_id}) - {status}")
    else:
        logger.warning("No students were recognized during this session.")
    
    # Create auto-backup of the attendance file
    if recognized_students:
        _create_attendance_backup(attendance_file)
    
    return attendance_file


def _create_attendance_backup(attendance_file):
    """
    Create a backup of the attendance file.
    
    Args:
        attendance_file (str): Path to the attendance file
    """
    try:
        if os.path.exists(attendance_file):
            # Extract filename from path
            filename = os.path.basename(attendance_file)
            
            # Extract subject from filename
            subject = filename.split('_')[0]
            
            # Create backup directory if it doesn't exist
            backup_dir = os.path.join("backups", "attendance_backup", subject)
            os.makedirs(backup_dir, exist_ok=True)
            
            # Create backup file
            backup_file = os.path.join(backup_dir, filename)
            with open(attendance_file, 'r') as src, open(backup_file, 'w') as dst:
                dst.write(src.read())
                
            logger.info(f"Created backup of attendance file: {backup_file}")
            return True
    except Exception as e:
        logger.error(f"Error creating backup: {e}")
    return False


def main_with_args(args):
    """Run with parsed arguments from the main CLI."""
    attendance_file = take_attendance(
        args.subject, 
        args.model, 
        args.threshold, 
        not args.no_window, 
        args.timeout
    )
    return 0 if attendance_file else 1


def main():
    """Main entry point for the script when run directly."""
    parser = argparse.ArgumentParser(description="Take attendance using face recognition")
    parser.add_argument("subject", type=str, help="Subject name for the attendance record")
    parser.add_argument("--model", type=str, default="TrainingImageLabel/Trainner.yml",
                      help="Path to the trained model")
    parser.add_argument("--threshold", type=int, default=60,
                      help="Threshold for face recognition confidence")
    parser.add_argument("--no-window", action="store_true",
                      help="Don't show the video window")
    parser.add_argument("--timeout", type=int, default=60,
                      help="Timeout in seconds (0 for no timeout)")
    parser.add_argument("--late-threshold", type=int, default=300,
                      help="Seconds after which a student is marked as late (0 to disable)")
    
    args = parser.parse_args()
    
    return main_with_args(args)


if __name__ == "__main__":
    main()