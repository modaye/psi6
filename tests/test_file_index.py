"""文件索引参考任务：空目录、过滤、上限、取消。"""

from __future__ import annotations

from pathlib import Path

import pytest

from psi6.jobs.file_index import FileIndexParams, run_file_index
from psi6.runtime.logs import LogLevel, LogRecord


def _run(params: FileIndexParams, *, cancelled: bool = False) -> tuple:
    logs: list[LogRecord] = []
    progress: list[tuple[int, int, str]] = []

    def is_cancelled() -> bool:
        return cancelled

    outcome = run_file_index(
        params,
        on_progress=lambda c, t, m: progress.append((c, t, m)),
        on_log=logs.append,
        is_cancelled=is_cancelled,
    )
    return outcome, logs, progress


def test_empty_directory(tmp_path: Path) -> None:
    outcome, logs, _ = _run(FileIndexParams(input_dir=tmp_path))
    assert outcome.rows == []
    assert "没有匹配" in outcome.message
    assert any(item.level is LogLevel.WARNING for item in logs)


def test_recursive_and_suffix(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("aa", encoding="utf-8")
    (tmp_path / "b.md").write_text("bb", encoding="utf-8")
    nested = tmp_path / "sub"
    nested.mkdir()
    (nested / "c.txt").write_text("cc", encoding="utf-8")

    all_rows, _, _ = _run(FileIndexParams(input_dir=tmp_path, recursive=True, suffix=""))
    assert {row["name"] for row in all_rows.rows} == {"a.txt", "b.md", "c.txt"}

    txt, _, _ = _run(FileIndexParams(input_dir=tmp_path, recursive=True, suffix="txt"))
    assert {row["name"] for row in txt.rows} == {"a.txt", "c.txt"}

    top, _, _ = _run(FileIndexParams(input_dir=tmp_path, recursive=False, suffix=""))
    assert {row["name"] for row in top.rows} == {"a.txt", "b.md"}


def test_max_files_truncates(tmp_path: Path) -> None:
    for index in range(4):
        (tmp_path / f"{index}.txt").write_text("x", encoding="utf-8")
    outcome, logs, _ = _run(FileIndexParams(input_dir=tmp_path, max_files=2))
    assert len(outcome.rows) == 2
    assert any("上限" in item.message for item in logs)


def test_missing_directory_raises(tmp_path: Path) -> None:
    missing = tmp_path / "nope"
    with pytest.raises(FileNotFoundError):
        _run(FileIndexParams(input_dir=missing))


def test_cancel_raises(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    with pytest.raises(InterruptedError):
        _run(FileIndexParams(input_dir=tmp_path), cancelled=True)
