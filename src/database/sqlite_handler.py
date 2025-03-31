import sqlite3
import os

class SQLiteHandler:
    def __init__(self, db_path='attendance.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.create_tables()

    def create_tables(self):
        with self.conn:
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS students (
                    enrollment TEXT PRIMARY KEY,
                    name TEXT NOT NULL
                )
            ''')
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    enrollment TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    date TEXT NOT NULL,
                    time TEXT NOT NULL,
                    FOREIGN KEY (enrollment) REFERENCES students (enrollment)
                )
            ''')

    def add_student(self, enrollment, name):
        """
        Add a new student to the database
        
        Args:
            enrollment: Student enrollment ID
            name: Student name
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if student already exists
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM students WHERE enrollment = ?', (enrollment,))
            existing = cursor.fetchone()
            
            if existing:
                # Student already exists, check if we should update the name
                if existing[1] != name:
                    with self.conn:
                        self.conn.execute('UPDATE students SET name = ? WHERE enrollment = ?', (name, enrollment))
                return True  # Return success even if the student already exists
                
            # Add new student
            with self.conn:
                self.conn.execute('INSERT INTO students (enrollment, name) VALUES (?, ?)', (enrollment, name))
            return True
            
        except Exception as e:
            print(f"Error adding student: {e}")
            return False

    def get_student_details(self):
        """
        Get all student details from the database
        
        Returns:
            pandas.DataFrame: DataFrame containing student details
        """
        try:
            import pandas as pd
            
            with self.conn:
                cursor = self.conn.cursor()
                cursor.execute('SELECT enrollment, name FROM students')
                rows = cursor.fetchall()
                
                # Convert to DataFrame
                df = pd.DataFrame(rows, columns=['Enrollment', 'Name'])
                return df
                
        except ImportError:
            # If pandas is not available, return empty DataFrame-like object
            class EmptyDataFrame:
                def __init__(self):
                    self.empty = True
                    self.columns = ['Enrollment', 'Name']
                
            return EmptyDataFrame()
        except Exception as e:
            print(f"Error getting student details: {e}")
            # Return empty DataFrame
            import pandas as pd
            return pd.DataFrame(columns=['Enrollment', 'Name'])

    def mark_attendance(self, enrollment, name, subject, date, time):
        """
        Mark attendance for a student
        
        Args:
            enrollment: Student enrollment ID
            name: Student name
            subject: Subject name
            date: Date string
            time: Time string
            
        Returns:
            bool: Success or failure
        """
        try:
            with self.conn:
                self.conn.execute('INSERT INTO attendance (enrollment, subject, date, time) VALUES (?, ?, ?, ?)', 
                                 (enrollment, subject, date, time))
            return True
        except Exception as e:
            print(f"Error marking attendance: {e}")
            return False

    def get_attendance_records(self, subject=None, date=None):
        """
        Get attendance records filtered by subject and/or date
        
        Args:
            subject: Optional subject filter
            date: Optional date filter
            
        Returns:
            dict: Dictionary of DataFrames with filenames as keys
        """
        try:
            import pandas as pd
            import os
            
            # First check if there are CSV files in Attendance folder
            attendance_files = {}
            
            # Create the directory if it doesn't exist
            if not os.path.exists("Attendance"):
                os.makedirs("Attendance")
                
            # Look for CSV files
            for file in os.listdir("Attendance"):
                if file.endswith(".csv"):
                    # Only include files matching the subject if specified
                    if subject and subject not in file:
                        continue
                        
                    try:
                        # Read CSV into DataFrame
                        file_path = os.path.join("Attendance", file)
                        df = pd.read_csv(file_path)
                        
                        # Filter by date if specified
                        if date and 'Date' in df.columns:
                            df = df[df['Date'] == date]
                            
                        if not df.empty:
                            attendance_files[file] = df
                    except Exception as e:
                        print(f"Error reading file {file}: {e}")
            
            # If no files found, try getting from database
            if not attendance_files:
                query = 'SELECT a.enrollment, s.name, a.subject, a.date, a.time FROM attendance a ' \
                       'LEFT JOIN students s ON a.enrollment = s.enrollment'
                params = []
                
                # Add filters
                if subject:
                    query += ' WHERE a.subject = ?'
                    params.append(subject)
                    
                if date:
                    if 'WHERE' in query:
                        query += ' AND a.date = ?'
                    else:
                        query += ' WHERE a.date = ?'
                    params.append(date)
                    
                # Execute query
                with self.conn:
                    cursor = self.conn.cursor()
                    cursor.execute(query, params)
                    rows = cursor.fetchall()
                    
                    if rows:
                        # Group by subject and date
                        records = {}
                        for row in rows:
                            enrollment, name, subj, dt, tm = row
                            key = f"{subj}_{dt}"
                            
                            if key not in records:
                                records[key] = []
                                
                            records[key].append({
                                'Enrollment': enrollment,
                                'Name': name,
                                'Date': dt,
                                'Time': tm
                            })
                        
                        # Convert records to DataFrames
                        for key, data in records.items():
                            file_name = f"{key}.csv"
                            attendance_files[file_name] = pd.DataFrame(data)
            
            return attendance_files
            
        except ImportError:
            # If pandas is not available, return empty dict
            return {}
        except Exception as e:
            print(f"Error getting attendance records: {e}")
            return {}

    def create_attendance_record(self, subject, date, time_str):
        """
        Create a new attendance record file
        
        Args:
            subject: Subject name
            date: Date string
            time_str: Time string
            
        Returns:
            str: Path to the created attendance file or None if failed
        """
        try:
            # Create Attendance directory if it doesn't exist
            if not os.path.exists("Attendance"):
                os.makedirs("Attendance")
                
            # Create a file name with subject, date and time
            file_name = f"{subject}_{date}_{time_str.replace(':', '-')}.csv"
            file_path = os.path.join("Attendance", file_name)
            
            # Create file with header if it doesn't exist
            if not os.path.exists(file_path):
                with open(file_path, 'w', newline='') as f:
                    f.write("Enrollment,Name,Date,Time\n")
            
            return file_path
        except Exception as e:
            print(f"Error creating attendance record: {e}")
            return None

    def close(self):
        self.conn.close()