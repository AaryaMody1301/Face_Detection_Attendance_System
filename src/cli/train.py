"""Command-line training for the canonical YuNet + SFace gallery."""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

from src.core.face_engine import FaceEngine
from src.core.face_models import ModelUnavailableError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def train_model(
    training_dir: str = "TrainingImage",
    model_dir: str = "TrainingImageLabel",
    model_file: str = "face_gallery.npz",
) -> bool:
    """Build an SFace embedding gallery from the training directory."""
    training_path = Path(training_dir)
    if not training_path.is_dir():
        logger.error("Training directory %s does not exist", training_path)
        return False

    output_dir = Path(model_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / model_file

    engine = FaceEngine()
    try:
        if not engine.train_recognizer(training_path):
            logger.error("No usable YuNet/SFace training faces were found")
            return False
        if not engine.save_model(output_path):
            logger.error("Could not save SFace gallery to %s", output_path)
            return False
        logger.info("SFace gallery saved to %s", output_path)
        return True
    except ModelUnavailableError as exc:
        logger.error("Required OpenCV face model unavailable: %s", exc)
        return False
    finally:
        engine.cleanup()


def main_with_args(args) -> int:
    success = train_model(args.training_dir, args.model_dir, args.model_file)
    return 0 if success else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Train the YuNet + SFace face gallery")
    parser.add_argument(
        "--training-dir",
        type=str,
        default="TrainingImage",
        help="Directory containing training images",
    )
    parser.add_argument(
        "--model-dir",
        type=str,
        default="TrainingImageLabel",
        help="Directory to save the gallery",
    )
    parser.add_argument(
        "--model-file",
        type=str,
        default="face_gallery.npz",
        help="Gallery filename",
    )
    return main_with_args(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
