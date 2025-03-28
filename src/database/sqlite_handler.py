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
        with self.conn:
            self.conn.execute('INSERT INTO students (enrollment, name) VALUES (?, ?)', (enrollment, name))

    def get_student_details(self):
        with self.conn:
            return self.conn.execute('SELECT * FROM students').fetchall()

    def mark_attendance(self, enrollment, subject, date, time):
        with self.conn:
            self.conn.execute('INSERT INTO attendance (enrollment, subject, date, time) VALUES (?, ?, ?, ?)', (enrollment, subject, date, time))

    def get_attendance_records(self, subject=None, date=None):
        query = 'SELECT * FROM attendance'
        params = []
        if subject:
            query += ' WHERE subject = ?'
            params.append(subject)
        if date:
            query += ' AND date = ?' if 'WHERE' in query else ' WHERE date = ?'
            params.append(date)
        with self.conn:
            return self.conn.execute(query, params).fetchall()

    def close(self):
        self.conn.close()