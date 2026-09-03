"""Command-line attendance using the canonical YuNet + SFace engine."""
from __future__ import annotations

import argparse
import logging
import shutil
import time
from datetime import UTC, datetime
from pathlib import Path

import cv2

from src.core.face_engine import DEFAULT_GALLERY_PATH, SFACE_COSINE_THRESHOLD
from src.core.face_models import ModelUnavailableError
from src.database.db_handler import AttendanceDB
from src.face_recognition.detector import FaceDetector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _local_now() -> datetime:
    return datetime.now(UTC).astimezone()


def take_attendance(
    subject: str,
    model_path: str | Path = DEFAULT_GALLERY_PATH,
    confidence_threshold: float = SFACE_COSINE_THRESHOLD,
    show_window: bool = True,
    timeout: int = 60,
    late_threshold: int = 300,
) -> str | None:
    """Recognize students from the default camera and mark attendance."""
    detector = FaceDetector(confidence_threshold=confidence_threshold)
    db = AttendanceDB()
    model = Path(model_path)

    try:
        if not detector.load_model(model):
            logger.error(
                "SFace gallery %s is unavailable or incompatible. Train the Phase-3 gallery first.",
                model,
            )
            return None

        now = _local_now()
        date = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H-%M-%S")
        attendance_file = db.create_attendance_record(subject, date, time_str)
        if not attendance_file:
            logger.error("Failed to create attendance record")
            return None

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            logger.error("Failed to open video capture")
            return None
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)

        recognized_students: dict[str, str] = {}
        late_students: set[str] = set()
        recognition_buffer: dict[str, list[float]] = {}
        buffer_size = 5
        min_recognized_frames = 3
        start_time = time.monotonic()

        logger.info("Started SFace attendance capture. Press 'q' to stop.")
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    logger.error("Failed to read frame from video capture")
                    break

                display_frame = frame.copy()
                results = detector.recognize_faces(
                    frame,
                    confidence_threshold=confidence_threshold,
                )

                for location, name, student_id, score in results:
                    top, right, bottom, left = location
                    recognized = name != "Unknown" and bool(student_id)
                    color = (0, 255, 0) if recognized else (0, 165, 255)
                    label = "Unknown"

                    if recognized:
                        scores = recognition_buffer.setdefault(student_id, [])
                        scores.append(float(score))
                        del scores[:-buffer_size]
                        good_frames = sum(
                            value >= confidence_threshold for value in scores
                        )

                        if good_frames >= min_recognized_frames:
                            elapsed = time.monotonic() - start_time
                            status = (
                                "Late"
                                if late_threshold > 0 and elapsed > late_threshold
                                else "Present"
                            )
                            if student_id not in recognized_students:
                                db.mark_attendance(
                                    student_id,
                                    name,
                                    subject=subject,
                                    date=date,
                                    time=_local_now().strftime("%H:%M:%S"),
                                    file_path=attendance_file,
                                    status=status,
                                    method="sface",
                                )
                                recognized_students[student_id] = name
                                if status == "Late":
                                    late_students.add(student_id)
                                logger.info(
                                    "Marked %s attendance for %s (%s), cosine=%.3f",
                                    status.upper(),
                                    name,
                                    student_id,
                                    score,
                                )
                            label = f"{name} ({student_id}) {score:.3f}"
                            if student_id in late_students:
                                label += " LATE"
                                color = (0, 0, 255)
                        else:
                            label = (
                                f"Confirming {name} "
                                f"({good_frames}/{min_recognized_frames}, {score:.3f})"
                            )

                    cv2.rectangle(display_frame, (left, top), (right, bottom), color, 2)
                    y_pos = top - 10 if top > 20 else bottom + 20
                    cv2.putText(
                        display_frame,
                        label,
                        (left, y_pos),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        color,
                        2,
                    )

                elapsed = time.monotonic() - start_time
                cv2.putText(
                    display_frame,
                    f"Attendance Count: {len(recognized_students)}",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 0, 255),
                    2,
                )
                cv2.putText(
                    display_frame,
                    f"Subject: {subject}",
                    (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 0, 255),
                    2,
                )

                if show_window:
                    cv2.imshow("Attendance System - YuNet + SFace", display_frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
                if timeout > 0 and elapsed > timeout:
                    logger.info("Timeout reached (%s seconds)", timeout)
                    break
        finally:
            cap.release()
            if show_window:
                cv2.destroyAllWindows()

        logger.info("Attendance complete: %s student(s)", len(recognized_students))
        if recognized_students:
            _create_attendance_backup(attendance_file)
        return attendance_file
    except ModelUnavailableError as exc:
        logger.error("Required YuNet/SFace model unavailable: %s", exc)
        return None
    finally:
        detector.cleanup()
        db.close()


def _create_attendance_backup(attendance_file: str | Path) -> bool:
    """Create a compatibility backup of the derived attendance CSV."""
    source = Path(attendance_file)
    if not source.is_file():
        return False
    subject = source.name.split("_", 1)[0]
    destination = Path("backups") / "attendance_backup" / subject / source.name
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        logger.info("Created attendance backup: %s", destination)
        return True
    except OSError as exc:
        logger.error("Could not create attendance backup: %s", exc)
        return False


def main_with_args(args: argparse.Namespace) -> int:
    attendance_file = take_attendance(
        args.subject,
        args.model,
        args.threshold,
        not args.no_window,
        args.timeout,
        args.late_threshold,
    )
    return 0 if attendance_file else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Take attendance using YuNet + SFace")
    parser.add_argument("subject", type=str, help="Subject name for the attendance record")
    parser.add_argument(
        "--model",
        type=str,
        default=str(DEFAULT_GALLERY_PATH),
        help="Path to the SFace gallery",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=SFACE_COSINE_THRESHOLD,
        help="Minimum SFace cosine similarity (OpenCV reference: 0.363)",
    )
    parser.add_argument("--no-window", action="store_true", help="Do not show the video window")
    parser.add_argument("--timeout", type=int, default=60, help="Timeout in seconds (0 disables)")
    parser.add_argument(
        "--late-threshold",
        type=int,
        default=300,
        help="Seconds after which a student is marked late (0 disables)",
    )
    return main_with_args(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
