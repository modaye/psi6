"""JobWindow：结果进表、配置可记住目录。"""

from __future__ import annotations

import time
from pathlib import Path

from pydantic import BaseModel, Field
from pytestqt.qtbot import QtBot

from psi6.jobs.file_index import FILE_INDEX_COLUMNS, FileIndexParams, run_file_index
from psi6.runtime.app import App
from psi6.runtime.job import JobOutcome
from psi6.runtime.logs import LogLevel, LogRecord
from psi6.runtime.tasks import TaskStatus
from psi6.templates.batch_tool import BatchToolWindow
from psi6.ui.data_table import TableColumn


class Params(BaseModel):
    folder: Path = Field(json_schema_extra={"kind": "dir"}, description="目录")


def test_batch_window_runs(qtbot: QtBot, tmp_path: Path) -> None:
    app = App("psi6-test", config_root=tmp_path / "cfg")
    window = BatchToolWindow(
        title="test",
        params=Params(folder=tmp_path),
        job=lambda params, on_progress, on_log, is_cancelled: (
            on_log(LogRecord(LogLevel.SUCCESS, "done"))
            or JobOutcome(rows=[{"name": "x"}], message="完成，共 1 项")
        ),
        app=app,
        result_columns=[TableColumn("name", "名称")],
        persist_config=False,
    )
    qtbot.addWidget(window)
    assert window.form is not None
    window._start()
    qtbot.waitUntil(
        lambda: window._handle is None or window._handle.status is not TaskStatus.RUNNING,
        timeout=3000,
    )
    assert window.log.count_by_level()[LogLevel.SUCCESS] == 1
    assert window.table.rows()[0]["name"] == "x"


def test_file_index_window_fills_table(qtbot: QtBot, tmp_path: Path) -> None:
    (tmp_path / "note.txt").write_text("hello", encoding="utf-8")
    app = App("psi6-index-ui", config_root=tmp_path / "cfg")
    window = BatchToolWindow(
        title="index",
        params=FileIndexParams(input_dir=tmp_path, recursive=False),
        job=run_file_index,
        app=app,
        result_columns=FILE_INDEX_COLUMNS,
        persist_config=True,
    )
    qtbot.addWidget(window)
    window._start()
    qtbot.waitUntil(lambda: window._handle is None, timeout=5000)
    names = {row["name"] for row in window._table.rows()}
    assert "note.txt" in names
    assert ".txt" in {tag.text() for tag in window._tags._tags}
    loaded = app.load_config(FileIndexParams)
    assert loaded.input_dir == tmp_path


def test_batch_window_exclusive_and_icon(qtbot: QtBot, tmp_path: Path) -> None:
    app = App("psi6-exclusive", config_root=tmp_path / "cfg")
    started = 0

    def job(params, on_progress, on_log, is_cancelled):  # noqa: ANN001
        nonlocal started
        started += 1
        while not is_cancelled():
            time.sleep(0.02)
        raise InterruptedError

    window = BatchToolWindow(
        title="scan",
        params=Params(folder=tmp_path),
        job=job,
        app=app,
        result_columns=[TableColumn("name", "名称")],
        persist_config=False,
        icon="search",
        exclusive="scan",
    )
    qtbot.addWidget(window)
    assert window.exclusive == "scan"
    assert window.title_bar.icon_name == "search"
    assert window.task_panel._cancel.objectName() == "psi6Ghost"
    window._start()
    qtbot.waitUntil(lambda: started >= 1, timeout=3000)
    assert app.runner.is_busy("scan") is True
    window._start()
    assert started == 1
    assert window.handle is not None
    window.handle.cancel()
    qtbot.waitUntil(lambda: window.handle is None, timeout=3000)
    assert app.runner.is_busy("scan") is False
