"""Command-line attendance using YuNet, SFace, and MiniFAS anti-spoofing."""
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
from src.core.liveness import (
    DEFAULT_LIVENESS_THRESHOLD,
    DEFAULT_LIVENESS_WINDOW,
    DEFAULT_REQUIRED_LIVE_FRAMES,
    MiniFASLiveness,
    TemporalLivenessGate,
    recognize_faces_guarded,
)
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
    liveness_threshold: float = DEFAULT_LIVENESS_THRESHOLD,
    liveness_frames: int = DEFAULT_REQUIRED_LIVE_FRAMES,
    liveness_window: int = DEFAULT_LIVENESS_WINDOW,
) -> str | None:
    """Recognize live students from the default camera and mark attendance."""
    detector = FaceDetector(confidence_threshold=confidence_threshold)
    liveness = MiniFASLiveness(live_threshold=liveness_threshold)
    liveness_gate = TemporalLivenessGate(
        window_size=liveness_window,
        required_live_frames=liveness_frames,
    )
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

        logger.info("Started liveness-gated SFace attendance capture. Press 'q' to stop.")
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    logger.error("Failed to read frame from video capture")
                    break

                display_frame = frame.copy()
                results = recognize_faces_guarded(
                    detector,
                    frame,
                    liveness,
                    liveness_gate,
                    confidence_threshold=confidence_threshold,
                )

                for result in results:
                    top, right, bottom, left = result.location
                    decision = result.liveness
                    prediction = decision.prediction
                    recognized = result.name != "Unknown" and bool(result.student_id)

                    if not prediction.is_live:
                        color = (0, 0, 255)
                        label = f"SPOOF BLOCKED: {prediction.label}"
                    elif not decision.passed:
                        color = (0, 215, 255)
                        label = (
                            f"Liveness {decision.live_frames}/"
                            f"{liveness_gate.required_live_frames}"
                        )
                    elif not recognized:
                        color = (0, 165, 255)
                        label = f"Live - Unknown ({prediction.live_score:.2f})"
                    else:
                        color = (0, 255, 0)
                        scores = recognition_buffer.setdefault(result.student_id, [])
                        scores.append(float(result.recognition_score))
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
                            if result.student_id not in recognized_students:
                                db.mark_attendance(
                                    result.student_id,
                                    result.name,
                                    subject=subject,
                                    date=date,
                                    time=_local_now().strftime("%H:%M:%S"),
                                    file_path=attendance_file,
                                    status=status,
                                    method="sface+liveness",
                                )
                                recognized_students[result.student_id] = result.name
                                if status == "Late":
                                    late_students.add(result.student_id)
                                logger.info(
                                    "Marked %s attendance for %s (%s), cosine=%.3f, live=%.3f",
                                    status.upper(),
                                    result.name,
                                    result.student_id,
                                    result.recognition_score,
                                    prediction.live_score,
                                )
                            label = (
                                f"{result.name} ({result.student_id}) "
                                f"SFace {result.recognition_score:.3f} Live {prediction.live_score:.2f}"
                            )
                            if result.student_id in late_students:
                                label += " LATE"
                                color = (0, 0, 255)
                        else:
                            label = (
                                f"Confirming {result.name} "
                                f"({good_frames}/{min_recognized_frames}, "
                                f"{result.recognition_score:.3f})"
                            )

                    cv2.rectangle(display_frame, (left, top), (right, bottom), color, 2)
                    y_pos = top - 10 if top > 20 else bottom + 20
                    cv2.putText(
                        display_frame,
                        label,
                        (left, y_pos),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.58,
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
                    cv2.imshow("Attendance System - Liveness + SFace", display_frame)
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
        logger.error("Required recognition/liveness model unavailable: %s", exc)
        return None
    finally:
        liveness_gate.reset()
        liveness.cleanup()
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
        subject=args.subject,
        model_path=args.model,
        confidence_threshold=args.threshold,
        show_window=not args.no_window,
        timeout=args.timeout,
        late_threshold=args.late_threshold,
        liveness_threshold=args.liveness_threshold,
        liveness_frames=args.liveness_frames,
        liveness_window=args.liveness_window,
    )
    return 0 if attendance_file else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Take attendance using liveness-gated YuNet + SFace"
    )
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
    parser.add_argument(
        "--liveness-threshold",
        type=float,
        default=DEFAULT_LIVENESS_THRESHOLD,
        help="Minimum MiniFAS live-class probability (default: 0.50)",
    )
    parser.add_argument(
        "--liveness-frames",
        type=int,
        default=DEFAULT_REQUIRED_LIVE_FRAMES,
        help="Live frames required before identity matching (default: 3)",
    )
    parser.add_argument(
        "--liveness-window",
        type=int,
        default=DEFAULT_LIVENESS_WINDOW,
        help="Temporal liveness window size (default: 5)",
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