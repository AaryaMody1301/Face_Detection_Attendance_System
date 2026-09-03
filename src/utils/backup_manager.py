"""Local backup management for application data and face enrollment state."""
from __future__ import annotations

import logging
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from src.core.paths import (
    BACKUPS_DIR,
    CONFIG_DIR,
    DATABASE_PATH,
    TRAINING_IMAGES_DIR,
    TRAINING_MODELS_DIR,
    ensure_runtime_dirs,
)
from src.core.utils.config_manager import ConfigManager

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BackupResult:
    success: bool
    message: str


class BackupManager:
    """Create local, consistent backups under the canonical application-data root."""

    def __init__(
        self,
        *,
        database_path: str | Path | None = None,
        backup_root: str | Path | None = None,
        config_path: str | Path | None = None,
        models_dir: str | Path | None = None,
        training_images_dir: str | Path | None = None,
    ) -> None:
        ensure_runtime_dirs()
        self.database_path = Path(database_path or DATABASE_PATH).expanduser().resolve()
        self.backup_root = Path(backup_root or BACKUPS_DIR).expanduser().resolve()
        self.config_path = Path(config_path or (CONFIG_DIR / "config.json")).expanduser().resolve()
        self.models_dir = Path(models_dir or TRAINING_MODELS_DIR).expanduser().resolve()
        self.training_images_dir = Path(training_images_dir or TRAINING_IMAGES_DIR).expanduser().resolve()
        self.backup_root.mkdir(parents=True, exist_ok=True)

        config = ConfigManager(config_path=self.config_path)
        self.auto_backup = bool(config.get("backup.auto_backup", True))
        self.frequency_days = max(1, int(config.get("backup.frequency_days", 7)))
        self.retention_days = max(1, int(config.get("backup.retention_days", 30)))
        self.last_backup_file = self.backup_root / ".last_backup"

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(UTC).astimezone().strftime("%Y%m%d_%H%M%S")

    def should_backup(self) -> bool:
        if not self.auto_backup:
            return False
        if not self.last_backup_file.is_file():
            return True
        try:
            last = datetime.fromisoformat(self.last_backup_file.read_text(encoding="utf-8").strip())
            if last.tzinfo is None:
                last = last.replace(tzinfo=UTC)
            return datetime.now(UTC) - last.astimezone(UTC) >= timedelta(days=self.frequency_days)
        except (OSError, ValueError):
            return True

    def _backup_database(self, target_dir: Path) -> BackupResult:
        if not self.database_path.is_file():
            return BackupResult(True, "No SQLite database exists yet")
        target = target_dir / "attendance.db"
        try:
            source = sqlite3.connect(str(self.database_path), timeout=30.0)
            destination = sqlite3.connect(str(target), timeout=30.0)
            try:
                source.backup(destination)
                violations = destination.execute("PRAGMA integrity_check").fetchone()
                if not violations or violations[0] != "ok":
                    raise sqlite3.IntegrityError(f"Backup integrity check failed: {violations}")
            finally:
                destination.close()
                source.close()
            return BackupResult(True, f"Database backed up to {target}")
        except sqlite3.Error as exc:
            logger.error("Database backup failed: %s", exc)
            target.unlink(missing_ok=True)
            return BackupResult(False, f"Database backup failed: {exc}")

    @staticmethod
    def _copy_optional_file(source: Path, destination: Path) -> None:
        if source.is_file():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

    @staticmethod
    def _copy_optional_tree(source: Path, destination: Path) -> None:
        if source.is_dir():
            shutil.copytree(source, destination, dirs_exist_ok=True)

    def perform_backup(self) -> BackupResult:
        timestamp = self._timestamp()
        target_dir = self.backup_root / f"backup_{timestamp}"
        target_dir.mkdir(parents=True, exist_ok=False)
        messages: list[str] = []
        try:
            database_result = self._backup_database(target_dir)
            messages.append(database_result.message)
            if not database_result.success:
                shutil.rmtree(target_dir, ignore_errors=True)
                return database_result

            self._copy_optional_file(self.config_path, target_dir / "config" / "config.json")
            self._copy_optional_tree(self.models_dir, target_dir / "models")
            self._copy_optional_tree(self.training_images_dir, target_dir / "training_images")

            self.last_backup_file.write_text(datetime.now(UTC).isoformat(), encoding="utf-8")
            messages.append(f"Runtime state backed up to {target_dir}")
            return BackupResult(True, "\n".join(messages))
        except OSError as exc:
            shutil.rmtree(target_dir, ignore_errors=True)
            logger.error("Backup failed: %s", exc)
            return BackupResult(False, f"Backup failed: {exc}")

    def clean_old_backups(self, max_days: int | None = None) -> BackupResult:
        retention = max(1, int(max_days or self.retention_days))
        cutoff = datetime.now(UTC).timestamp() - timedelta(days=retention).total_seconds()
        removed = 0
        try:
            for path in self.backup_root.glob("backup_*"):
                try:
                    if path.stat().st_mtime >= cutoff:
                        continue
                    if path.is_dir():
                        shutil.rmtree(path)
                    else:
                        path.unlink()
                    removed += 1
                except OSError as exc:
                    logger.warning("Could not remove old backup %s: %s", path, exc)
            return BackupResult(True, f"Removed {removed} backup set(s) older than {retention} days")
        except OSError as exc:
            return BackupResult(False, f"Could not clean old backups: {exc}")


__all__ = ["BackupManager", "BackupResult"]
