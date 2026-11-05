"""ConfigStore 读写测试。"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import BaseModel, Field

from psi6.runtime.config import ConfigMigrations, ConfigStore


class SampleConfig(BaseModel):
    folder: Path = Field(default_factory=Path.home)
    retries: int = 3


def test_load_missing_returns_defaults(tmp_path: Path) -> None:
    store = ConfigStore(tmp_path)
    loaded = store.load(SampleConfig, app_name="demo")
    assert loaded.retries == 3


def test_roundtrip(tmp_path: Path) -> None:
    store = ConfigStore(tmp_path)
    original = SampleConfig(folder=tmp_path / "in", retries=9)
    store.save(original, app_name="demo")
    loaded = store.load(SampleConfig, app_name="demo")
    assert loaded.retries == 9
    assert loaded.folder == tmp_path / "in"


def test_replace_failure_keeps_the_previous_config(tmp_path: Path, monkeypatch) -> None:
    store = ConfigStore(tmp_path)
    store.save(SampleConfig(retries=4), app_name="demo")
    path = store.path_for("demo")
    before = path.read_text(encoding="utf-8")

    def fail_replace(_source: Path, _destination: Path) -> None:
        raise OSError("磁盘写入中断")

    monkeypatch.setattr("psi6.runtime.config.os.replace", fail_replace)
    try:
        store.save(SampleConfig(retries=1), app_name="demo")
    except OSError:
        pass
    else:
        raise AssertionError("替换失败时应把异常交给调用方")
    assert path.read_text(encoding="utf-8") == before
    assert "retries" in before


def test_save_does_not_leave_a_temp_file(tmp_path: Path) -> None:
    store = ConfigStore(tmp_path)
    store.save(SampleConfig(retries=4), app_name="demo")
    assert store.path_for("demo").is_file()
    assert list(tmp_path.rglob("*.tmp")) == []


def test_broken_file_falls_back(tmp_path: Path) -> None:
    store = ConfigStore(tmp_path)
    path = store.path_for("demo")
    path.parent.mkdir(parents=True)
    path.write_text("{not json", encoding="utf-8")
    loaded = store.load(SampleConfig, app_name="demo")
    assert loaded.retries == 3
    assert path.with_name("config.json.bak").is_file()


def test_broken_file_warns_before_falling_back(tmp_path: Path, caplog) -> None:
    import logging

    store = ConfigStore(tmp_path)
    path = store.path_for("demo")
    path.parent.mkdir(parents=True)
    path.write_text("{not json", encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger="psi6.runtime.config"):
        assert store.load(SampleConfig, app_name="demo").retries == 3
    assert "config.json" in caplog.text
    assert "备份" in caplog.text


def test_reserved_windows_names_are_rejected(tmp_path: Path) -> None:
    store = ConfigStore(tmp_path)
    for name in ("CON", "con.txt", "LPT1", "NUL "):
        with pytest.raises(ValueError, match="保留名"):
            store.path_for(name)
    with pytest.raises(ValueError, match="保留名"):
        store.data_path("demo", "com2.json")
    with pytest.raises(ValueError, match="保留名"):
        store.data_path("AUX", "settings.json")


def test_save_fsyncs_the_file_and_directory(tmp_path: Path, monkeypatch) -> None:
    from psi6.runtime import config

    calls: list[int] = []
    original = config.os.fsync

    def spy(fd: int) -> None:
        calls.append(fd)
        original(fd)

    monkeypatch.setattr(config.os, "fsync", spy)
    ConfigStore(tmp_path).save(SampleConfig(), app_name="demo")
    expected = 1 if config.os.name == "nt" else 2
    assert len(calls) == expected


def test_app_name_cannot_escape_the_root(tmp_path: Path) -> None:
    store = ConfigStore(tmp_path)
    escaped = store.path_for("../evil")
    assert escaped.resolve().is_relative_to(tmp_path.resolve())
    escape_file = store.data_path("demo", "../escape.json")
    assert escape_file.resolve().is_relative_to(tmp_path.resolve())
    with pytest.raises(ValueError):
        store.path_for("..")


def test_migrations_upgrade_an_old_file(tmp_path: Path) -> None:
    class FolderConfig(BaseModel):
        version: int = 1
        folder: str = ""

    path = tmp_path / "demo" / "config.json"
    path.parent.mkdir()
    path.write_text('{"path": "C:/work"}', encoding="utf-8")
    migrations = ConfigMigrations()

    def rename_path(data: dict) -> dict:
        updated = dict(data)
        updated["folder"] = str(updated.pop("path", ""))
        return updated

    migrations.add(0, rename_path)
    loaded = ConfigStore(tmp_path).load(FolderConfig, app_name="demo", migrate=migrations)
    assert loaded.folder == "C:/work"
    assert loaded.version == 1


def test_failed_migration_falls_back_to_defaults(tmp_path: Path) -> None:
    path = tmp_path / "demo" / "config.json"
    path.parent.mkdir()
    path.write_text('{"retries": 9}', encoding="utf-8")
    migrations = ConfigMigrations()

    def broken(_data: dict) -> dict:
        raise RuntimeError("无法升级")

    migrations.add(0, broken)
    loaded = ConfigStore(tmp_path).load(SampleConfig, app_name="demo", migrate=migrations)
    assert loaded.retries == 3
    assert path.with_name("config.json.bak").is_file()


def test_load_data_runs_migrations(tmp_path: Path) -> None:
    store = ConfigStore(tmp_path)
    store.save_data("demo", "layout.json", {"side": "left"})
    migrations = ConfigMigrations()
    migrations.add(0, lambda data: {**data, "side": "right"})
    loaded = store.load_data("demo", "layout.json", migrate=migrations)
    assert loaded == {"side": "right", "version": 1}
