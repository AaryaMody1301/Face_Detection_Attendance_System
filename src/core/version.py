"""Canonical application version access."""
from __future__ import annotations

from importlib import metadata

PACKAGE_NAME = "face-detection-attendance-system"
SOURCE_VERSION = "1.5.0"


def get_version() -> str:
    """Return the installed package version, with a source-tree fallback."""
    try:
        return metadata.version(PACKAGE_NAME)
    except metadata.PackageNotFoundError:
        return SOURCE_VERSION


__all__ = ["PACKAGE_NAME", "SOURCE_VERSION", "get_version"]
