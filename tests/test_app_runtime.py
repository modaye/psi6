"""App 配置与通知。"""

from __future__ import annotations

import threading
from pathlib import Path

from pydantic import BaseModel, Field
from PySide6.QtWidgets import QMainWindow, QStatusBar, QWidget
from pytestqt.qtbot import QtBot

from psi6.runtime.app import App
from psi6.runtime.notifications import NoticeLevel, Notifier
from psi6.ui.toast import ToastCard, ToastHost


class Prefs(BaseModel):
    retries: int = Field(default=1)


def test_reduced_motion_zeroes_durations(qtbot: QtBot, tmp_path: Path) -> None:
    """``set_reduced_motion`` 把两档动画时长归零，恢复后回到主题值。"""

    app = App("psi6-reduced-motion", theme="light", config_root=tmp_path)
    assert app.reduced_motion is False
    fast, slow = app.tokens.motion_fast_ms, app.tokens.motion_ms
    assert fast > 0 and slow > 0

    app.set_reduced_motion(True)
    assert app.reduced_motion is True
    assert app.tokens.motion_fast_ms == 0
    assert app.tokens.motion_ms == 0

    app.set_reduced_motion(False)
    assert app.tokens.motion_fast_ms == fast
    assert app.tokens.motion_ms == slow


def test_reduced_motion_can_be_set_at_construction(qtbot: QtBot, tmp_path: Path) -> None:
    app = App("psi6-reduced-motion-boot", config_root=tmp_path, reduced_motion=True)
    assert app.reduced_motion is True
    assert app.tokens.motion_fast_ms == 0


def test_app_config_roundtrip(qtbot: QtBot, tmp_path: Path) -> None:
    app = App("psi6-infra-test", config_root=tmp_path)
    app.save_config(Prefs(retries=4))
    loaded = app.load_config(Prefs)
    assert loaded.retries == 4


def test_remembered_path_drops_missing_entries(qtbot: QtBot, tmp_path: Path) -> None:
    """界面路径记进 QSettings；恢复时目录已不在就清掉，不留死路径。"""

    from PySide6.QtCore import QSettings

    app = App("psi6-path-memory-test", config_root=tmp_path)
    folder = tmp_path / "input"
    folder.mkdir()
    app.remember_path("last_dir", folder)
    assert app.recalled_path("last_dir") == folder
    folder.rmdir()
    assert app.recalled_path("last_dir") is None
    assert app.recalled_path("last_dir", must_exist=False) is None
    QSettings(app.organization, app.name).clear()


def test_notifier_records_last(qtbot: QtBot) -> None:
    notifier = Notifier()
    notifier.warning("慢一点")
    assert notifier.last == (NoticeLevel.WARNING.value, "慢一点")


def test_notifier_binds_status_bar(qtbot: QtBot) -> None:
    window = QMainWindow()
    bar = QStatusBar(window)
    window.setStatusBar(bar)
    qtbot.addWidget(window)
    notifier = Notifier()
    notifier.bind_status_bar(bar)
    notifier.info("就绪")
    assert bar.currentMessage() == "就绪"


def test_notifier_info_skips_toast_success_shows(qtbot: QtBot) -> None:
    window = QMainWindow()
    window.setCentralWidget(QWidget())
    qtbot.addWidget(window)
    host = ToastHost(window.centralWidget())
    notifier = Notifier()
    notifier.bind_toast_host(host)
    notifier.info("扫描中 1/10")
    assert host.findChildren(ToastCard) == []
    notifier.success("完成，共 3 项")
    assert host.findChildren(ToastCard)


def test_notifier_marshals_worker_thread_updates(qtbot: QtBot) -> None:
    window = QMainWindow()
    bar = QStatusBar(window)
    window.setStatusBar(bar)
    qtbot.addWidget(window)
    notifier = Notifier()
    notifier.bind_status_bar(bar)
    thread = threading.Thread(target=lambda: notifier.warning("来自后台"), daemon=True)
    thread.start()
    qtbot.waitUntil(lambda: bar.currentMessage() == "来自后台", timeout=3000)
    assert notifier.last == (NoticeLevel.WARNING.value, "来自后台")


def test_window_geometry_roundtrip(qtbot: QtBot, tmp_path: Path) -> None:
    from psi6.runtime.config import ConfigStore
    from psi6.runtime.window_state import restore_window, save_window

    store = ConfigStore(tmp_path)
    window = QWidget()
    qtbot.addWidget(window)
    window.resize(640, 480)
    window.show()
    qtbot.waitExposed(window)
    save_window(window, store, "geo")
    other = QWidget()
    qtbot.addWidget(other)
    assert restore_window(other, store, "geo") is True
    assert other.size().width() == 640
    assert other.size().height() == 480


def test_restore_maximized_flag(qtbot: QtBot, tmp_path: Path) -> None:
    from psi6.runtime.config import ConfigStore
    from psi6.runtime.window_state import restore_window, save_window

    store = ConfigStore(tmp_path)
    window = QWidget()
    qtbot.addWidget(window)
    window.resize(400, 300)
    window.show()
    qtbot.waitExposed(window)
    save_window(window, store, "geo-max")
    payload = store.load_data("geo-max", "window.json")
    assert payload is not None
    payload["maximized"] = True
    store.save_data("geo-max", "window.json", payload)
    other = QWidget()
    qtbot.addWidget(other)
    assert restore_window(other, store, "geo-max") is True
    assert other.isMaximized()


def test_run_does_not_lock_or_persist_by_default() -> None:
    import inspect

    params = inspect.signature(App.run).parameters
    assert params["single_instance"].default is False
    assert params["restore_geometry"].default is False


def test_quit_writes_geometry_only_when_requested(qtbot: QtBot, tmp_path: Path) -> None:
    app = App("psi6-no-geo", config_root=tmp_path)
    window = QWidget()
    qtbot.addWidget(window)
    window.resize(320, 240)
    app._window = window
    app._restore_geometry = False
    app._on_quit()
    assert not (tmp_path / "psi6-no-geo" / "window.json").exists()
    app._restore_geometry = True
    app._on_quit()
    assert (tmp_path / "psi6-no-geo" / "window.json").is_file()
