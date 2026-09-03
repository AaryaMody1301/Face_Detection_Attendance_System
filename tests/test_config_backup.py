from __future__ import annotations

import sqlite3

from src.core.utils.config_manager import ConfigManager
from src.core.version import get_version
from src.utils.backup_manager import BackupManager


def test_config_normalizes_supported_production_backends(tmp_path):
    config_path = tmp_path / "config.json"
    manager = ConfigManager(config_path=config_path)

    assert manager.get("app.version") == get_version()
    assert manager.get("ui.type") == "modern"
    assert manager.get("face_detection.detection_method") == "yunet"
    assert manager.get("face_recognition.method") == "sface"
    assert manager.get("liveness.enabled") is True

    assert manager.update_config({"face_recognition": {"threshold": 0.41}}) is True
    reloaded = ConfigManager(config_path=config_path)
    assert reloaded.get("face_recognition.threshold") == 0.41


def test_backup_uses_sqlite_backup_and_includes_runtime_state(tmp_path):
    database_path = tmp_path / "attendance.db"
    connection = sqlite3.connect(database_path)
    connection.execute("CREATE TABLE sample(value TEXT NOT NULL)")
    connection.execute("INSERT INTO sample(value) VALUES ('present')")
    connection.commit()
    connection.close()

    config_path = tmp_path / "config" / "config.json"
    ConfigManager(config_path=config_path)
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    (models_dir / "face_gallery.npz").write_bytes(b"gallery")
    training_dir = tmp_path / "training_images"
    training_dir.mkdir()
    (training_dir / "student.jpg").write_bytes(b"image")

    backup_root = tmp_path / "backups"
    manager = BackupManager(
        database_path=database_path,
        backup_root=backup_root,
        config_path=config_path,
        models_dir=models_dir,
        training_images_dir=training_dir,
    )
    result = manager.perform_backup()

    assert result.success is True
    backup_sets = list(backup_root.glob("backup_*"))
    assert len(backup_sets) == 1
    backup = backup_sets[0]
    backed_up_db = sqlite3.connect(backup / "attendance.db")
    try:
        assert backed_up_db.execute("SELECT value FROM sample").fetchone()[0] == "present"
    finally:
        backed_up_db.close()
    assert (backup / "config" / "config.json").is_file()
    assert (backup / "models" / "face_gallery.npz").is_file()
    assert (backup / "training_images" / "student.jpg").is_file()
