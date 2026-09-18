"""ConfigStore 读写测试。"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from psi6.runtime.config import ConfigStore


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


def test_broken_file_falls_back(tmp_path: Path) -> None:
    store = ConfigStore(tmp_path)
    path = store.path_for("demo")
    path.parent.mkdir(parents=True)
    path.write_text("{not json", encoding="utf-8")
    loaded = store.load(SampleConfig, app_name="demo")
    assert loaded.retries == 3
    assert path.with_name("config.json.bak").is_file()
