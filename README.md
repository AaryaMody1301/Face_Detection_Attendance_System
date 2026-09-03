# Face Detection Attendance System

A local-first facial-recognition attendance system built with Python, OpenCV, and customtkinter. Automatic attendance uses YuNet face detection, MiniFAS passive liveness checks, and SFace identity matching before a student can be marked present.

![Python Version](https://img.shields.io/badge/python-3.10--3.12-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![OpenCV](https://img.shields.io/badge/OpenCV-4.x-red)

## Features

- **Liveness-gated attendance**: Print and screen presentation attacks are checked before SFace identity matching
- **YuNet + SFace recognition**: OpenCV-native face detection, alignment, embeddings, and cosine matching
- **Temporal anti-spoofing**: A face must pass repeated MiniFAS liveness checks before automatic recognition is allowed
- **Resilient camera capture**: Platform backend fallback plus automatic reconnect after repeated frame-read failures
- **Student registration and training**: Capture images and build the local SFace gallery
- **SQLite-first attendance data**: Attendance and student records use the local database; CSV files are compatibility exports
- **Local model inference**: No cloud recognition API or paid service is required
- **Native desktop bundles**: PyInstaller one-folder builds for Windows, macOS, and Linux
- **Multi-platform CI**: Source and frozen-app smoke checks run on GitHub-hosted runners

## Security model

Automatic attendance follows this order:

1. YuNet detects the face.
2. MiniFASNet V2 + V1SE classify the face crop as live, paper spoof, or screen spoof.
3. A short temporal gate requires repeated live results for the same spatial face track.
4. Only after liveness passes does SFace compute and match the identity embedding.
5. Attendance is stored with method `sface+liveness`.

If the liveness models are unavailable or fail verification, automatic attendance fails closed. Manual attendance remains an explicit operator action.

Passive RGB liveness reduces common printed-photo and screen-replay attacks, but it is not a certified biometric presentation-attack-detection system and should not be treated as equivalent to dedicated IR/depth hardware.

## Screenshot

<p align="center">
  <img src="docs/img/screenshot.png" alt="Face Detection Attendance System" width="80%">
</p>

## Installation from source

### Prerequisites

- Python 3.10, 3.11, or 3.12
- Webcam (built-in or external)
- Internet access once for the default model download, or locally preloaded model files

### Steps

1. Clone the repository:

   ```bash
   git clone https://github.com/AaryaMody1301/Face_Detection_Attendance_System.git
   cd Face_Detection_Attendance_System
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv venv
   ```

   Windows:

   ```bash
   venv\Scripts\activate
   ```

   macOS/Linux:

   ```bash
   source venv/bin/activate
   ```

3. Install the application:

   ```bash
   python -m pip install -e .
   ```

4. Optionally preload and verify all face models:

   ```bash
   python scripts/download_face_models.py
   ```

5. Run the application:

   ```bash
   python main.py
   ```

## Desktop bundles

Tagged releases can produce native one-folder bundles for Windows, macOS, and Linux through `.github/workflows/release.yml`. PyInstaller builds on each target operating system rather than cross-compiling.

To build on the current machine:

```bash
python -m pip install -e ".[dev]"
python -m PyInstaller --clean --noconfirm face_attendance.spec
python scripts/smoke_package.py
```

The packaged executable supports headless diagnostics, which is also used by CI:

```bash
python main.py --diagnostics
python main.py --version
```

For tagged releases, push a version tag such as `v1.4.0`. The release workflow builds and smoke-tests each native bundle, archives it, and attaches the artifacts to the GitHub Release.

## Runtime models

Model binaries are not committed to this repository. The application downloads pinned copies and verifies exact file size and SHA-256 before use.

- **YuNet** — face detection
- **SFace** — face alignment, embeddings, and cosine matching
- **MiniFASNetV2 + MiniFASNetV1SE** — passive print/screen anti-spoofing ensemble

Offline installations can point to local model files with:

- `FACE_YUNET_MODEL`
- `FACE_SFACE_MODEL`
- `FACE_LIVENESS_V2_MODEL`
- `FACE_LIVENESS_V1SE_MODEL`

See [MODEL_LICENSES.md](MODEL_LICENSES.md) for model provenance, hashes, and license notes.

## Usage

### Student registration and training

1. Open the student registration/training area.
2. Enter the student ID and name.
3. Capture varied facial images with the webcam.
4. Start training/enrollment.
5. The application creates or updates the local `face_gallery.npz` SFace gallery.

Legacy LBPH/dlib model files are not compatible with the SFace gallery and are not converted automatically.

### Mark attendance

1. Open Attendance.
2. Select the subject/class.
3. Start the camera.
4. Keep the face clearly visible while the short liveness confirmation completes.
5. A spoof result is blocked before identity matching. A live, enrolled face is then matched with SFace and marked automatically.
6. If the camera disconnects temporarily, the capture layer retries the platform backend and attempts to reconnect automatically.
7. Manual attendance remains available when operator review is required.

### Command-line attendance

```bash
python -m src.cli.take_attendance "Data Science" --camera 0
```

Useful controls include `--camera`, `--threshold`, `--liveness-threshold`, `--liveness-frames`, `--liveness-window`, `--timeout`, and `--late-threshold`.

## Data and model locations

Source checkouts store mutable runtime data under `Data/` by default. Frozen desktop builds use the operating system's per-user application-data directory so installed applications do not need write access beside the executable.

Typical packaged locations are:

- Windows: `%LOCALAPPDATA%\AaryaMody1301\FaceDetectionAttendanceSystem`
- macOS: `~/Library/Application Support/FaceDetectionAttendanceSystem`
- Linux: `~/.local/share/FaceDetectionAttendanceSystem`

`FACE_ATTENDANCE_DATA_DIR` overrides the default on every platform.

Important generated paths include:

```text
<application-data>/
├── attendance.db
├── backups/
├── config/
├── exports/
├── logs/
├── models/
│   ├── face_gallery.npz
│   ├── opencv_zoo/
│   └── anti_spoof/
└── training_images/
```

## Diagnostics and performance

Run a headless environment report:

```bash
python main.py --diagnostics
```

It reports the app/Python/dependency versions, resource path, data path, frozen/source mode, and whether the data directory is writable.

Benchmark the real local camera pipeline after the models are available:

```bash
python scripts/benchmark_pipeline.py --camera 0 --frames 120 --warmup 10
```

The benchmark reports average and p95 pipeline latency, approximate pipeline FPS, detected-face count, camera reconnects, and camera read failures. Calibrate recognition/liveness thresholds and performance on the actual deployment cameras rather than relying only on development-machine results.

## Troubleshooting

- **Camera not working**: Ensure the webcam is connected and not in use by another application. The application automatically tries a platform-preferred backend and OpenCV's default backend.
- **Camera disconnects during attendance**: The resilient capture layer attempts reconnection after repeated failed reads. Check `logs/app.log` if it cannot recover.
- **Face not detected**: Improve lighting and keep the full face visible.
- **Liveness unavailable**: Run `python scripts/download_face_models.py` while online or set the liveness model environment variables to verified local files.
- **Spoof result on a real face**: Improve frontal lighting, reduce glare, avoid an overexposed display behind the face, and try again. Thresholds should be calibrated on the target cameras before deployment.
- **Recognition issues**: Re-enroll the student with more varied, clear images.
- **Packaged app fails to start**: Run the packaged executable with `--diagnostics` and inspect the per-user `logs/app.log` file.

## Development

Install development dependencies:

```bash
python -m pip install -e ".[dev]"
```

Run tests and lint:

```bash
python -m pytest -q
python -m ruff check main.py tests scripts src/core/camera.py src/core/runtime.py src/core/paths.py
```

Build and smoke-test the native bundle:

```bash
make package-smoke
```

CI additionally builds the frozen application on Windows, macOS, and Linux.

## License

Application source code is licensed under the MIT License. Runtime model files have their own upstream licenses and attribution; see [MODEL_LICENSES.md](MODEL_LICENSES.md).

## Acknowledgements

- [OpenCV](https://opencv.org/) and OpenCV Zoo for YuNet and SFace
- Minivision AI's Silent-Face-Anti-Spoofing project for the MiniFAS anti-spoofing architecture and weights
- [yakhyo/face-anti-spoofing](https://github.com/yakhyo/face-anti-spoofing) for lightweight ONNX MiniFAS exports
- [customtkinter](https://github.com/TomSchimansky/CustomTkinter) for UI components
