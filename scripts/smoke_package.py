"""Run headless diagnostics against a PyInstaller build."""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path


def packaged_executable(dist_dir: Path) -> Path:
    if sys.platform == "win32":
        return dist_dir / "FaceAttendance" / "FaceAttendance.exe"
    if sys.platform == "darwin":
        bundle_exe = dist_dir / "FaceAttendance.app" / "Contents" / "MacOS" / "FaceAttendance"
        if bundle_exe.is_file():
            return bundle_exe
    return dist_dir / "FaceAttendance" / "FaceAttendance"


def main() -> int:
    executable = packaged_executable(Path("dist"))
    if not executable.is_file():
        print(f"Packaged executable not found: {executable}", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory(prefix="face-attendance-smoke-") as temp_dir:
        env = os.environ.copy()
        env["FACE_ATTENDANCE_DATA_DIR"] = temp_dir
        result = subprocess.run(
            [str(executable), "--diagnostics"],
            env=env,
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    if result.returncode != 0:
        print(
            f"Packaged diagnostics failed with exit code {result.returncode}",
            file=sys.stderr,
        )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
