"""
Command-line script for training the face recognition model.
"""
import os
import argparse
import logging
from src.face_recognition.detector import FaceDetector

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def train_model(training_dir="TrainingImage", model_dir="TrainingImageLabel", 
               model_file="trainner.yml"):
    """
    Train the face recognition model with images in the training directory.
    
    Args:
        training_dir (str): Directory containing training images
        model_dir (str): Directory to save the model
        model_file (str): Filename for the model
        
    Returns:
        bool: True if training was successful
    """
    logger.info(f"Training model with images from {training_dir}...")
    
    # Check if training directory exists
    if not os.path.exists(training_dir):
        logger.error(f"Training directory {training_dir} does not exist.")
        return False
    
    # Check if training directory contains images
    if not os.listdir(training_dir):
        logger.error(f"No images found in training directory {training_dir}.")
        return False
    
    # Create model directory if it doesn't exist
    os.makedirs(model_dir, exist_ok=True)
    
    # Train the model
    detector = FaceDetector()
    success = detector.train_recognizer(training_dir)
    
    if not success:
        logger.error("Failed to train the model.")
        return False
    
    # Save the model
    model_path = os.path.join(model_dir, model_file)
    if detector.save_model(model_path):
        logger.info(f"Model trained successfully and saved to {model_path}.")
        return True
    else:
        logger.error(f"Failed to save model to {model_path}.")
        return False


def main_with_args(args):
    """Run with parsed arguments from the main CLI."""
    success = train_model(args.training_dir, args.model_dir, args.model_file)
    return 0 if success else 1


def main():
    """Main entry point for the script when run directly."""
    parser = argparse.ArgumentParser(description="Train the face recognition model")
    parser.add_argument("--training-dir", type=str, default="TrainingImage",
                      help="Directory containing training images")
    parser.add_argument("--model-dir", type=str, default="TrainingImageLabel",
                      help="Directory to save the model")
    parser.add_argument("--model-file", type=str, default="trainner.yml",
                      help="Filename for the model")
    
    args = parser.parse_args()
    
    return main_with_args(args)


if __name__ == "__main__":
    main() 