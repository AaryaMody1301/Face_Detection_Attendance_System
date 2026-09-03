"""Regression tests for packaged runtime bootstrap and diagnostics."""
from __future__ import annotations

from pathlib import Path

from src.core import runtime


def test_packaged_runtime_seeds_resources_without_overwriting_config(tmp_path, monkeypatch):
    resource_root = tmp_path / "bundle"
    data_root = tmp_path / "user-data"
    assets = resource_root / "assets"
    default_config = resource_root / "config" / "config.json"
    assets.mkdir(parents=True)
    default_config.parent.mkdir(parents=True)
    (assets / "icon.txt").write_text("bundled-icon", encoding="utf-8")
    default_config.write_text('{"theme": "dark"}', encoding="utf-8")

    config_dir = data_root / "config"
    config_dir.mkdir(parents=True)
    runtime_config = config_dir / "config.json"
    runtime_config.write_text('{"theme": "user"}', encoding="utf-8")

    changed_to = []
    monkeypatch.setattr(runtime, "IS_FROZEN", True)
    monkeypatch.setattr(runtime, "ASSETS_ROOT", assets)
    monkeypatch.setattr(runtime, "DATA_ROOT", data_root)
    monkeypatch.setattr(runtime, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(runtime, "DEFAULT_CONFIG_PATH", default_config)
    monkeypatch.setattr(runtime, "ensure_runtime_dirs", lambda: data_root.mkdir(parents=True, exist_ok=True))
    monkeypatch.setattr(runtime.os, "chdir", lambda path: changed_to.append(Path(path)))

    assert runtime.prepare_runtime_environment() == data_root
    assert (data_root / "assets" / "icon.txt").read_text(encoding="utf-8") == "bundled-icon"
    assert runtime_config.read_text(encoding="utf-8") == '{"theme": "user"}'
    assert changed_to == [data_root]


def test_runtime_diagnostics_confirms_data_directory_is_writable(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "DATA_ROOT", tmp_path)
    diagnostics = runtime.runtime_diagnostics()

    assert diagnostics["data_root"] == str(tmp_path)
    assert diagnostics["data_root_writable"] is True
    assert "python" in diagnostics
    assert "platform" in diagnostics
    assert not (tmp_path / ".write-test").exists()
