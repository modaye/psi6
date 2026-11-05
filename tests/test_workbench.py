"""三个原型共用工作区，并能离屏截图。"""

from __future__ import annotations

import threading
import time
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton, QSplitter, QWidget
from pytestqt.qtbot import QtBot

from psi6 import App
from psi6.examples.file_index import build
from psi6.examples.kit import KitWindow
from psi6.jobs.file_index import FileIndexParams
from psi6.theme.builtin import Compact
from psi6.ui.data_table import DataTable
from psi6.ui.empty_state import EmptyState
from psi6.ui.form import FormView
from psi6.ui.property_list import PropertyList
from psi6.ui.search_field import SearchField
from psi6.ui.window_shape import grab_rounded
from psi6.ui.workspace import Workspace


def test_file_index_is_a_workspace(qtbot: QtBot, tmp_path: Path) -> None:
    app = App("psi6-batch-proto", config_root=tmp_path)
    window = build(app)
    qtbot.addWidget(window)
    window.resize(880, 640)
    window.show()
    qtbot.waitExposed(window)
    work = window.findChild(Workspace, "psi6PrototypeBatch")
    assert work is not None
    assert work.breadcrumb.crumbs() == ["文件", "索引"]
    assert len(work.sizes()) == 2
    path = tmp_path / "batch.png"
    assert grab_rounded(window).save(str(path))
    assert path.stat().st_size > 0


def test_kit_prototypes_cover_shell_data_and_density(qtbot: QtBot, tmp_path: Path) -> None:
    app = App("psi6-kit-proto", config_root=tmp_path)
    window = KitWindow(app)
    qtbot.addWidget(window)
    window.resize(1180, 760)
    window.show()
    qtbot.waitExposed(window)

    window.show_page("theme")
    texts = [button.text() for button in window.findChildren(QPushButton)]
    assert "现代浅色" in texts
    assert "紧凑深色" in texts
    assert not any("Mono" in text or "Obsidian" in text for text in texts)

    window.show_page("shell")
    shell = window.findChild(Workspace, "psi6PrototypeShell")
    assert shell is not None
    assert shell.breadcrumb.crumbs() == ["工作区", "壳", "预览"]
    assert len(shell.sizes()) == 3
    assert shell.findChild(EmptyState) is not None
    assert any(label.text() == "路径无效" for label in shell.findChildren(QLabel))
    assert any("故意写长" in label.text() for label in shell.findChildren(QLabel))

    window.show_page("inspect")
    table = window.findChild(DataTable, "psi6PrototypeInspect")
    search = window.findChild(SearchField, "psi6PrototypeSearch")
    props = window.findChild(PropertyList, "psi6PrototypeProps")
    assert table is not None and search is not None and props is not None
    assert len(table.rows()) == 200
    assert "很长" in props.values()["说明"]
    table.sort_by("value", descending=True)
    assert table.visible_rows()[0]["value"] == 199
    search.setText("记录 001")
    assert [row["name"] for row in table.visible_rows()] == ["记录 001"]
    search.setText("没有这条记录")
    assert table.visible_rows() == []
    assert any(
        label.text() == "无匹配项"
        for label in table.findChildren(QLabel)
        if label.objectName() == "psi6EmptyTitle"
    )
    search.clear()
    table.select_row(0)

    window.show_page("formlab")
    groups = [
        label.text()
        for label in window.findChildren(QLabel)
        if label.objectName() == "psi6FormGroup"
    ]
    assert "扫描" in groups

    window.show_page("dense")
    assert window.findChild(DataTable, "psi6PrototypeDense") is not None
    assert any(splitter.count() == 3 for splitter in window.findChildren(QSplitter))

    for page_id in ("shell", "inspect", "dense"):
        window.show_page(page_id)
        path = tmp_path / f"{page_id}.png"
        assert grab_rounded(window).save(str(path))
        assert path.stat().st_size > 0


def _labeled(window: QWidget, text: str) -> QPushButton:
    found = [button for button in window.findChildren(QPushButton) if button.text() == text]
    assert len(found) == 1
    return found[0]


def test_file_index_start_fail_and_cancel(qtbot: QtBot, tmp_path: Path, monkeypatch) -> None:
    app = App("psi6-batch-flow", config_root=tmp_path)
    window = build(app)
    qtbot.addWidget(window)
    window.resize(880, 640)
    window.show()
    qtbot.waitExposed(window)
    form = window.findChild(FormView)
    table = window.findChild(DataTable)
    start = _labeled(window, "开始")
    cancel = _labeled(window, "取消")
    assert form is not None and table is not None

    folder = tmp_path / "docs"
    folder.mkdir()
    (folder / "a.txt").write_text("x", encoding="utf-8")
    form.restore(FileIndexParams(input_dir=folder, recursive=False))
    qtbot.mouseClick(start, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: any(row.get("name") == "a.txt" for row in table.rows()), timeout=5000)
    assert start.isEnabled()
    assert cancel.isEnabled() is False

    form.restore(FileIndexParams(input_dir=tmp_path / "missing-dir"))
    qtbot.mouseClick(start, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(
        lambda: app.notifier.last is not None and app.notifier.last[0] == "error",
        timeout=5000,
    )
    assert start.isEnabled()
    assert cancel.isEnabled() is False

    started = threading.Event()

    def block(_params, *, on_progress, on_log, is_cancelled) -> None:
        started.set()
        while not is_cancelled():
            time.sleep(0.02)
        raise InterruptedError

    monkeypatch.setattr("psi6.examples.file_index.run_file_index", block)
    form.restore(FileIndexParams(input_dir=folder))
    qtbot.mouseClick(start, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(started.is_set, timeout=3000)
    qtbot.mouseClick(cancel, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: app.runner.is_busy("index") is False, timeout=3000)
    assert window.isVisible()


def test_dense_prototype_uses_compact_and_can_split(qtbot: QtBot, tmp_path: Path) -> None:
    app = App("psi6-dense-proto", config_root=tmp_path, theme=Compact)
    window = KitWindow(app)
    qtbot.addWidget(window)
    window.resize(1180, 760)
    window.show()
    qtbot.waitExposed(window)
    window.show_page("dense")
    table = window.findChild(DataTable, "psi6PrototypeDense")
    assert table is not None
    splitter = table.parent()
    assert isinstance(splitter, QSplitter)
    assert splitter.count() == 3
    work = splitter.parent()
    assert isinstance(work, Workspace)
    assert work.layout() is not None
    assert work.layout().contentsMargins().left() == 10
    labels = {button.text() for button in work.toolbar.findChildren(QPushButton)}
    assert {"刷新", "标记", "导出"} <= labels
    qtbot.waitUntil(lambda: splitter.sizes()[1] > splitter.sizes()[0])
    before = splitter.sizes()[0]
    splitter.setSizes([before + 60, max(40, splitter.sizes()[1] - 60), splitter.sizes()[2]])
    qtbot.mouseRelease(splitter.handle(1), Qt.MouseButton.LeftButton)
    assert work.sizes()[0] != before
    assert work.sizes()[1] > 0
    path = tmp_path / "dense-compact.png"
    assert grab_rounded(window).save(str(path))
    assert path.stat().st_size > 0
    assert app.tokens.color_primary
