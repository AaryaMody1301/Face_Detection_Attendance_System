"""
Main entry point for the Face Detection Attendance System CLI.
"""
import argparse
import sys
from importlib import import_module


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Face Detection Attendance System",
        prog="attend",
    )
    parser.add_argument(
        "--version", action="version", version="Face Detection Attendance System 1.0.0"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Train command
    train_parser = subparsers.add_parser("train", help="Train the face recognition model")
    train_parser.add_argument(
        "--training-dir",
        type=str,
        default="TrainingImage",
        help="Directory containing training images",
    )
    train_parser.add_argument(
        "--model-dir",
        type=str,
        default="TrainingImageLabel",
        help="Directory to save the model",
    )
    train_parser.add_argument(
        "--model-file",
        type=str,
        default="trainner.yml",
        help="Filename for the model",
    )

    # Take attendance command
    take_parser = subparsers.add_parser(
        "take", help="Take attendance using face recognition"
    )
    take_parser.add_argument(
        "subject", type=str, help="Subject name for the attendance record"
    )
    take_parser.add_argument(
        "--model",
        type=str,
        default="TrainingImageLabel/trainner.yml",
        help="Path to the trained model",
    )
    take_parser.add_argument(
        "--threshold",
        type=int,
        default=50,
        help="Threshold for face recognition confidence",
    )
    take_parser.add_argument(
        "--no-window", action="store_true", help="Don't show the video window"
    )
    take_parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Timeout in seconds (0 for no timeout)",
    )

    # View attendance command
    view_parser = subparsers.add_parser("view", help="View attendance records")
    view_parser.add_argument("--subject", type=str, help="Filter by subject")
    view_parser.add_argument("--date", type=str, help="Filter by date (YYYY-MM-DD)")
    view_parser.add_argument(
        "--export", action="store_true", help="Export to CSV file"
    )

    # Run app command
    app_parser = subparsers.add_parser("app", help="Start the GUI application")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    try:
        if args.command == "app":
            # Import the UI module and start the application
            from src.ui.app import FaceAttendanceApp
            import tkinter as tk

            root = tk.Tk()
            app = FaceAttendanceApp(root)
            root.mainloop()
            return 0

        # Import the appropriate module based on the command
        module_name = f"src.cli.{args.command}_attendance"
        if args.command == "train":
            module_name = "src.cli.train"

        module = import_module(module_name)
        
        # Remove the command from the args namespace
        delattr(args, "command")
        
        # Call the main function of the module with the parsed arguments
        return module.main_with_args(args)
    
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 