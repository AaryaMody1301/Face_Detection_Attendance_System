"""Run headless diagnostics against a PyInstaller build."""
from __future__ import annotations

import json
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
        temp_path = Path(temp_dir)
        diagnostics_path = temp_path / "diagnostics.json"
        env = os.environ.copy()
        env["FACE_ATTENDANCE_DATA_DIR"] = str(temp_path / "data")
        result = subprocess.run(
            [
                str(executable),
                "--diagnostics",
                "--diagnostics-output",
                str(diagnostics_path),
            ],
            env=env,
            timeout=90,
            check=False,
        )
        if result.returncode != 0:
            print(
                f"Packaged diagnostics failed with exit code {result.returncode}",
                file=sys.stderr,
            )
            return result.returncode
        if not diagnostics_path.is_file():
            print("Packaged diagnostics did not create the output file", file=sys.stderr)
            return 1

        diagnostics = json.loads(diagnostics_path.read_text(encoding="utf-8"))
        required = {
            "app_version",
            "python",
            "platform",
            "frozen",
            "resource_root",
            "data_root",
            "data_root_writable",
            "opencv",
            "customtkinter",
        }
        missing = sorted(required.difference(diagnostics))
        if missing:
            print(f"Packaged diagnostics are missing keys: {missing}", file=sys.stderr)
            return 1
        if diagnostics["frozen"] is not True:
            print("Packaged diagnostics did not report frozen=true", file=sys.stderr)
            return 1
        if diagnostics["data_root_writable"] is not True:
            print("Packaged data directory is not writable", file=sys.stderr)
            return 1

        print(json.dumps(diagnostics, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
