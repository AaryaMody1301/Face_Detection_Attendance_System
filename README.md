# Face Detection Attendance System

A local-first facial-recognition attendance system built with Python, OpenCV, and customtkinter. Automatic attendance uses YuNet face detection, SFace identity matching, and MiniFAS passive liveness checks before a student can be marked present.

![Python Version](https://img.shields.io/badge/python-3.10--3.12-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![OpenCV](https://img.shields.io/badge/OpenCV-4.x-red)

## Features

- **Liveness-gated attendance**: Print and screen presentation attacks are checked before SFace identity matching
- **YuNet + SFace recognition**: OpenCV-native face detection, alignment, embeddings, and cosine matching
- **Temporal anti-spoofing**: A face must pass repeated MiniFAS liveness checks before automatic recognition is allowed
- **Student registration and training**: Capture images and build the local SFace gallery
- **SQLite-first attendance data**: Attendance and student records use the local database; CSV files are compatibility exports
- **Attendance management**: View, filter, and export attendance records
- **Modern UI**: Light/dark UI plus a retained classic compatibility path
- **Analytics dashboard**: Visualize attendance statistics and patterns
- **Local model inference**: No cloud recognition API or paid service is required
- **Multi-platform**: Windows, macOS, and Linux

## Security model

Automatic attendance follows this order:

1. YuNet detects the face.
2. MiniFASNet V2 + V1SE classify the face crop as live, paper spoof, or screen spoof.
3. A short temporal gate requires repeated live results for the same spatial face track.
4. Only after liveness passes does SFace compute and match the identity embedding.
5. Attendance is stored with method `sface+liveness`.

If the liveness models are unavailable or fail verification, automatic attendance fails closed. Manual attendance remains an explicit operator action.

Passive RGB liveness reduces common printed-photo and screen-replay attacks, but it is not a certified biometric presentation-attack-detection system and should not be treated as equivalent to dedicated IR/depth hardware.

## Screenshots

<p align="center">
  <img src="assets/screenshots/dashboard.png" alt="Dashboard" width="45%">
  <img src="assets/screenshots/attendance.png" alt="Attendance Module" width="45%">
</p>

## Installation

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

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Optionally preload and verify all face models:

   ```bash
   python scripts/download_face_models.py
   ```

5. Run the application:

   ```bash
   python main.py
   ```

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
6. Manual attendance remains available when operator review is required.

### Command-line attendance

```bash
python -m src.cli.take_attendance "Data Science"
```

Useful controls include `--threshold`, `--liveness-threshold`, `--liveness-frames`, `--liveness-window`, `--timeout`, and `--late-threshold`.

## Data and model locations

Mutable runtime data is stored under `Data/` by default and can be moved with `FACE_ATTENDANCE_DATA_DIR`.

Important generated paths include:

```text
Data/
├── attendance.db
├── exports/
├── logs/
├── models/
│   ├── face_gallery.npz
│   ├── opencv_zoo/
│   └── anti_spoof/
└── training_images/
```

## Troubleshooting

- **Camera not working**: Ensure the webcam is connected and not in use by another application.
- **Face not detected**: Improve lighting and keep the full face visible.
- **Liveness unavailable**: Run `python scripts/download_face_models.py` while online or set the liveness model environment variables to verified local files.
- **Spoof result on a real face**: Improve frontal lighting, reduce glare, avoid an overexposed display behind the face, and try again. Thresholds should be calibrated on the target cameras before deployment.
- **Recognition issues**: Re-enroll the student with more varied, clear images.
- **OpenCV errors**: Install the project dependencies from `requirements.txt`; the supported package is `opencv-contrib-python`.

## Development

Run the test suite:

```bash
python -m pytest -q
```

Run the same focused lint used by CI through the workflow configuration in `.github/workflows/ci.yml`.

## License

Application source code is licensed under the MIT License. Runtime model files have their own upstream licenses and attribution; see [MODEL_LICENSES.md](MODEL_LICENSES.md).

## Acknowledgements

- [OpenCV](https://opencv.org/) and OpenCV Zoo for YuNet and SFace
- Minivision AI's Silent-Face-Anti-Spoofing project for the MiniFAS anti-spoofing architecture and weights
- [yakhyo/face-anti-spoofing](https://github.com/yakhyo/face-anti-spoofing) for lightweight ONNX MiniFAS exports
- [customtkinter](https://github.com/TomSchimansky/CustomTkinter) for UI components
