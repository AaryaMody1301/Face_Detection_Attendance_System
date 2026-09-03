"""Face Detection Attendance System - production entry point."""
from __future__ import annotations

import argparse
import importlib
import json
import logging
import sys
from pathlib import Path

from src.core.paths import LOGS_DIR, PROJECT_ROOT
from src.core.runtime import (
    application_import_self_test,
    prepare_runtime_environment,
    runtime_diagnostics,
)
from src.core.version import get_version

BASE_DIR = PROJECT_ROOT
prepare_runtime_environment()
LOGS_DIR.mkdir(parents=True, exist_ok=True)

_handlers: list[logging.Handler] = [logging.FileHandler(LOGS_DIR / "app.log")]
if sys.stderr is not None:
    _handlers.insert(0, logging.StreamHandler())

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=_handlers,
)
logger = logging.getLogger(__name__)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Face Detection Attendance System")
    parser.add_argument("--version", action="store_true", help="Print the application version and exit")
    parser.add_argument(
        "--diagnostics",
        action="store_true",
        help="Run headless dependency/runtime diagnostics and exit",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Import every supported production surface without opening the GUI",
    )
    parser.add_argument(
        "--diagnostics-output",
        type=Path,
        help="Write diagnostics/self-test JSON to this file",
    )
    return parser.parse_args(argv)


def check_dependencies() -> bool:
    """Verify imports and OpenCV APIs required by recognition and liveness."""
    required = {"cv2": "OpenCV", "customtkinter": "CustomTkinter"}

    ok = True
    modules = {}
    for module_name, display_name in required.items():
        try:
            module = importlib.import_module(module_name)
            modules[module_name] = module
            version = getattr(module, "__version__", "unknown")
            logger.info("%s version: %s", display_name, version)
        except ImportError as exc:
            logger.error("Missing required dependency %s: %s", display_name, exc)
            ok = False

    cv2 = modules.get("cv2")
    if cv2 is not None:
        for api_name in ("FaceDetectorYN", "FaceRecognizerSF"):
            if not hasattr(cv2, api_name):
                logger.error("Installed OpenCV does not expose %s", api_name)
                ok = False
        if not hasattr(cv2, "dnn") or not hasattr(cv2.dnn, "readNetFromONNX"):
            logger.error("Installed OpenCV does not expose DNN ONNX loading for liveness")
            ok = False

    return ok


def _emit_payload(payload: dict[str, object], output_path: Path | None) -> None:
    encoded = json.dumps(payload, indent=2, sort_keys=True)
    if output_path is not None:
        output_path = output_path.expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(encoded + "\n", encoding="utf-8")
    elif sys.stdout is not None:
        print(encoded)


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

    import tkinter as tk

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
        "Preparing YuNet + SFace...",
        "Preparing liveness protection...",
        "Starting secure login...",
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


def main(argv: list[str] | None = None) -> int:
    """Start the supported desktop UI or run a headless support command."""
    args = parse_args(argv)

    if args.version:
        if sys.stdout is not None:
            print(get_version())
        return 0

    if args.diagnostics or args.self_test:
        dependencies_ok = check_dependencies()
        payload: dict[str, object] = runtime_diagnostics()
        imports_ok = True
        if args.self_test:
            import_report = application_import_self_test()
            payload["application_imports"] = import_report
            imports_ok = bool(import_report["ok"])
        _emit_payload(payload, args.diagnostics_output)
        return 0 if dependencies_ok and imports_ok else 1

    try:
        if str(BASE_DIR) not in sys.path:
            sys.path.insert(0, str(BASE_DIR))

        if not check_dependencies():
            logger.error("Required dependencies are missing or incompatible")
            return 1

        show_splash_screen()
        from src.ui.modern_launcher import launch_modern_ui

        return 0 if launch_modern_ui() else 1
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
        return 0
    except Exception:
        logger.exception("Error starting application")
        return 1


if __name__ == "__main__":
    sys.exit(main())
