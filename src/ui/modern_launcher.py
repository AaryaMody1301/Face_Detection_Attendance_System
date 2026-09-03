"""Launcher for the supported modern desktop UI."""
from __future__ import annotations

import logging

from src.core.version import get_version
from src.ui.auth_gate import authenticate_interactively

logger = logging.getLogger(__name__)


def launch_modern_ui() -> bool:
    """Authenticate locally, then launch the production modern UI."""
    try:
        from src.ui.modern_app import ModernAttendanceApp

        auth_system = authenticate_interactively()
        if auth_system is None:
            logger.info("Application launch cancelled at authentication gate")
            return False

        class ProductionModernAttendanceApp(ModernAttendanceApp):
            """Keep legacy visual code while sourcing the displayed version canonically."""

            def _sync_version_label(self) -> None:
                if hasattr(self, "version_label"):
                    text = "" if getattr(self, "is_sidebar_collapsed", False) else f"v{get_version()}"
                    self.version_label.configure(text=text)

            def toggle_sidebar(self) -> None:
                super().toggle_sidebar()
                self._sync_version_label()

        app = ProductionModernAttendanceApp(auth_system)
        app._sync_version_label()
        app.mainloop()
        logger.info("Modern UI closed normally")
        return True
    except Exception:
        logger.exception("Error launching modern UI")
        return False


if __name__ == "__main__":
    launch_modern_ui()
