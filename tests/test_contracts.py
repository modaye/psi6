"""0.2.0 行为契约：多开、坏配置、主题诊断、销毁后的回调、退出与无托盘。"""

from __future__ import annotations

import importlib
import threading
import time
from pathlib import Path

from pydantic import BaseModel
from pytestqt.qtbot import QtBot
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QLabel, QWidget

from psi6.api import OPTIONAL_UI, STABLE
from psi6.icons.export import svg_dir
from psi6.icons.render import pixmap_for, raster_px
from psi6.runtime.app import App
from psi6.runtime.config import ConfigStore
from psi6.runtime.tasks import TaskRunner, TaskStatus
from psi6.runtime.window_state import restore_window
from psi6.theme.diagnose import contrast_notes
from psi6.theme.theme import Theme
from psi6.theme.tokens import Tokens
from psi6.ui.desktop_window import DesktopWindow


class Prefs(BaseModel):
    retries: int = 1


def test_two_apps_keep_separate_config(tmp_path: Path) -> None:
    first = App("psi6-a", config_root=tmp_path)
    second = App("psi6-b", config_root=tmp_path)
    first.save_config(Prefs(retries=3))
    assert second.load_config(Prefs).retries == 1
    assert first._instance is None
    assert second._instance is None


def test_corrupt_window_geometry_does_not_block_startup(qtbot: QtBot, tmp_path: Path) -> None:
    store = ConfigStore(tmp_path)
    store.save_data("geo", "window.json", {"geometry": "不是合法几何", "maximized": True})
    window = QWidget()
    qtbot.addWidget(window)
    window.resize(400, 300)
    assert restore_window(window, store, "geo") is False
    assert window.width() == 400


def test_contrast_note_does_not_reject_theme() -> None:
    class Pale(Theme):
        name = "pale"
        color_text = "#f4f4f4"
        color_bg = "#ffffff"

    tokens = Pale().tokens()
    assert tokens.color_text == "#f4f4f4"
    assert contrast_notes(tokens)
    assert contrast_notes(Tokens.light()) == []


def test_callback_after_widget_deleted_does_not_fail(qtbot: QtBot) -> None:
    runner = TaskRunner()
    label = QLabel("活着")
    label.deleteLater()
    qtbot.waitUntil(lambda: not _alive(label), timeout=2000)
    handle = runner.submit(lambda: "done", on_succeeded=lambda _value: label.setText("晚到"))
    qtbot.waitUntil(lambda: handle.status is TaskStatus.SUCCEEDED, timeout=3000)


def _alive(widget: QWidget) -> bool:
    from psi6.runtime.qt_alive import qt_alive

    return qt_alive(widget)


def test_high_dpi_policy_is_passthrough() -> None:
    assert (
        QGuiApplication.highDpiScaleFactorRoundingPolicy()
        == Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )


def test_icon_raster_keeps_logical_size() -> None:
    assert raster_px(16, 2) == 32
    assert raster_px(16, 1.5) == 24
    assert raster_px(16, 0.5) == 16
    pix = pixmap_for("search", color="#222222", size=16, ratio=2)
    assert pix.devicePixelRatio() == 2
    assert pix.width() == 32
    assert pix.deviceIndependentSize().width() == 16


def test_quit_order_is_geometry_runner_lock_tray(qtbot: QtBot, tmp_path: Path, monkeypatch) -> None:
    order: list[str] = []
    app = App("psi6-quit-order", config_root=tmp_path)
    window = QWidget()
    qtbot.addWidget(window)
    app._window = window
    app._restore_geometry = True
    monkeypatch.setattr("psi6.runtime.app.save_window", lambda *_args: order.append("geometry"))

    def shutdown(*_args: object, **_kwargs: object) -> bool:
        order.append("runner")
        return True

    app.runner.shutdown = shutdown  # type: ignore[method-assign]

    class Lock:
        def close(self) -> None:
            order.append("lock")

    class Tray:
        def hide(self) -> None:
            order.append("tray")

    app._instance = Lock()  # type: ignore[assignment]
    app.tray = Tray()  # type: ignore[assignment]
    app._on_quit()
    assert order == ["geometry", "runner", "lock", "tray"]


