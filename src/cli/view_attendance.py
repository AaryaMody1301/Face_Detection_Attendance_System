"""View SQLite-backed attendance records from the command line."""
from __future__ import annotations

import argparse
import logging
from datetime import UTC, datetime
from pathlib import Path

from src.core.paths import ATTENDANCE_EXPORTS_DIR
from src.database.db_handler import AttendanceDB

logger = logging.getLogger(__name__)


def view_attendance(subject: str | None = None, date: str | None = None, export: bool = False):
    db = AttendanceDB()
    try:
        attendance_records = db.get_attendance_records(subject=subject, date=date)
        if not attendance_records:
            logger.info("No attendance records found")
            return None

        for filename, dataframe in attendance_records.items():
            print(f"\n{'-' * 80}\n{filename}\n{'-' * 80}")
            print(dataframe.to_string(index=False))
            print(f"\nTotal Students: {dataframe['Enrollment'].nunique()}")

            if export:
                timestamp = datetime.now(UTC).astimezone().strftime("%Y%m%d_%H%M%S")
                destination = ATTENDANCE_EXPORTS_DIR / "cli" / f"{Path(filename).stem}_{timestamp}.csv"
                destination.parent.mkdir(parents=True, exist_ok=True)
                dataframe.to_csv(destination, index=False)
                print(f"Exported: {destination}")
        return attendance_records
    finally:
        db.close()


def main_with_args(args: argparse.Namespace) -> int:
    records = view_attendance(args.subject, args.date, args.export)
    return 0 if records else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="View attendance records")
    parser.add_argument("--subject", help="Filter by subject")
    parser.add_argument("--date", help="Filter by date (YYYY-MM-DD)")
    parser.add_argument("--export", action="store_true", help="Export matching rows to CSV")
    return main_with_args(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
