"""Verified runtime acquisition for the OpenCV Zoo YuNet and SFace models."""
from __future__ import annotations

import hashlib
import logging
import os
import shutil
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from src.core.paths import TRAINING_MODELS_DIR, ensure_runtime_dirs

logger = logging.getLogger(__name__)

OPENCV_ZOO_COMMIT = "47534e27c9851bb1128ccc0102f1145e27f23f98"
MODEL_CACHE_DIR = TRAINING_MODELS_DIR / "opencv_zoo"


class ModelUnavailableError(RuntimeError):
    """Raised when a required recognition model cannot be resolved safely."""


@dataclass(frozen=True)
class ModelSpec:
    """Pinned OpenCV Zoo model metadata."""

    name: str
    relative_path: str
    sha256: str
    size: int
    env_var: str

    @property
    def url(self) -> str:
        return (
            "https://github.com/opencv/opencv_zoo/raw/"
            f"{OPENCV_ZOO_COMMIT}/{self.relative_path}"
        )

    @property
    def filename(self) -> str:
        return Path(self.relative_path).name


YUNET = ModelSpec(
    name="YuNet",
    relative_path="models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
    sha256="8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4",
    size=232589,
    env_var="FACE_YUNET_MODEL",
)
SFACE = ModelSpec(
    name="SFace",
    relative_path="models/face_recognition_sface/face_recognition_sface_2021dec.onnx",
    sha256="0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79",
    size=38696353,
    env_var="FACE_SFACE_MODEL",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify(path: Path, spec: ModelSpec) -> bool:
    if not path.is_file() or path.stat().st_size != spec.size:
        return False
    return _sha256(path) == spec.sha256


def _explicit_model_path(spec: ModelSpec) -> Path | None:
    configured = os.environ.get(spec.env_var)
    if not configured:
        return None
    path = Path(configured).expanduser().resolve()
    if not path.is_file():
        raise ModelUnavailableError(
            f"{spec.env_var} points to a missing {spec.name} model: {path}"
        )
    return path


def resolve_model(
    spec: ModelSpec,
    *,
    cache_dir: str | Path | None = None,
    allow_download: bool = True,
) -> Path:
    """Resolve a model from an explicit override or a verified local cache."""
    explicit = _explicit_model_path(spec)
    if explicit is not None:
        return explicit

    ensure_runtime_dirs()
    destination_dir = Path(cache_dir or MODEL_CACHE_DIR).expanduser().resolve()
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / spec.filename

    if _verify(destination, spec):
        return destination
    if destination.exists():
        logger.warning("Removing invalid cached %s model: %s", spec.name, destination)
        destination.unlink()

    if not allow_download:
        raise ModelUnavailableError(
            f"{spec.name} model is not cached at {destination}. "
            "Run scripts/download_face_models.py while online or set "
            f"{spec.env_var} to a local model path."
        )

    temporary = destination.with_suffix(destination.suffix + ".part")
    temporary.unlink(missing_ok=True)
    logger.info("Downloading pinned %s model from OpenCV Zoo", spec.name)
    try:
        request = urllib.request.Request(
            spec.url,
            headers={"User-Agent": "Face-Detection-Attendance-System/1.2"},
        )
        with urllib.request.urlopen(request, timeout=120) as response, temporary.open("wb") as handle:
            shutil.copyfileobj(response, handle)
    except (OSError, urllib.error.URLError) as exc:
        temporary.unlink(missing_ok=True)
        raise ModelUnavailableError(
            f"Could not download the pinned {spec.name} model. "
            f"Set {spec.env_var} to a local model path for offline use."
        ) from exc

    if not _verify(temporary, spec):
        temporary.unlink(missing_ok=True)
        raise ModelUnavailableError(
            f"Downloaded {spec.name} model failed the pinned SHA-256/size check."
        )

    temporary.replace(destination)
    return destination


def ensure_face_models(
    *,
    cache_dir: str | Path | None = None,
    allow_download: bool = True,
) -> tuple[Path, Path]:
    """Return verified YuNet and SFace model paths."""
    return (
        resolve_model(YUNET, cache_dir=cache_dir, allow_download=allow_download),
        resolve_model(SFACE, cache_dir=cache_dir, allow_download=allow_download),
    )
