"""焦点环打开时只跟键盘焦点。鼠标点击不画环，关闭时选择器不做门控。"""

from __future__ import annotations

import re
import warnings
from pathlib import Path

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QLineEdit, QPushButton, QVBoxLayout, QWidget
from pytestqt.qtbot import QtBot

from psi6.runtime.app import App
from psi6.theme.apply import build_stylesheet, psi6_button_stylesheet
from psi6.theme.tokens import Tokens
from psi6.ui.buttons import ghost_button

_GATE = '[psi6KbdFocus="1"]'
_BARE_FOCUS = re.compile(r":focus(?!\[psi6KbdFocus)")


def _activate(app: App, host: QWidget) -> None:
    """offscreen 里 ``activateWindow`` 不会把窗口变成活动窗口，``setFocus`` 也就不生效。

    ``QWindow.requestActivate`` 在 pytest-qt 里是异步的，常常赶不上紧接着的 ``setFocus``。
    ``setActiveWindow`` 仍是同步的，只是绑定标成了弃用。
    """

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        app.qt_app.setActiveWindow(host)


def test_focus_selectors_are_gated_to_keyboard() -> None:
    """打开时 ``:focus`` 收成键盘属性。``psi6State="focus"`` 仍是预览选择器。"""

    tokens = Tokens.light().resolve_states()
    css = build_stylesheet(tokens, focus_ring=True)
    assert _GATE in css
    assert _BARE_FOCUS.search(css) is None
    assert 'QLineEdit[psi6State="focus"]' in css
    assert 'QPushButton[psi6State="focus"]' in css
    assert 'psi6State="focus"]' + _GATE not in css

    primary = psi6_button_stylesheet("psi6Primary", tokens, focus_ring=True)
    assert f"QPushButton:focus{_GATE}" in primary
    assert _BARE_FOCUS.search(primary) is None

    nav = psi6_button_stylesheet("psi6NavItem", tokens, focus_ring=True)
    assert 'QPushButton[psi6State="focus"]' in nav
    assert 'psi6State="focus"]' + _GATE not in nav
    assert f"QPushButton:focus{_GATE}" in nav


def test_mouse_focus_is_unmarked_and_keyboard_focus_is_marked(qtbot: QtBot, tmp_path: Path) -> None:
    """鼠标、窗口激活、弹层写 0；Tab、Backtab、快捷键和 setFocus 写 1。失焦清零。"""

    app = App("psi6-focus-visible", theme="light", config_root=tmp_path, focus_ring=True)
    host = QWidget()
    layout = QVBoxLayout(host)
    first = QPushButton("第一")
    second = QPushButton("第二")
    ghost = ghost_button("取消")
    edit = QLineEdit()
    for widget in (first, second, ghost, edit):
        layout.addWidget(widget)
    qtbot.addWidget(host)
    host.resize(280, 220)
    host.show()
    _activate(app, host)
    qtbot.waitExposed(host)

    def focus(widget: QWidget, reason: Qt.FocusReason) -> None:
        widget.setFocus(reason)
        qtbot.wait(0)

    def edge_color(widget: QWidget) -> str:
        image = host.grab().toImage()
        ratio = image.devicePixelRatio()
        origin = widget.mapTo(host, QPoint(0, 0))
        x = int((origin.x() + 1) * ratio)
        y = int((origin.y() + widget.height() / 2) * ratio)
        return image.pixelColor(x, y).name().lower()

    focus_color = app.tokens.color_focus.lower()

    focus(first, Qt.FocusReason.MouseFocusReason)
    assert first.hasFocus()
    assert first.property("psi6KbdFocus") == "0"
    assert edge_color(first) != focus_color

    focus(second, Qt.FocusReason.TabFocusReason)
    assert second.hasFocus()
    assert second.property("psi6KbdFocus") == "1"
    assert first.property("psi6KbdFocus") == "0"
    assert edge_color(second) == focus_color

    focus(edit, Qt.FocusReason.BacktabFocusReason)
    assert edit.property("psi6KbdFocus") == "1"
    assert second.property("psi6KbdFocus") == "0"

    focus(first, Qt.FocusReason.ShortcutFocusReason)
    assert first.property("psi6KbdFocus") == "1"

    focus(second, Qt.FocusReason.OtherFocusReason)
    assert second.property("psi6KbdFocus") == "1"

    focus(edit, Qt.FocusReason.ActiveWindowFocusReason)
    assert edit.property("psi6KbdFocus") == "0"

    focus(first, Qt.FocusReason.PopupFocusReason)
    assert first.property("psi6KbdFocus") == "0"

    qtbot.mouseClick(second, Qt.MouseButton.LeftButton)
    assert second.property("psi6KbdFocus") == "0"
    assert _GATE in app.qt_app.styleSheet()
    assert _GATE in ghost.styleSheet()

    app.set_focus_ring(False)
    assert "psi6KbdFocus" not in app.qt_app.styleSheet()
    assert "psi6KbdFocus" not in ghost.styleSheet()
    app.set_focus_ring(True)
    assert _GATE in app.qt_app.styleSheet()
    assert _GATE in ghost.styleSheet()


def test_focus_ring_off_does_not_gate_selectors(qtbot: QtBot, tmp_path: Path) -> None:
    """关闭时选择器仍是普通 ``:focus``，键盘焦点也不会被打上标记。"""

    tokens = Tokens.light().resolve_states()
    css = build_stylesheet(tokens, focus_ring=False)
    button = psi6_button_stylesheet("psi6Ghost", tokens, focus_ring=False)
    assert "psi6KbdFocus" not in css
    assert "psi6KbdFocus" not in button
    assert "QPushButton:focus" in css
    assert "QLineEdit:focus" in css

    app = App("psi6-focus-off", theme="light", config_root=tmp_path, focus_ring=False)
    host = QWidget()
    layout = QVBoxLayout(host)
    plain = QPushButton("普通")
    layout.addWidget(plain)
    qtbot.addWidget(host)
    host.show()
    _activate(app, host)
    qtbot.waitExposed(host)
    plain.setFocus(Qt.FocusReason.TabFocusReason)
    qtbot.wait(0)
    assert plain.property("psi6KbdFocus") != "1"
    assert "psi6KbdFocus" not in app.qt_app.styleSheet()
