"""Preload all pinned local recognition and anti-spoofing runtime models."""
from __future__ import annotations

import logging

from src.core.face_models import ensure_face_models, ensure_liveness_models

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def main() -> int:
    yunet, sface = ensure_face_models()
    minifas_v2, minifas_v1se = ensure_liveness_models()
    print(f"YuNet: {yunet}")
    print(f"SFace: {sface}")
    print(f"MiniFASNetV2: {minifas_v2}")
    print(f"MiniFASNetV1SE: {minifas_v1se}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())