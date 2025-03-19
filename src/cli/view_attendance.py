"""
Command-line script for viewing attendance records.
"""
import os
import argparse
import pandas as pd
import logging
from tabulate import tabulate
from datetime import datetime

from src.database.db_handler import AttendanceDB

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def view_attendance(subject=None, date=None, export=None):
    """
    View attendance records.
    
    Args:
        subject (str, optional): Filter by subject
        date (str, optional): Filter by date (YYYY-MM-DD)
        export (bool, optional): Export to CSV file
        
    Returns:
        dict: Dictionary of attendance records
    """
    db = AttendanceDB()
    attendance_records = db.get_attendance_records(subject, date)
    
    if not attendance_records:
        logger.info("No attendance records found.")
        return None
    
    logger.info(f"Found {len(attendance_records)} attendance records.")
    
    # Display each attendance record
    for filename, df in attendance_records.items():
        logger.info(f"\n{'-' * 80}")
        logger.info(f"File: {filename}")
        logger.info(f"{'-' * 80}")
        
        if df.empty:
            logger.info("No attendance data found.")
            continue
        
        # Print the data
        print(tabulate(df, headers="keys", tablefmt="grid", showindex=False))
        
        # Calculate statistics
        student_count = len(df['Enrollment'].unique())
        logger.info(f"\nTotal Students: {student_count}")
        
        # Export if requested
        if export:
            export_dir = "Exports"
            os.makedirs(export_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_file = os.path.join(export_dir, f"{os.path.splitext(filename)[0]}_{timestamp}.csv")
            
            df.to_csv(export_file, index=False)
            logger.info(f"Exported to {export_file}")
    
    return attendance_records


def main_with_args(args):
    """Run with parsed arguments from the main CLI."""
    attendance_records = view_attendance(args.subject, args.date, args.export)
    return 0 if attendance_records else 1


def main():
    """Main entry point for the script when run directly."""
    parser = argparse.ArgumentParser(description="View attendance records")
    parser.add_argument("--subject", type=str, help="Filter by subject")
    parser.add_argument("--date", type=str, help="Filter by date (YYYY-MM-DD)")
    parser.add_argument("--export", action="store_true", help="Export to CSV file")
    
    args = parser.parse_args()
    
    return main_with_args(args)


if __name__ == "__main__":
    main() 