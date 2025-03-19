"""
Tests for the database handler module.
"""
import os
import pytest
import tempfile
import pandas as pd
from datetime import datetime
from src.database.db_handler import AttendanceDB


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db = AttendanceDB(base_dir=temp_dir)
        yield db


def test_db_initialization(temp_db):
    """Test that the database can be initialized."""
    assert temp_db is not None
    assert os.path.exists(temp_db.student_details_dir)
    assert os.path.exists(temp_db.attendance_dir)


def test_get_student_details_empty(temp_db):
    """Test getting student details from an empty database."""
    df = temp_db.get_student_details()
    assert isinstance(df, pd.DataFrame)
    assert df.empty


def test_add_student(temp_db):
    """Test adding a student to the database."""
    success = temp_db.add_student("123", "Test Student")
    assert success
    
    # Verify that the student was added
    df = temp_db.get_student_details()
    assert not df.empty
    assert "123" in df["Enrollment"].values
    assert "Test Student" in df["Name"].values


def test_create_attendance_record(temp_db):
    """Test creating an attendance record."""
    subject = "TestSubject"
    date = datetime.now().strftime("%Y-%m-%d")
    time = datetime.now().strftime("%H-%M-%S")
    
    file_path = temp_db.create_attendance_record(subject, date, time)
    assert file_path is not None
    assert os.path.exists(file_path)
    
    # Verify that the file is a CSV with the correct header
    df = pd.read_csv(file_path)
    assert list(df.columns) == ["Enrollment", "Name", "Date", "Time"]


def test_mark_attendance(temp_db):
    """Test marking attendance."""
    # Add a student
    temp_db.add_student("123", "Test Student")
    
    # Create an attendance record
    subject = "TestSubject"
    date = datetime.now().strftime("%Y-%m-%d")
    time = datetime.now().strftime("%H-%M-%S")
    file_path = temp_db.create_attendance_record(subject, date, time)
    
    # Mark attendance
    success = temp_db.mark_attendance(
        "123", "Test Student", file_path=file_path
    )
    assert success
    
    # Verify that attendance was marked
    df = pd.read_csv(file_path)
    assert not df.empty
    assert "123" in df["Enrollment"].values
    assert "Test Student" in df["Name"].values 