# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller one-folder build for the production desktop attendance application."""
from importlib import metadata
from pathlib import Path
import sys

from PyInstaller.utils.hooks import collect_all, copy_metadata

project_root = Path(SPECPATH).resolve()
app_version = metadata.version("face-detection-attendance-system")
datas = copy_metadata("face-detection-attendance-system")
binaries = []
hiddenimports = []

for package_name in ("customtkinter", "ttkthemes"):
    package_datas, package_binaries, package_hiddenimports = collect_all(package_name)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports

assets_dir = project_root / "assets"
config_file = project_root / "config" / "config.json"
if assets_dir.is_dir():
    datas.append((str(assets_dir), "assets"))
if config_file.is_file():
    datas.append((str(config_file), "config"))

a = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="FaceAttendance",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="FaceAttendance",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="FaceAttendance.app",
        icon=None,
        bundle_identifier="io.github.aaryamody1301.faceattendance",
        version=app_version,
        info_plist={
            "NSCameraUsageDescription": (
                "Camera access is required to recognize enrolled students and record attendance."
            ),
        },
    )
