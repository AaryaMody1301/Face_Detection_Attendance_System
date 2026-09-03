"""Face Detection Attendance System - main entry point."""
from __future__ import annotations

import importlib
import logging
import sys
import traceback
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / "app.log"),
    ],
)
logger = logging.getLogger(__name__)

REQUIRED_DIRS = (
    "TrainingImage",
    "TrainingImageLabel",
    "Attendance",
    "Data",
    "StudentDetails",
    "backups",
    "config",
)
for directory in REQUIRED_DIRS:
    (BASE_DIR / directory).mkdir(parents=True, exist_ok=True)


def check_dependencies() -> bool:
    """Verify required imports without crashing before diagnostics can run."""
    required = {"cv2": "OpenCV", "customtkinter": "CustomTkinter"}
    optional = {"face_recognition": "face_recognition", "dlib": "dlib"}

    ok = True
    for module_name, display_name in required.items():
        try:
            module = importlib.import_module(module_name)
            version = getattr(module, "__version__", "unknown")
            logger.info("%s version: %s", display_name, version)
        except ImportError as exc:
            logger.error("Missing required dependency %s: %s", display_name, exc)
            ok = False

    for module_name, display_name in optional.items():
        try:
            module = importlib.import_module(module_name)
            version = getattr(module, "__version__", "available")
            logger.info("%s version: %s", display_name, version)
        except ImportError:
            logger.warning("Optional dependency %s is unavailable.", display_name)

    return ok


def show_splash_screen() -> None:
    """Show the startup splash without relying on implicit tkinter.ttk imports."""
    import tkinter as tk
    from tkinter import ttk

    root = tk.Tk()
    root.withdraw()
    splash = tk.Toplevel(root)
    splash.title("Loading...")

    screen_width = splash.winfo_screenwidth()
    screen_height = splash.winfo_screenheight()
    width, height = 400, 300
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    splash.geometry(f"{width}x{height}+{x}+{y}")
    splash.overrideredirect(True)
    splash.configure(bg="#2d3436")

    tk.Label(
        splash,
        text="Face Detection Attendance System",
        font=("Arial", 16, "bold"),
        bg="#2d3436",
        fg="white",
    ).pack(pady=(50, 20))

    message_var = tk.StringVar(value="Loading components...")
    tk.Label(
        splash,
        textvariable=message_var,
        font=("Arial", 10),
        bg="#2d3436",
        fg="white",
    ).pack(pady=10)

    progress_var = tk.DoubleVar()
    ttk.Progressbar(
        splash,
        orient="horizontal",
        length=300,
        mode="determinate",
        variable=progress_var,
    ).pack(pady=20)

    steps = [
        "Checking dependencies...",
        "Initializing database...",
        "Loading face detection models...",
        "Preparing user interface...",
        "Starting application...",
    ]

    def update_splash(step: int = 0) -> None:
        if step < len(steps):
            message_var.set(steps[step])
            progress_var.set((step + 1) / len(steps) * 100)
            splash.after(350, lambda: update_splash(step + 1))
            return
        splash.destroy()
        root.destroy()

    splash.after(150, update_splash)
    root.mainloop()


def main() -> int:
    """Start the desktop application."""
    try:
        if str(BASE_DIR) not in sys.path:
            sys.path.insert(0, str(BASE_DIR))

        if not check_dependencies():
            logger.error("Required dependencies are missing or incompatible")
            return 1

        show_splash_screen()

        models_dir = BASE_DIR / "models"
        models_dir.mkdir(exist_ok=True)

        from src.ui.ui_selector import select_ui

        ui_type = select_ui()
        logger.info("Selected UI type: %s", ui_type)

        if ui_type.lower() == "modern":
            try:
                from src.ui.modern_launcher import launch_modern_ui

                launch_modern_ui()
            except ImportError as exc:
                logger.error("Failed to import modern UI: %s", exc)
                from src.ui.classic_launcher import launch_classic_ui

                launch_classic_ui()
        else:
            from src.ui.classic_launcher import launch_classic_ui

            launch_classic_ui()
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
        return 0
    except Exception as exc:  # noqa: BLE001 - top-level boundary logs unexpected startup failures.
        logger.error("Error starting application: %s", exc)
        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
