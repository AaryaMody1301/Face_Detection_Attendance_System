"""Small production authentication gate shared by desktop launchers."""
from __future__ import annotations

import logging
import tkinter as tk
from tkinter import messagebox, simpledialog

from src.auth.auth_system import AuthSystem

logger = logging.getLogger(__name__)


def _prompt_new_admin(root: tk.Tk, auth: AuthSystem) -> bool:
    messagebox.showinfo(
        "First-run setup",
        "Create the first local administrator account. No default password is provided.",
        parent=root,
    )
    username = simpledialog.askstring(
        "Create administrator",
        "Administrator username:",
        initialvalue="admin",
        parent=root,
    )
    if username is None:
        return False
    full_name = simpledialog.askstring(
        "Create administrator",
        "Administrator display name:",
        initialvalue="Administrator",
        parent=root,
    )
    if full_name is None:
        return False

    while True:
        password = simpledialog.askstring(
            "Create administrator",
            "Choose a password (minimum 10 characters):",
            show="*",
            parent=root,
        )
        if password is None:
            return False
        confirmation = simpledialog.askstring(
            "Create administrator",
            "Confirm password:",
            show="*",
            parent=root,
        )
        if confirmation is None:
            return False
        if password != confirmation:
            messagebox.showerror("Password mismatch", "The passwords do not match.", parent=root)
            continue
        result = auth.create_user(
            username=username,
            password=password,
            role="admin",
            full_name=full_name or username,
        )
        if result.success:
            messagebox.showinfo(
                "Administrator created",
                "The local administrator account was created successfully.",
                parent=root,
            )
            return True
        messagebox.showerror("Account setup", result.message, parent=root)
        if "Password" not in result.message:
            return False


def authenticate_interactively(auth: AuthSystem | None = None, *, max_attempts: int = 5) -> AuthSystem | None:
    """Require first-run setup or a local login before opening the application."""
    auth = auth or AuthSystem()
    root = tk.Tk()
    root.withdraw()
    try:
        if not auth.check_if_any_user_exists() and not _prompt_new_admin(root, auth):
            return None

        for attempt in range(1, max_attempts + 1):
            username = simpledialog.askstring("Sign in", "Username:", parent=root)
            if username is None:
                return None
            password = simpledialog.askstring("Sign in", "Password:", show="*", parent=root)
            if password is None:
                return None
            if auth.login(username, password):
                return auth
            remaining = max_attempts - attempt
            message = "Invalid username or password."
            if remaining:
                message += f" {remaining} attempt(s) remaining."
            messagebox.showerror("Sign in failed", message, parent=root)
        logger.warning("Authentication gate exhausted %s attempts", max_attempts)
        return None
    finally:
        root.destroy()


__all__ = ["authenticate_interactively"]
