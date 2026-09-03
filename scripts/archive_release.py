"""Create a platform-labelled archive from a PyInstaller build."""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


def _target(dist_dir: Path) -> Path:
    if sys.platform == "darwin":
        bundle = dist_dir / "FaceAttendance.app"
        if bundle.exists():
            return bundle
    return dist_dir / "FaceAttendance"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True, help="Artifact label such as windows-x64")
    args = parser.parse_args()

    target = _target(Path("dist"))
    if not target.exists():
        raise SystemExit(f"Release target does not exist: {target}")

    output_dir = Path("release")
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = output_dir / f"FaceAttendance-1.4.0-{args.label}"
    archive_format = "zip" if sys.platform == "win32" else "gztar"
    archive = shutil.make_archive(
        str(stem),
        archive_format,
        root_dir=target.parent,
        base_dir=target.name,
    )
    print(archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
