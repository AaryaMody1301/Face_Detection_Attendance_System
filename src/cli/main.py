"""Unified command-line entry point for the attendance system."""
from __future__ import annotations

import argparse

from src.core.face_engine import DEFAULT_GALLERY_PATH, SFACE_COSINE_THRESHOLD
from src.core.liveness import (
    DEFAULT_LIVENESS_THRESHOLD,
    DEFAULT_LIVENESS_WINDOW,
    DEFAULT_REQUIRED_LIVE_FRAMES,
)
from src.core.paths import TRAINING_IMAGES_DIR, TRAINING_MODELS_DIR
from src.core.version import get_version


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Face Detection Attendance System", prog="attend")
    parser.add_argument(
        "--version",
        action="version",
        version=f"Face Detection Attendance System {get_version()}",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    train = subparsers.add_parser("train", help="Build the local YuNet + SFace gallery")
    train.add_argument("--training-dir", default=str(TRAINING_IMAGES_DIR))
    train.add_argument("--model-dir", default=str(TRAINING_MODELS_DIR))
    train.add_argument("--model-file", default="face_gallery.npz")

    take = subparsers.add_parser("take", help="Take liveness-gated face attendance")
    take.add_argument("subject")
    take.add_argument("--model", default=str(DEFAULT_GALLERY_PATH))
    take.add_argument("--threshold", type=float, default=SFACE_COSINE_THRESHOLD)
    take.add_argument("--liveness-threshold", type=float, default=DEFAULT_LIVENESS_THRESHOLD)
    take.add_argument("--liveness-frames", type=int, default=DEFAULT_REQUIRED_LIVE_FRAMES)
    take.add_argument("--liveness-window", type=int, default=DEFAULT_LIVENESS_WINDOW)
    take.add_argument("--camera", type=int, default=0)
    take.add_argument("--no-window", action="store_true")
    take.add_argument("--timeout", type=int, default=60)
    take.add_argument("--late-threshold", type=int, default=300)

    view = subparsers.add_parser("view", help="View attendance records from SQLite")
    view.add_argument("--subject")
    view.add_argument("--date")
    view.add_argument("--export", action="store_true")

    subparsers.add_parser("app", help="Start the supported modern desktop UI")
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "app":
        from src.ui.modern_launcher import launch_modern_ui

        return 0 if launch_modern_ui() else 1
    if args.command == "train":
        from src.cli.train import main_with_args

        return main_with_args(args)
    if args.command == "take":
        from src.cli.take_attendance import main_with_args

        return main_with_args(args)
    if args.command == "view":
        from src.cli.view_attendance import main_with_args

        return main_with_args(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
