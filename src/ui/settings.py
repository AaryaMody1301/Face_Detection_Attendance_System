"""Production settings page for the supported modern UI."""
from __future__ import annotations

import logging
import threading
from tkinter import messagebox

import customtkinter as ctk
import cv2

from src.core.camera import ResilientCamera
from src.core.utils.config_manager import ConfigManager
from src.core.version import get_version
from src.utils.backup_manager import BackupManager

logger = logging.getLogger(__name__)


class SettingsPage(ctk.CTkFrame):
    """Configure supported runtime options and local backups."""

    def __init__(self, master):
        super().__init__(master)
        self.config_manager = ConfigManager()
        self.backup_manager = BackupManager()
        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._setup_general_panel()
        self._setup_backup_panel()
        self._load_values()

    def _section(self, parent, title: str) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=12, pady=8)
        ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(size=16, weight="bold")).pack(
            anchor="w", padx=14, pady=(12, 6)
        )
        return frame

    def _setup_general_panel(self) -> None:
        panel = ctk.CTkScrollableFrame(self, label_text=f"Application Settings · v{get_version()}")
        panel.grid(row=0, column=0, padx=(18, 9), pady=18, sticky="nsew")

        appearance = self._section(panel, "Appearance")
        self.appearance_var = ctk.StringVar(value="system")
        ctk.CTkLabel(appearance, text="Appearance mode").pack(anchor="w", padx=14)
        ctk.CTkOptionMenu(
            appearance,
            values=["system", "light", "dark"],
            variable=self.appearance_var,
        ).pack(fill="x", padx=14, pady=(4, 12))

        camera = self._section(panel, "Camera")
        self.camera_var = ctk.StringVar(value="0")
        ctk.CTkLabel(camera, text="Camera ID").pack(anchor="w", padx=14)
        ctk.CTkEntry(camera, textvariable=self.camera_var).pack(fill="x", padx=14, pady=(4, 8))
        ctk.CTkButton(camera, text="Test Camera", command=self._test_camera).pack(
            fill="x", padx=14, pady=(0, 12)
        )

        recognition = self._section(panel, "Recognition")
        ctk.CTkLabel(
            recognition,
            text="Backend: YuNet detection + SFace recognition",
        ).pack(anchor="w", padx=14, pady=(0, 8))
        self.recognition_threshold_var = ctk.DoubleVar(value=0.363)
        self.recognition_threshold_label = ctk.CTkLabel(recognition, text="SFace threshold: 0.363")
        self.recognition_threshold_label.pack(anchor="w", padx=14)
        ctk.CTkSlider(
            recognition,
            from_=0.20,
            to=0.70,
            number_of_steps=50,
            variable=self.recognition_threshold_var,
            command=self._update_threshold_labels,
        ).pack(fill="x", padx=14, pady=(4, 12))

        liveness = self._section(panel, "Liveness")
        ctk.CTkLabel(
            liveness,
            text="Passive MiniFAS liveness is mandatory for automatic attendance.",
            wraplength=420,
            justify="left",
        ).pack(anchor="w", padx=14, pady=(0, 8))
        self.liveness_threshold_var = ctk.DoubleVar(value=0.50)
        self.liveness_threshold_label = ctk.CTkLabel(liveness, text="Live threshold: 0.50")
        self.liveness_threshold_label.pack(anchor="w", padx=14)
        ctk.CTkSlider(
            liveness,
            from_=0.30,
            to=0.80,
            number_of_steps=50,
            variable=self.liveness_threshold_var,
            command=self._update_threshold_labels,
        ).pack(fill="x", padx=14, pady=(4, 8))
        self.live_frames_var = ctk.StringVar(value="3")
        ctk.CTkLabel(liveness, text="Required live frames (5-frame window)").pack(
            anchor="w", padx=14
        )
        ctk.CTkOptionMenu(
            liveness,
            values=["2", "3", "4", "5"],
            variable=self.live_frames_var,
        ).pack(fill="x", padx=14, pady=(4, 12))

        buttons = ctk.CTkFrame(panel, fg_color="transparent")
        buttons.pack(fill="x", padx=12, pady=12)
        buttons.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(buttons, text="Save Settings", command=self._save_settings).grid(
            row=0, column=0, padx=(0, 5), sticky="ew"
        )
        ctk.CTkButton(
            buttons,
            text="Reset Defaults",
            fg_color="gray45",
            command=self._reset_defaults,
        ).grid(row=0, column=1, padx=(5, 0), sticky="ew")
        self.general_status = ctk.CTkLabel(panel, text="")
        self.general_status.pack(fill="x", padx=12, pady=(0, 12))

    def _setup_backup_panel(self) -> None:
        panel = ctk.CTkFrame(self)
        panel.grid(row=0, column=1, padx=(9, 18), pady=18, sticky="nsew")
        panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(panel, text="Local Backups", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, padx=18, pady=(20, 8), sticky="w"
        )
        ctk.CTkLabel(
            panel,
            text=(
                "Backups stay in the application's local data directory. The SQLite database "
                "is copied with SQLite's online backup API, and enrollment models/config are "
                "included in the same timestamped backup set."
            ),
            wraplength=420,
            justify="left",
        ).grid(row=1, column=0, padx=18, pady=(0, 18), sticky="ew")

        ctk.CTkButton(panel, text="Create Backup Now", command=self._perform_backup).grid(
            row=2, column=0, padx=18, pady=6, sticky="ew"
        )
        ctk.CTkButton(
            panel,
            text="Clean Old Backups",
            fg_color="gray45",
            command=self._clean_old_backups,
        ).grid(row=3, column=0, padx=18, pady=6, sticky="ew")
        self.backup_status = ctk.CTkLabel(panel, text="", wraplength=420, justify="left")
        self.backup_status.grid(row=4, column=0, padx=18, pady=18, sticky="ew")

    def _load_values(self) -> None:
        config = self.config_manager.get_config()
        ui = config.get("ui", {})
        camera = config.get("camera", {})
        recognition = config.get("face_recognition", {})
        liveness = config.get("liveness", {})
        self.appearance_var.set(str(ui.get("theme", "system")))
        self.camera_var.set(str(camera.get("device_id", camera.get("id", 0))))
        self.recognition_threshold_var.set(float(recognition.get("threshold", 0.363)))
        self.liveness_threshold_var.set(float(liveness.get("threshold", 0.50)))
        self.live_frames_var.set(str(liveness.get("required_live_frames", 3)))
        self._update_threshold_labels()

    def _update_threshold_labels(self, _value=None) -> None:
        self.recognition_threshold_label.configure(
            text=f"SFace threshold: {self.recognition_threshold_var.get():.3f}"
        )
        self.liveness_threshold_label.configure(
            text=f"Live threshold: {self.liveness_threshold_var.get():.2f}"
        )

    def _save_settings(self) -> None:
        try:
            camera_id = int(self.camera_var.get().strip())
            required_frames = int(self.live_frames_var.get())
        except ValueError:
            self.general_status.configure(
                text="Camera ID and liveness frames must be integers.",
                text_color="red",
            )
            return

        payload = {
            "ui": {"type": "modern", "theme": self.appearance_var.get()},
            "camera": {"device_id": camera_id, "id": camera_id},
            "face_detection": {"detection_method": "yunet"},
            "face_recognition": {
                "method": "sface",
                "threshold": float(self.recognition_threshold_var.get()),
            },
            "liveness": {
                "enabled": True,
                "threshold": float(self.liveness_threshold_var.get()),
                "window": 5,
                "required_live_frames": required_frames,
            },
        }
        if self.config_manager.update_config(payload):
            ctk.set_appearance_mode(self.appearance_var.get())
            self.general_status.configure(text="Settings saved.", text_color="green")
        else:
            self.general_status.configure(text="Could not save settings.", text_color="red")

    def _reset_defaults(self) -> None:
        if not messagebox.askyesno("Reset settings", "Restore supported settings to defaults?"):
            return
        if self.config_manager.restore_defaults():
            self._load_values()
            ctk.set_appearance_mode(self.appearance_var.get())
            self.general_status.configure(text="Defaults restored.", text_color="green")
        else:
            self.general_status.configure(text="Could not restore defaults.", text_color="red")

    def _test_camera(self) -> None:
        try:
            camera_id = int(self.camera_var.get().strip())
        except ValueError:
            self.general_status.configure(text="Camera ID must be an integer.", text_color="red")
            return

        camera = ResilientCamera(camera_id)
        try:
            if not camera.open():
                self.general_status.configure(
                    text=f"Could not open camera {camera_id}.", text_color="red"
                )
                return
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            ok, frame = camera.read()
            if not ok or frame is None:
                self.general_status.configure(
                    text=f"Camera {camera_id} opened but no frame was read.",
                    text_color="red",
                )
                return
            height, width = frame.shape[:2]
            self.general_status.configure(
                text=f"Camera {camera_id} is working ({width}×{height}).",
                text_color="green",
            )
        finally:
            camera.release()

    def _run_backup_action(self, action, prefix: str) -> None:
        self.backup_status.configure(text=f"{prefix}…", text_color="gray70")

        def worker() -> None:
            result = action()
            self.after(
                0,
                lambda: self.backup_status.configure(
                    text=result.message,
                    text_color="green" if result.success else "red",
                ),
            )

        threading.Thread(target=worker, daemon=True).start()

    def _perform_backup(self) -> None:
        self._run_backup_action(self.backup_manager.perform_backup, "Creating backup")

    def _clean_old_backups(self) -> None:
        self._run_backup_action(self.backup_manager.clean_old_backups, "Cleaning old backups")


__all__ = ["SettingsPage"]
