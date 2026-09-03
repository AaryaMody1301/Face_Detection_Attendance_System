"""Canonical YuNet + SFace detection and recognition engine."""
from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict, deque
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from src.core.face_models import SFACE, YUNET, ModelUnavailableError, resolve_model
from src.core.paths import TRAINING_MODELS_DIR, ensure_runtime_dirs

logger = logging.getLogger(__name__)

DEFAULT_GALLERY_PATH = TRAINING_MODELS_DIR / "face_gallery.npz"
SFACE_COSINE_THRESHOLD = 0.363


class FaceEngine:
    """Single application API backed by OpenCV YuNet and SFace."""

    def __init__(
        self,
        detection_method: str = "yunet",
        recognition_method: str = "sface",
        scale_factor: float = 1.0,
        min_face_size: int = 20,
        confidence_threshold: float = SFACE_COSINE_THRESHOLD,
        detector_score_threshold: float = 0.9,
        nms_threshold: float = 0.3,
        top_k: int = 5000,
        auto_download_models: bool = True,
        yunet_model_path: str | Path | None = None,
        sface_model_path: str | Path | None = None,
        **legacy_options: Any,
    ) -> None:
        ensure_runtime_dirs()

        detection_method = legacy_options.pop("detection_model", detection_method)
        detection_method = legacy_options.pop("method", detection_method)
        confidence_threshold = legacy_options.pop("threshold", confidence_threshold)
        legacy_options.pop("students_csv_path", None)

        requested_detection = str(detection_method).lower()
        requested_recognition = str(recognition_method).lower()
        if requested_detection not in {"yunet", "auto"}:
            logger.info("Mapping legacy detector '%s' to YuNet", requested_detection)
        if requested_recognition not in {"sface", "embedding", "hybrid"}:
            logger.info("Mapping legacy recognizer '%s' to SFace", requested_recognition)
        if legacy_options:
            logger.debug("Ignoring legacy FaceDetector options: %s", sorted(legacy_options))

        self.detection_method = "yunet"
        self.recognition_method = "sface"
        self.scale_factor = float(scale_factor)
        self.min_face_size = max(10, int(min_face_size))
        self.confidence_threshold = float(confidence_threshold)
        self.detector_score_threshold = float(detector_score_threshold)
        self.nms_threshold = float(nms_threshold)
        self.top_k = int(top_k)
        self.auto_download_models = bool(auto_download_models)

        self._yunet_model_path = Path(yunet_model_path).expanduser() if yunet_model_path else None
        self._sface_model_path = Path(sface_model_path).expanduser() if sface_model_path else None
        self._detector: Any | None = None
        self._recognizer: Any | None = None
        self._model_lock = threading.RLock()

        self._embeddings = np.empty((0, 0), dtype=np.float32)
        self.known_face_encodings: list[np.ndarray] = []
        self.known_face_names: list[str] = []
        self.known_face_ids: list[str] = []

        self.detection_times: deque[float] = deque(maxlen=30)
        self.recognition_times: deque[float] = deque(maxlen=30)

    @property
    def detection_model(self) -> str:
        """Historical attribute retained for old UI/controller callers."""
        return self.detection_method

    @property
    def model_ready(self) -> bool:
        return self._detector is not None and self._recognizer is not None

    @staticmethod
    def _normalize_frame(frame: Any) -> Any:
        if frame is not None and getattr(frame, "ndim", 0) == 2:
            return cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        return frame

    @staticmethod
    def _is_valid_frame(frame: Any) -> bool:
        return (
            frame is not None
            and isinstance(frame, np.ndarray)
            and frame.size > 0
            and frame.ndim == 3
            and frame.shape[2] >= 3
        )

    def _resolve_model_path(self, explicit: Path | None, spec: Any) -> Path:
        if explicit is not None:
            path = explicit.expanduser().resolve()
            if not path.is_file():
                raise ModelUnavailableError(f"Missing {spec.name} model: {path}")
            return path
        return resolve_model(spec, allow_download=self.auto_download_models)

    def _ensure_detector(self) -> None:
        if self._detector is not None:
            return
        with self._model_lock:
            if self._detector is not None:
                return
            model_path = self._resolve_model_path(self._yunet_model_path, YUNET)
            self._detector = cv2.FaceDetectorYN.create(
                str(model_path),
                "",
                (320, 320),
                self.detector_score_threshold,
                self.nms_threshold,
                self.top_k,
            )

    def _ensure_recognizer(self) -> None:
        if self._recognizer is not None:
            return
        with self._model_lock:
            if self._recognizer is not None:
                return
            model_path = self._resolve_model_path(self._sface_model_path, SFACE)
            self._recognizer = cv2.FaceRecognizerSF.create(str(model_path), "")

    def ensure_models(self) -> None:
        """Load both network models, downloading pinned copies if necessary."""
        self._ensure_detector()
        self._ensure_recognizer()

    def _detect_rows(self, frame: Any) -> np.ndarray:
        frame = self._normalize_frame(frame)
        if not self._is_valid_frame(frame):
            return np.empty((0, 15), dtype=np.float32)

        self._ensure_detector()
        height, width = frame.shape[:2]
        start = time.perf_counter()
        with self._model_lock:
            self._detector.setInputSize((width, height))
            _, faces = self._detector.detect(frame)
        self.detection_times.append(time.perf_counter() - start)

        if faces is None or len(faces) == 0:
            return np.empty((0, 15), dtype=np.float32)
        rows = np.asarray(faces, dtype=np.float32)
        keep = [
            row
            for row in rows
            if float(row[2]) >= self.min_face_size and float(row[3]) >= self.min_face_size
        ]
        return np.asarray(keep, dtype=np.float32) if keep else np.empty((0, 15), dtype=np.float32)

    @staticmethod
    def _row_to_location(row: np.ndarray) -> tuple[int, int, int, int]:
        x, y, width, height = (round(float(value)) for value in row[:4])
        return (max(0, y), max(0, x + width), max(0, y + height), max(0, x))

    def detect_faces(self, frame: Any) -> list[tuple[int, int, int, int]]:
        """Return face boxes as ``(top, right, bottom, left)`` tuples."""
        return [self._row_to_location(row) for row in self._detect_rows(frame)]

    def detect_faces_only(self, frame: Any) -> list[tuple[int, int, int, int]]:
        return self.detect_faces(frame)

    @staticmethod
    def _normalize_embedding(feature: Any) -> np.ndarray:
        vector = np.asarray(feature, dtype=np.float32).reshape(-1)
        norm = float(np.linalg.norm(vector))
        if norm <= 1e-12:
            raise ValueError("SFace returned an empty embedding")
        return vector / norm

    def _feature_from_row(self, frame: np.ndarray, row: np.ndarray) -> np.ndarray:
        self._ensure_recognizer()
        with self._model_lock:
            aligned = self._recognizer.alignCrop(frame, row)
            feature = self._recognizer.feature(aligned)
        return self._normalize_embedding(feature)

    def compute_face_embeddings(
        self,
        frame: Any,
        face_locations: Iterable[Any] | None = None,
    ) -> list[np.ndarray]:
        """Compute aligned SFace embeddings for faces in a frame."""
        normalized = self._normalize_frame(frame)
        if not self._is_valid_frame(normalized):
            return []
        rows = self._detect_rows(normalized)
        if face_locations is not None:
            requested = list(face_locations)
            rows = rows[: len(requested)]
        return [self._feature_from_row(normalized, row) for row in rows]

    @staticmethod
    def _parse_training_identity(path: Path) -> tuple[str, str] | None:
        parts = path.name.split(".")
        if len(parts) >= 3 and parts[0] and parts[1]:
            return parts[0], parts[1]
        if path.parent.name and "_" in path.stem:
            return path.parent.name, path.parent.name
        return None

    def _best_face_row(self, frame: np.ndarray) -> np.ndarray | None:
        rows = self._detect_rows(frame)
        if len(rows) == 0:
            return None
        return max(rows, key=lambda row: (float(row[14]), float(row[2] * row[3])))

    def _features_from_paths(self, image_paths: Iterable[str | Path]) -> list[np.ndarray]:
        features: list[np.ndarray] = []
        for raw_path in image_paths:
            path = Path(raw_path)
            frame = cv2.imread(str(path))
            if frame is None:
                logger.warning("Skipping unreadable training image: %s", path)
                continue
            row = self._best_face_row(frame)
            if row is None:
                logger.warning("No YuNet face found in training image: %s", path)
                continue
            try:
                features.append(self._feature_from_row(frame, row))
            except (cv2.error, ValueError) as exc:
                logger.warning("Could not embed training image %s: %s", path, exc)
        return features

    def _set_gallery(
        self,
        embeddings: np.ndarray,
        names: Iterable[str],
        student_ids: Iterable[str],
    ) -> None:
        matrix = np.asarray(embeddings, dtype=np.float32)
        if matrix.size == 0:
            self._embeddings = np.empty((0, 0), dtype=np.float32)
            self.known_face_encodings = []
            self.known_face_names = []
            self.known_face_ids = []
            return
        if matrix.ndim == 1:
            matrix = matrix.reshape(1, -1)
        matrix = np.vstack([self._normalize_embedding(row) for row in matrix])
        names_list = [str(value) for value in names]
        ids_list = [str(value) for value in student_ids]
        if len(matrix) != len(names_list) or len(matrix) != len(ids_list):
            raise ValueError("Face gallery embeddings and labels have different lengths")
        self._embeddings = matrix
        self.known_face_encodings = [row.copy() for row in matrix]
        self.known_face_names = names_list
        self.known_face_ids = ids_list

    def enroll_student(
        self,
        student_id: str,
        name: str,
        image_paths: Iterable[str | Path],
        *,
        model_path: str | Path | None = None,
    ) -> bool:
        """Create or replace one student's SFace template in the gallery."""
        features = self._features_from_paths(image_paths)
        if not features:
            return False
        template = self._normalize_embedding(np.mean(np.vstack(features), axis=0))

        retained = [
            index
            for index, existing_id in enumerate(self.known_face_ids)
            if str(existing_id) != str(student_id)
        ]
        embeddings = [self._embeddings[index] for index in retained] if retained else []
        names = [self.known_face_names[index] for index in retained]
        ids = [self.known_face_ids[index] for index in retained]
        embeddings.append(template)
        names.append(str(name))
        ids.append(str(student_id))
        self._set_gallery(np.vstack(embeddings), names, ids)

        if model_path is not None:
            return self.save_model(model_path)
        return True

    def train_recognizer(self, training_dir: str | Path) -> bool:
        """Build one averaged SFace template per identity from training images."""
        root = Path(training_dir)
        if not root.is_dir():
            return False

        grouped: dict[tuple[str, str], list[Path]] = defaultdict(list)
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
                continue
            identity = self._parse_training_identity(path)
            if identity is None:
                logger.warning("Skipping unrecognized training filename: %s", path.name)
                continue
            name, student_id = identity
            grouped[(str(student_id), str(name))].append(path)

        embeddings: list[np.ndarray] = []
        names: list[str] = []
        ids: list[str] = []
        for (student_id, name), paths in grouped.items():
            features = self._features_from_paths(paths)
            if not features:
                continue
            embeddings.append(self._normalize_embedding(np.mean(np.vstack(features), axis=0)))
            names.append(name)
            ids.append(student_id)

        if not embeddings:
            self._set_gallery(np.empty((0, 0), dtype=np.float32), [], [])
            return False
        self._set_gallery(np.vstack(embeddings), names, ids)
        return True

    def train_model(
        self,
        training_images_path: str | Path,
        training_labels_path: str | Path | None = None,
    ) -> dict[str, Any]:
        success = self.train_recognizer(training_images_path)
        if not success:
            return {"success": False, "message": "No usable YuNet/SFace training faces were found."}

        output_dir = Path(training_labels_path) if training_labels_path else TRAINING_MODELS_DIR
        output_dir.mkdir(parents=True, exist_ok=True)
        model_path = output_dir / "face_gallery.npz"
        saved = self.save_model(model_path)
        return {
            "success": bool(saved),
            "data": {"model_path": str(model_path)},
            "message": "SFace gallery trained and saved." if saved else "Gallery could not be saved.",
        }

    def save_model(self, model_path: str | Path) -> bool:
        """Save only embeddings and labels; ONNX network weights remain pinned separately."""
        if self._embeddings.size == 0:
            logger.error("Cannot save an empty SFace gallery")
            return False
        path = Path(model_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with path.open("wb") as handle:
                np.savez_compressed(
                    handle,
                    format_version=np.asarray([1], dtype=np.int32),
                    backend=np.asarray(["sface"]),
                    embeddings=self._embeddings.astype(np.float32),
                    names=np.asarray(self.known_face_names),
                    ids=np.asarray(self.known_face_ids),
                    cosine_threshold=np.asarray([self.confidence_threshold], dtype=np.float32),
                )
            return True
        except (OSError, ValueError) as exc:
            logger.error("Error saving SFace gallery %s: %s", path, exc)
            return False

    def load_model(self, model_path: str | Path) -> bool:
        path = Path(model_path)
        if not path.is_file():
            return False
        try:
            with np.load(path, allow_pickle=False) as data:
                backend = str(np.asarray(data["backend"]).reshape(-1)[0])
                if backend != "sface":
                    raise ValueError(f"Unsupported face gallery backend: {backend}")
                embeddings = np.asarray(data["embeddings"], dtype=np.float32)
                names = np.asarray(data["names"]).astype(str).tolist()
                ids = np.asarray(data["ids"]).astype(str).tolist()
                if "cosine_threshold" in data:
                    self.confidence_threshold = float(
                        np.asarray(data["cosine_threshold"]).reshape(-1)[0]
                    )
            self._set_gallery(embeddings, names, ids)
            return True
        except (OSError, KeyError, ValueError) as exc:
            logger.warning(
                "Could not load %s as a Phase-3 SFace gallery; retraining is required: %s",
                path,
                exc,
            )
            return False

    def load_default_gallery(self) -> bool:
        return self.load_model(DEFAULT_GALLERY_PATH)

    def _match_embedding(self, query: np.ndarray) -> tuple[str, str, float]:
        if self._embeddings.size == 0:
            return "Unknown", "", 0.0
        self._ensure_recognizer()
        query_feature = query.reshape(1, -1).astype(np.float32)
        best_index = -1
        best_score = -1.0
        distance_type = getattr(cv2, "FaceRecognizerSF_FR_COSINE", 0)
        with self._model_lock:
            for index, candidate in enumerate(self._embeddings):
                score = float(
                    self._recognizer.match(
                        query_feature,
                        candidate.reshape(1, -1).astype(np.float32),
                        distance_type,
                    )
                )
                if score > best_score:
                    best_score = score
                    best_index = index
        if best_index >= 0 and best_score >= self.confidence_threshold:
            return (
                self.known_face_names[best_index],
                self.known_face_ids[best_index],
                best_score,
            )
        return "Unknown", "", max(0.0, best_score)

    def recognize_faces(
        self,
        frame: Any,
        confidence_threshold: float | None = None,
    ) -> list[tuple[tuple[int, int, int, int], str, str, float]]:
        normalized = self._normalize_frame(frame)
        if not self._is_valid_frame(normalized):
            return []
        threshold = self.confidence_threshold
        if confidence_threshold is not None:
            self.confidence_threshold = float(confidence_threshold)

        start = time.perf_counter()
        try:
            results = []
            for row in self._detect_rows(normalized):
                location = self._row_to_location(row)
                try:
                    feature = self._feature_from_row(normalized, row)
                    name, student_id, score = self._match_embedding(feature)
                except (cv2.error, ValueError) as exc:
                    logger.warning("SFace recognition failed for one face: %s", exc)
                    name, student_id, score = "Unknown", "", 0.0
                if name == "Unknown":
                    results.append((location, "Unknown", "", 0.0))
                else:
                    results.append((location, name, student_id, score))
            return results
        finally:
            self.confidence_threshold = threshold
            self.recognition_times.append(time.perf_counter() - start)

    def detect_and_recognize(
        self,
        frame: Any,
    ) -> list[tuple[tuple[int, int, int, int], str, str, float]]:
        return self.recognize_faces(frame)

    def recognize_face(self, frame: Any) -> dict[str, Any] | None:
        recognized = [result for result in self.recognize_faces(frame) if result[1] != "Unknown"]
        if not recognized:
            return None
        _, name, student_id, confidence = max(recognized, key=lambda item: item[3])
        return {
            "student_id": student_id,
            "name": name,
            "confidence": float(confidence),
        }

    def get_performance_stats(self) -> dict[str, Any]:
        detection_avg = sum(self.detection_times) / max(1, len(self.detection_times))
        recognition_avg = sum(self.recognition_times) / max(1, len(self.recognition_times))
        return {
            "detection_method": self.detection_method,
            "recognition_method": self.recognition_method,
            "avg_detection_time": detection_avg,
            "avg_recognition_time": recognition_avg,
            "faces_stored": len(self.known_face_names),
        }

    def cleanup(self) -> None:
        self._set_gallery(np.empty((0, 0), dtype=np.float32), [], [])
        self.detection_times.clear()
        self.recognition_times.clear()
        with self._model_lock:
            self._detector = None
            self._recognizer = None


FaceDetector = FaceEngine
