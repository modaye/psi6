"""开关、设置行、表单 field_switch。"""

from __future__ import annotations

import warnings
from pathlib import Path

from pydantic import BaseModel
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QVBoxLayout, QWidget
from pytestqt.qtbot import QtBot

from psi6.runtime.app import App
from psi6.ui.form import field_switch, pydantic_form
from psi6.ui.setting_row import SettingRow
from psi6.ui.switch import Switch


def test_switch_toggles_without_becoming_a_window(qtbot: QtBot) -> None:
    host = QWidget()
    qtbot.addWidget(host)
    layout = QVBoxLayout(host)
    switch = Switch(checked=False)
    layout.addWidget(switch)
    host.show()
    qtbot.waitExposed(host)
    assert switch.parent() is host
    assert not switch.isChecked()
    assert (switch.width(), switch.height()) == (42, 24)
    switch.click()
    assert switch.isChecked()
    switch.setChecked(False)
    assert not switch.isChecked()


def test_setting_row_forwards_toggle(qtbot: QtBot) -> None:
    host = QWidget()
    qtbot.addWidget(host)
    layout = QVBoxLayout(host)
    row = SettingRow("包含子目录", hint="扫描嵌套文件夹", checked=True)
    layout.addWidget(row)
    seen: list[bool] = []
    row.toggled.connect(seen.append)
    row.set_checked(False)
    assert row.is_checked() is False
    assert seen[-1] is False


class SwitchModel(BaseModel):
    recursive: bool = field_switch(default=True, description="包含子目录")


def test_field_switch_builds_switch_widget(qtbot: QtBot) -> None:
    view = pydantic_form(SwitchModel())
    qtbot.addWidget(view)
    switches = view.findChildren(Switch)
    assert len(switches) == 1
    assert switches[0].isChecked() is True
    switches[0].setChecked(False)
    assert view.get_model().recursive is False


def test_motion_token_is_published(qtbot: QtBot, tmp_path) -> None:
    app = App("psi6-motion", config_root=tmp_path)
    assert app.qt_app.property("psi6MotionFastMs") == 160
    from psi6.theme.apply import apply_theme
    from psi6.theme.tokens import Tokens

    apply_theme(app.qt_app, Tokens.light().overlay({"motion_fast_ms": 0}))
    assert app.qt_app.property("psi6MotionFastMs") == 0
    apply_theme(app.qt_app, Tokens.light())


def _activate(app: App, host: QWidget) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        app.qt_app.setActiveWindow(host)


def _focus_hits(widget: QWidget, color: str) -> int:
    """数一数控件截图里有多少像素正好是焦点色。环画在胶囊外沿，不在中线。"""

    image = widget.grab().toImage()
    target = QColor(color)
    wanted = (target.red(), target.green(), target.blue())
    hits = 0
    for y in range(image.height()):
        for x in range(image.width()):
            pixel = image.pixelColor(x, y)
            if (pixel.red(), pixel.green(), pixel.blue()) == wanted:
                hits += 1
    return hits


def test_switch_ring_follows_keyboard_focus(qtbot: QtBot, tmp_path: Path) -> None:
    """鼠标焦点不画环。键盘焦点在开关打开时才画。"""

    app = App("psi6-switch-ring", theme="light", config_root=tmp_path, focus_ring=True)
    host = QWidget()
    layout = QVBoxLayout(host)
    switch = Switch()
    other = QWidget()
    other.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    layout.addWidget(switch)
    layout.addWidget(other)
    qtbot.addWidget(host)
    host.show()
    _activate(app, host)
    qtbot.waitExposed(host)
    focus = app.tokens.color_focus.lower()

    switch.setFocus(Qt.FocusReason.MouseFocusReason)
    qtbot.wait(0)
    assert switch.hasFocus()
    assert switch.property("psi6KbdFocus") == "0"
    assert _focus_hits(switch, focus) == 0

    other.setFocus(Qt.FocusReason.MouseFocusReason)
    switch.setFocus(Qt.FocusReason.TabFocusReason)
    qtbot.wait(0)
    assert switch.hasFocus()
    assert switch.property("psi6KbdFocus") == "1"
    assert _focus_hits(switch, focus) > 0


def test_switch_ring_stays_off_when_focus_ring_is_disabled(qtbot: QtBot, tmp_path: Path) -> None:
    app = App("psi6-switch-ring-off", theme="light", config_root=tmp_path, focus_ring=False)
    host = QWidget()
    layout = QVBoxLayout(host)
    switch = Switch()
    layout.addWidget(switch)
    qtbot.addWidget(host)
    host.show()
    _activate(app, host)
    qtbot.waitExposed(host)
    switch.setFocus(Qt.FocusReason.TabFocusReason)
    qtbot.wait(0)
    assert _focus_hits(switch, app.tokens.color_focus) == 0