def test_file_index_page_separates_close_cancel_and_quit(qtbot: QtBot, tmp_path: Path, monkeypatch) -> None:
    """关窗口、点取消、应用退出是三件事。页面用文件索引的开始/取消按钮。"""

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QPushButton

    from psi6.examples.file_index import build

    started = threading.Event()

    def block(_params, *, on_progress, on_log, is_cancelled) -> None:  # noqa: ARG001
        started.set()
        while not is_cancelled():
            time.sleep(0.02)
        raise InterruptedError

    monkeypatch.setattr("psi6.examples.file_index.run_file_index", block)
    app = App("psi6-index-life", config_root=tmp_path)
    window = build(app)
    qtbot.addWidget(window)
    window.show()
    app.qt_app.setQuitOnLastWindowClosed(False)
    start = _labeled(window, QPushButton, "开始")
    cancel = _labeled(window, QPushButton, "取消")

    qtbot.mouseClick(start, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(started.is_set, timeout=3000)
    handle = app.runner.active_handles()[-1]
    window.close()
    qtbot.wait(80)
    assert handle.cancel_requested is False
    assert handle.status is TaskStatus.RUNNING

    window.show()
    qtbot.mouseClick(cancel, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: handle.status is TaskStatus.CANCELLED, timeout=3000)
    assert handle.cancel_requested is True
    assert app.runner.is_busy("index") is False
    assert window.isVisible()

    started.clear()
    qtbot.mouseClick(start, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(started.is_set, timeout=3000)
    again = app.runner.active_handles()[-1]
    assert again.cancel_requested is False
    app._on_quit()
    qtbot.waitUntil(lambda: again.status is TaskStatus.CANCELLED, timeout=3000)


def _labeled(window, kind: type, text: str):
    found = [widget for widget in window.findChildren(kind) if widget.text() == text]
    assert len(found) == 1
    return found[0]


def test_closing_window_does_not_cancel_task(qtbot: QtBot, tmp_path: Path) -> None:
    app = App("psi6-close-window", config_root=tmp_path)
    window = QWidget()
    qtbot.addWidget(window)
    window.show()
    started = threading.Event()

    def job(is_cancelled=None) -> None:
        started.set()
        while not is_cancelled():
            time.sleep(0.02)
        raise InterruptedError

    handle = app.runner.submit(job)
    qtbot.waitUntil(started.is_set, timeout=3000)
    app.qt_app.setQuitOnLastWindowClosed(False)
    window.close()
    qtbot.wait(80)
    assert handle.status is TaskStatus.RUNNING
    app._on_quit()
    qtbot.waitUntil(lambda: handle.status is TaskStatus.CANCELLED, timeout=3000)


def test_missing_tray_does_not_trap_quit(qtbot: QtBot, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("psi6.ui.tray.QSystemTrayIcon.isSystemTrayAvailable", lambda: False)
    app = App("psi6-no-tray", config_root=tmp_path)
    window = DesktopWindow(title="无托盘")
    qtbot.addWidget(window)
    app.qt_app.setQuitOnLastWindowClosed(True)
    assert app._open(window, tray=True, single_instance=False, restore_geometry=False)
    assert app.tray is not None
    assert app.tray.available is False
    assert window.close_to_tray is False
    assert app.qt_app.quitOnLastWindowClosed() is True
    app.tray.refresh()
    app.tray.hide()


def test_packaged_icons_follow_the_module(tmp_path: Path, monkeypatch) -> None:
    import psi6.icons.export as export

    monkeypatch.chdir(tmp_path)
    folder = svg_dir()
    assert folder == Path(export.__file__).resolve().parent / "svg"
    assert (folder / "search.svg").is_file()
    assert tmp_path not in folder.parents


def test_stable_api_imports() -> None:
    import ast

    import psi6
    import psi6.theme as theme_pkg

    for module_name, attr in STABLE:
        module = importlib.import_module(module_name)
        assert hasattr(module, attr)
        assert attr in psi6.__all__
    assert psi6.Theme is theme_pkg.Theme
    assert psi6.contrast_notes is theme_pkg.contrast_notes
    for module_name, attr in OPTIONAL_UI:
        module = importlib.import_module(module_name)
        assert hasattr(module, attr)
        assert attr not in psi6.__all__
    assert not hasattr(psi6, "DataTable")
    assert all(not name.startswith("_") for name in psi6.__all__)
    forbidden = (
        Path(psi6.runtime.tasks.__file__).resolve().parent / "tasks.py",
        Path(psi6.runtime.job.__file__).resolve().parent / "job.py",
        Path(theme_pkg.theme.__file__).resolve(),
        Path(theme_pkg.tokens.__file__).resolve(),
    )
    for path in forbidden:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.ImportFrom) and node.module:
                modules.append(node.module)
            if isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
            assert all(not item.startswith("psi6.ui") for item in modules)


def test_app_rejects_background_thread(tmp_path: Path) -> None:
    import threading

    errors: list[str] = []

    def work() -> None:
        try:
            App("psi6-bg", config_root=tmp_path)
        except RuntimeError as exc:
            errors.append(str(exc))

    thread = threading.Thread(target=work)
    thread.start()
    thread.join()
    assert errors


def test_run_rejects_reentry(qtbot: QtBot, tmp_path: Path) -> None:
    import pytest

    app = App("psi6-reentry", config_root=tmp_path)
    window = QWidget()
    qtbot.addWidget(window)
    app._executing = True
    with pytest.raises(RuntimeError, match="再次调用"):
        app.run(window)


def test_second_instance_does_not_save_geometry(qtbot: QtBot, tmp_path: Path) -> None:
    import uuid

    name = f"psi6-lock-{uuid.uuid4().hex}"
    first = App(name, config_root=tmp_path)
    second = App(name, config_root=tmp_path)
    primary = QWidget()
    extra = QWidget()
    qtbot.addWidget(primary)
    qtbot.addWidget(extra)
    try:
        assert first._open(primary, tray=False, single_instance=True, restore_geometry=True)
        assert second._open(extra, tray=False, single_instance=True, restore_geometry=True) is False
        assert second._instance is None
        assert second._restore_geometry is False
    finally:
        if first._instance is not None:
            first._instance.close()
