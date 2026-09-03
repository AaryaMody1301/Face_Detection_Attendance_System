"""Derived exports for legacy modules that still consume student CSV files."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.core.database.service import DatabaseService


def export_legacy_student_csvs(database: DatabaseService) -> tuple[str, str]:
    """Regenerate historical student CSV shapes from SQLite.

    These files exist only as read-compatibility surfaces for legacy training and
    video modules. SQLite remains authoritative and all writes flow through the
    database service.
    """
    students = database.get_student_details()
    if students.empty:
        compatibility = pd.DataFrame(columns=["ID", "Name", "Course", "Year"])
    else:
        compatibility = pd.DataFrame(
            {
                "ID": students["Enrollment"].astype(str),
                "Name": students["Name"].astype(str),
                "Course": students["department"].fillna("").astype(str),
                "Year": students["year"].fillna("").astype(str),
            }
        )

    student_details_path = Path("StudentDetails") / "StudentDetails.csv"
    face_data_path = Path("data") / "students.csv"
    student_details_path.parent.mkdir(parents=True, exist_ok=True)
    face_data_path.parent.mkdir(parents=True, exist_ok=True)

    detailed = compatibility.copy()
    detailed["RegisteredDate"] = ""
    detailed.to_csv(student_details_path, index=False)
    compatibility.to_csv(face_data_path, index=False)
    return str(student_details_path), str(face_data_path)
