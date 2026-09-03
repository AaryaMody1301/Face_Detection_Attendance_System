"""Run the production self-test against a PyInstaller build."""
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
                "--self-test",
                "--diagnostics-output",
                str(diagnostics_path),
            ],
            env=env,
            timeout=90,
            check=False,
        )

        diagnostics = None
        if diagnostics_path.is_file():
            diagnostics = json.loads(diagnostics_path.read_text(encoding="utf-8"))
            print(json.dumps(diagnostics, indent=2, sort_keys=True))

        if result.returncode != 0:
            print(f"Packaged self-test failed with exit code {result.returncode}", file=sys.stderr)
            if isinstance(diagnostics, dict):
                imports = diagnostics.get("application_imports")
                if isinstance(imports, dict):
                    failed = {
                        name: status
                        for name, status in imports.get("modules", {}).items()
                        if status != "ok"
                    }
                    if failed:
                        print(f"Failed packaged imports: {failed}", file=sys.stderr)
            return result.returncode
        if diagnostics is None:
            print("Packaged self-test did not create the output file", file=sys.stderr)
            return 1

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
            "application_imports",
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
        if diagnostics["app_version"] in {"unknown", "0.0.0", ""}:
            print("Packaged application version metadata is missing", file=sys.stderr)
            return 1
        imports = diagnostics["application_imports"]
        if not isinstance(imports, dict) or imports.get("ok") is not True:
            print(f"Supported application imports failed: {imports}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
