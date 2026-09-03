"""Production navigation policy for authenticated desktop users."""
from __future__ import annotations

from typing import Protocol


class PermissionChecker(Protocol):
    def has_permission(self, permission: str) -> bool: ...


NAVIGATION_PERMISSIONS = {
    "Dashboard": "view_attendance",
    "Mark Attendance": "take_attendance",
    "Analytics": "view_attendance",
    "Registration": "manage_students",
    "Training": "manage_students",
    "Settings": "manage_settings",
}


def permission_for_navigation(label: str) -> str | None:
    """Return the permission required by a production navigation label."""
    return NAVIGATION_PERMISSIONS.get(label)


def can_access_navigation(auth_system: PermissionChecker, label: str) -> bool:
    """Return whether the current user may open the requested navigation surface."""
    permission = permission_for_navigation(label)
    return permission is None or auth_system.has_permission(permission)
