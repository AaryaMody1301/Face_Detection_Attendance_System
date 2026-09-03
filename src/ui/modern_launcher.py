"""Launcher for the supported modern desktop UI."""
from __future__ import annotations

import logging
from tkinter import messagebox

from src.core.version import get_version
from src.ui.access_policy import can_access_navigation
from src.ui.auth_gate import authenticate_interactively

logger = logging.getLogger(__name__)


def launch_modern_ui() -> bool:
    """Authenticate locally, enforce role permissions, then launch the production UI."""
    try:
        from src.ui.modern_app import ModernAttendanceApp

        auth_system = authenticate_interactively()
        if auth_system is None:
            logger.info("Application launch cancelled at authentication gate")
            return False

        class ProductionModernAttendanceApp(ModernAttendanceApp):
            """Production wrapper that adds version and authorization guardrails."""

            def __init__(self, authenticated_user):
                super().__init__(authenticated_user)
                self._apply_role_navigation()
                self._sync_version_label()

            def _sync_version_label(self) -> None:
                if hasattr(self, "version_label"):
                    collapsed = getattr(self, "is_sidebar_collapsed", False)
                    text = "" if collapsed else f"v{get_version()}"
                    self.version_label.configure(text=text)

            def _apply_role_navigation(self) -> None:
                for button in getattr(self, "buttons", []):
                    label = str(getattr(button, "_orig_text", ""))
                    if label and not can_access_navigation(self.auth_system, label):
                        button.pack_forget()

            def _authorize(self, label: str) -> bool:
                if can_access_navigation(self.auth_system, label):
                    return True
                logger.warning("Blocked unauthorized navigation to %s", label)
                messagebox.showwarning(
                    "Permission denied",
                    f"Your account is not allowed to open {label}.",
                    parent=self,
                )
                return False

            def show_dashboard(self):
                if self._authorize("Dashboard"):
                    return super().show_dashboard()
                return None

            def show_mark_attendance(self):
                if self._authorize("Mark Attendance"):
                    return super().show_mark_attendance()
                return None

            def show_analytics(self):
                if self._authorize("Analytics"):
                    return super().show_analytics()
                return None

            def register_student(self):
                if self._authorize("Registration"):
                    return super().register_student()
                return None

            def train_model(self):
                if self._authorize("Training"):
                    return super().train_model()
                return None

            def show_settings(self):
                if self._authorize("Settings"):
                    return super().show_settings()
                return None

            def toggle_sidebar(self) -> None:
                super().toggle_sidebar()
                self._sync_version_label()

        app = ProductionModernAttendanceApp(auth_system)
        app.mainloop()
        logger.info("Modern UI closed normally")
        return True
    except Exception:
        logger.exception("Error launching modern UI")
        return False


if __name__ == "__main__":
    launch_modern_ui()
