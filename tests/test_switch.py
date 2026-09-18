"""开关、设置行、表单 field_switch。"""

from __future__ import annotations

from pydantic import BaseModel
from pytestqt.qtbot import QtBot
from PySide6.QtWidgets import QVBoxLayout, QWidget

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
