"""Launcher for the classic UI version of Face Detection Attendance System."""
from __future__ import annotations

import logging
import tkinter as tk

from src.ui.classic_face_compat import ClassicFaceDetector

logger = logging.getLogger(__name__)


def launch_classic_ui() -> bool:
    """Launch the original classic UI on the canonical face engine."""
    try:
        from src.ui import app as classic_app

        # The original classic camera loop expects a historical two-list return
        # value. Keep that UI contract local to this launcher while its detector
        # still runs YuNet + SFace underneath.
        classic_app.FaceDetector = ClassicFaceDetector

        root = tk.Tk()
        classic_app.FaceAttendanceApp(root)
        root.mainloop()
        logger.info("Classic UI closed normally")
        return True
    except Exception as exc:  # noqa: BLE001 - top-level UI boundary
        logger.error("Error launching classic UI: %s", exc)
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    launch_classic_ui()
