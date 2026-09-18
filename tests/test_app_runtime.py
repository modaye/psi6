"""App 配置与通知。"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field
from pytestqt.qtbot import QtBot
from PySide6.QtWidgets import QMainWindow, QStatusBar, QWidget

from psi6.runtime.app import App
from psi6.runtime.notifications import NoticeLevel, Notifier
from psi6.ui.toast import ToastCard, ToastHost


class Prefs(BaseModel):
    retries: int = Field(default=1)


def test_app_config_roundtrip(qtbot: QtBot, tmp_path: Path) -> None:
    app = App("psi6-infra-test", config_root=tmp_path)
    app.save_config(Prefs(retries=4))
    loaded = app.load_config(Prefs)
    assert loaded.retries == 4


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

