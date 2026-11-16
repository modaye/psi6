"""抽屉的焦点：打开记住、Tab 留在内部、关闭还回、宿主销毁不还。"""

from __future__ import annotations

import warnings
from pathlib import Path

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QLineEdit, QPushButton, QVBoxLayout, QWidget
from pytestqt.qtbot import QtBot

from psi6 import App
from psi6.ui import motion
from psi6.ui.drawer import Drawer


def _activate(app: App, host: QWidget) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        app.qt_app.setActiveWindow(host)


def test_drawer_traps_tab_and_restores_focus(qtbot: QtBot, tmp_path: Path) -> None:
    app = App("psi6-drawer-focus", theme="light", config_root=tmp_path, reduced_motion=True)
    host = QWidget()
    layout = QVBoxLayout(host)
    opener = QPushButton("打开")
    layout.addWidget(opener)
    qtbot.addWidget(host)
    host.resize(480, 320)
    host.show()
    _activate(app, host)
    qtbot.waitExposed(host)
    opener.setFocus()
    qtbot.wait(0)
    assert opener.hasFocus()

    drawer = Drawer("详情", host)
    field = QLineEdit()
    extra = QPushButton("动作")
    drawer.body().addWidget(field)
    drawer.body().addWidget(extra)
    drawer.open()

    assert field.hasFocus()
    qtbot.keyClick(field, Qt.Key.Key_Tab)
    assert extra.hasFocus()
    qtbot.keyClick(extra, Qt.Key.Key_Tab)
    assert extra.hasFocus() is False
    assert field.hasFocus() is False
    qtbot.keyClick(host.focusWidget(), Qt.Key.Key_Tab)
    assert field.hasFocus()

    qtbot.keyClick(field, Qt.Key.Key_Escape)
    assert drawer.isVisible() is False
    assert opener.hasFocus()


def test_drawer_mask_click_restores_focus(qtbot: QtBot, tmp_path: Path) -> None:
    app = App("psi6-drawer-mask", theme="light", config_root=tmp_path, reduced_motion=True)
    host = QWidget()
    opener = QPushButton("打开", host)
    qtbot.addWidget(host)
    host.resize(480, 320)
    host.show()
    _activate(app, host)
    qtbot.waitExposed(host)
    opener.setFocus()

    drawer = Drawer("详情", host)
    drawer.body().addWidget(QLineEdit())
    drawer.open()
    qtbot.mouseClick(drawer, Qt.MouseButton.LeftButton, pos=QPoint(8, 40))
    assert drawer.isVisible() is False
    assert opener.hasFocus()


def test_destroying_the_host_drops_the_drawer_animation(qtbot: QtBot, tmp_path: Path) -> None:
    app = App("psi6-drawer-destroy", theme="light", config_root=tmp_path)
    del app
    host = QWidget()
    host.resize(480, 320)
    host.show()
    drawer = Drawer("详情", host)
    motion.stop_all()
    drawer.open()
    assert motion._RUNNING
    host.deleteLater()
    qtbot.waitUntil(lambda: motion._RUNNING == [])
