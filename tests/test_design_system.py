"""四种风格组合、焦点顺序和紧凑图标热区。不把截图像素当验收。"""

from __future__ import annotations

from pathlib import Path

from pytestqt.qtbot import QtBot
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QLineEdit, QVBoxLayout, QWidget

from psi6 import App
from psi6.theme.theme import Theme
from psi6.theme.tokens import Tokens
from psi6.ui.buttons import primary_button
from psi6.ui.icon import IconButton


def _probe(base: str, style: str) -> type[Theme]:
    class Probe(Theme):
        name = f"{style}-{base}"

    Probe.base = base
    Probe.style = style
    return Probe


def test_four_combinations_restyle_live_widgets(qtbot: QtBot, tmp_path: Path) -> None:
    """已创建的控件跟着主题切换，不留下上一套高度或画布色。"""

    app = App("psi6-four", theme="light", config_root=tmp_path)
    button = primary_button("开始")
    edit = QLineEdit()
    qtbot.addWidget(button)
    qtbot.addWidget(edit)
    expect = (
        ("light", "modern", Tokens.light().color_bg, 36, 6),
        ("dark", "modern", Tokens.dark().color_bg, 36, 6),
        ("light", "compact", Tokens.light().color_bg, 30, 4),
        ("dark", "compact", Tokens.dark().color_bg, 30, 4),
    )
    for base, style, canvas, height, radius in expect:
        app.set_theme(_probe(base, style))
        css = app.qt_app.styleSheet()
        assert app.tokens.color_bg == canvas
        assert app.tokens.control_height == height
        assert app.tokens.radius == radius
        assert canvas in css
        assert f"min-height: {height}px" in css
        assert f"border: {app.tokens.focus_ring_width}px solid" in css
        assert "psi6Primary:pressed" in css
        assert "psi6NavItem:focus" in css
        assert "QTabBar::tab:disabled" in css


def test_tab_skips_disabled_and_space_activates_button(qtbot: QtBot, tmp_path: Path) -> None:
    App("psi6-keys", theme="light", config_root=tmp_path)
    window = QWidget()
    first = primary_button("甲")
    blocked = primary_button("乙")
    blocked.setEnabled(False)
    field = QLineEdit()
    error = QLabel("请填写名称。")
    error.setObjectName("psi6Error")
    field.setProperty("invalid", True)
    layout = QVBoxLayout(window)
    layout.addWidget(first)
    layout.addWidget(blocked)
    layout.addWidget(field)
    layout.addWidget(error)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    first.setFocus()
    qtbot.keyClick(first, Qt.Key.Key_Tab)
    assert window.focusWidget() is field
    clicks: list[str] = []
    blocked.clicked.connect(lambda: clicks.append("blocked"))
    first.clicked.connect(lambda: clicks.append("first"))
    qtbot.keyClick(blocked, Qt.Key.Key_Space)
    assert clicks == []
    first.setFocus()
    qtbot.keyClick(first, Qt.Key.Key_Space)
    assert clicks == ["first"]
    assert error.text()
    assert field.property("invalid") is True


def test_compact_icon_keeps_a_hit_target(qtbot: QtBot, tmp_path: Path) -> None:
    app = App("psi6-hit", config_root=tmp_path)
    app.set_theme(_probe("light", "compact"))
    button = IconButton("search", label="搜索")
    qtbot.addWidget(button)
    assert app.tokens.icon_size == 14
    assert button.iconSize().width() == 14
    assert button.width() >= 28
    assert button.height() >= 28
