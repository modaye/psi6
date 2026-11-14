"""焦点环默认关闭。``focus_ring=True`` 才画环，并且不改控件外框尺寸。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QLineEdit, QVBoxLayout, QWidget
from pytestqt.qtbot import QtBot

from psi6.runtime.app import App
from psi6.theme.apply import build_stylesheet, psi6_button_stylesheet
from psi6.theme.tokens import Tokens
from psi6.ui.buttons import ghost_button, primary_button

_RING = f"border: {Tokens.light().resolve_states().focus_ring_width}px solid"
_FOCUS_KEY = "psi6FocusRingEnabled"


def _focus_block(css: str, selector: str) -> str:
    """取选择器之后紧随的声明块。"""

    return css.split(selector, 1)[1].split("{", 1)[1].split("}", 1)[0]


def test_build_stylesheet_focus_ring_is_opt_in() -> None:
    """默认参数保留原有焦点环；显式关闭后只剩抑制原生焦点框的中性规则。"""

    tokens = Tokens.light().resolve_states()
    on = build_stylesheet(tokens)
    off = build_stylesheet(tokens, focus_ring=False)

    # 开启：既有 a11y 能力与几何补偿不回退。
    assert _RING in on
    for selector in ("QPushButton:focus", "QLineEdit:focus", "QTabBar::tab:focus"):
        assert f"border: {tokens.focus_ring_width}px solid" in _focus_block(on, selector)
    assert 'QPushButton[psi6State="focus"]' in on

    # 关闭：选择器仍在（继续抑制原生焦点框），但不画环、也不改边框 / 间距 / 高度。
    assert _RING not in off
    for selector in (
        "QPushButton:focus",
        "QLineEdit:focus",
        "QTabBar::tab:focus",
        "QToolButton#psi6IconButton:focus",
        "QWidget#psi6DropZone:focus",
        "QCheckBox::indicator:focus",
    ):
        block = _focus_block(off, selector)
        assert "border:" not in block, selector
        assert "padding:" not in block, selector
        assert "min-height:" not in block, selector
        assert "outline: none" in block, selector
    # 勾选框 / 单选框的其它状态不能因为关焦点环而消失。
    assert "QCheckBox::indicator:checked" in off
    assert "QRadioButton::indicator:checked" in off


def test_button_stylesheets_follow_the_switch() -> None:
    """逐控件样式化的按钮也要跟着开关，不能只改全局 QSS。"""

    tokens = Tokens.light().resolve_states()
    for kind in (
        "psi6Primary",
        "psi6Danger",
        "psi6Ghost",
        "psi6Link",
        "psi6Segment",
        "psi6NavItem",
    ):
        on = psi6_button_stylesheet(kind, tokens)
        off = psi6_button_stylesheet(kind, tokens, focus_ring=False)
        assert "QPushButton:focus" in on, kind
        block = _focus_block(off, "QPushButton:focus")
        assert "border:" not in block, kind
        assert "padding:" not in block, kind
        assert "min-height:" not in block, kind
        assert "text-decoration" not in block, kind
        assert "outline: none" in block, kind
    # 开启时链接按钮仍用下划线、导航按钮仍带环。
    assert "text-decoration: underline" in psi6_button_stylesheet("psi6Link", tokens)
    assert _RING in psi6_button_stylesheet("psi6NavItem", tokens)


def test_app_hides_focus_ring_by_default(qtbot: QtBot, tmp_path: Path) -> None:
    app = App("psi6-focus-default", theme="light", config_root=tmp_path)

    assert app.focus_ring is False
    assert not app.qt_app.property(_FOCUS_KEY)
    assert _RING not in app.qt_app.styleSheet()


def test_app_can_enable_focus_ring_at_construction(qtbot: QtBot, tmp_path: Path) -> None:
    app = App("psi6-focus-on", theme="light", config_root=tmp_path, focus_ring=True)

    assert app.focus_ring is True
    assert app.qt_app.property(_FOCUS_KEY)
    assert _RING in app.qt_app.styleSheet()


def test_set_focus_ring_restyles_global_and_themed_buttons(qtbot: QtBot, tmp_path: Path) -> None:
    """切换开关后全局 QSS 与逐控件按钮同步；换主题不能把开关弄丢。"""

    app = App("psi6-focus-toggle", theme="light", config_root=tmp_path)
    host = QWidget()
    layout = QVBoxLayout(host)
    edit = QLineEdit()
    primary = primary_button("开始")
    ghost = ghost_button("取消")
    for widget in (edit, primary, ghost):
        layout.addWidget(widget)
    qtbot.addWidget(host)
    host.show()
    qtbot.wait(10)

    assert _RING not in primary.styleSheet()
    assert _RING not in ghost.styleSheet()

    app.set_focus_ring(True)
    assert _RING in primary.styleSheet()
    assert _RING in ghost.styleSheet()

    app.set_focus_ring(False)
    assert app.focus_ring is False
    assert not app.qt_app.property(_FOCUS_KEY)
    assert _RING not in app.qt_app.styleSheet()
    assert _RING not in primary.styleSheet()
    assert _RING not in ghost.styleSheet()

    app.set_theme("dark")
    assert app.focus_ring is False
    assert _RING not in primary.styleSheet()

    app.set_focus_ring(True)
    assert app.focus_ring is True
    assert _RING in app.qt_app.styleSheet()
    assert _RING in primary.styleSheet()
    assert _RING in ghost.styleSheet()
