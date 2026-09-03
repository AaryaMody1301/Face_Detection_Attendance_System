"""Preload the pinned YuNet and SFace runtime models."""
from __future__ import annotations

import logging

from src.core.face_models import ensure_face_models

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def main() -> int:
    yunet, sface = ensure_face_models()
    print(f"YuNet: {yunet}")
    print(f"SFace: {sface}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
