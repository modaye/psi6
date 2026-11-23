"""发布脚本：标签和包内容。"""

from __future__ import annotations

import importlib.util
import tarfile
import zipfile
from pathlib import Path

import pytest


def _load(name: str, relative: str):
    """按文件加载脚本，避免把 ``scripts`` 做成可导入包。"""

    path = Path(__file__).resolve().parents[1] / relative
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_dist = _load("psi6_check_dist", "scripts/check_dist.py")
_release = _load("psi6_check_release_version", "scripts/check_release_version.py")
SDIST_MARKERS = _dist.SDIST_MARKERS
WHEEL_MARKERS = _dist.WHEEL_MARKERS
_missing = _dist._missing
main = _dist.main
check = _release.check
tag_version = _release.tag_version


def test_tag_must_match_the_project_version() -> None:
    assert tag_version("refs/tags/v0.7.0") == "0.7.0"
    assert tag_version("refs/heads/main") is None
    assert check("refs/tags/v0.7.0", "push", "0.7.0") is None
    assert "不一致" in (check("refs/tags/v0.7.0", "push", "0.6.0") or "")
    assert "手动发布" in (check("refs/heads/main", "workflow_dispatch", "0.6.0") or "")
    assert check("", "", "0.6.0") is None


def test_archive_markers_notice_a_missing_icon(tmp_path: Path) -> None:
    assert _missing(["psi6/py.typed"], WHEEL_MARKERS)
    names = [f"pkg/{marker}" for marker in WHEEL_MARKERS]
    assert _missing(names, WHEEL_MARKERS) == []


def test_main_checks_one_wheel_and_one_sdist(tmp_path: Path) -> None:
    wheel = tmp_path / "psi6-0.6.0-py3-none-any.whl"
    sdist = tmp_path / "psi6-0.6.0.tar.gz"
    with zipfile.ZipFile(wheel, "w") as archive:
        for marker in WHEEL_MARKERS:
            archive.writestr(marker, b"")
    with tarfile.open(sdist, "w:gz") as archive:
        for marker in SDIST_MARKERS:
            info = tarfile.TarInfo(name=f"psi6-0.6.0/{marker}")
            archive.addfile(info)
    assert main([str(tmp_path)]) == 0


def test_main_rejects_an_incomplete_wheel(tmp_path: Path) -> None:
    wheel = tmp_path / "psi6-0.6.0-py3-none-any.whl"
    sdist = tmp_path / "psi6-0.6.0.tar.gz"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("psi6/__init__.py", b"")
    with tarfile.open(sdist, "w:gz") as archive:
        info = tarfile.TarInfo(name="psi6-0.6.0/pyproject.toml")
        archive.addfile(info)
    with pytest.raises(SystemExit, match=r"py\.typed"):
        main([str(tmp_path)])
