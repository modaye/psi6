"""页签关闭按钮走主题图形，不再用 Qt 原生的橙底方块。"""

from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtWidgets import QLabel
from pytestqt.qtbot import QtBot

from psi6.runtime.app import App
from psi6.theme.apply import build_stylesheet
from psi6.theme.chrome import chrome_images
from psi6.theme.tokens import Tokens
from psi6.ui.tab_view import TabView


def _block(css: str, selector: str) -> str:
    """取指定选择器自己的声明块。

    基础选择器是 ``:hover`` / ``:pressed`` 变体的前缀，字符串匹配会先命中变体，
    所以按「选择器 + 紧跟左花括号」精确取。
    """

    match = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", css)
    assert match is not None, selector
    return match.group(1)


def test_close_button_uses_a_themed_glyph() -> None:
    """QSS 一旦接管 close-button 就会吃掉 Qt 的叉号，所以必须自己给图形。"""

    tokens = Tokens.light().resolve_states()
    css = build_stylesheet(tokens)

    block = _block(css, "QTabBar::close-button")
    assert "image: url(" in block
    assert "psi6icon:" in block
    # 原生方块由 QSS 接管后要彻底替换掉：背景透明、无边框。
    assert "background: transparent" in block
    assert "border: none" in block


def test_close_button_hover_uses_the_text_color() -> None:
    tokens = Tokens.light().resolve_states()
    css = build_stylesheet(tokens)

    hover = _block(css, "QTabBar::close-button:hover")
    assert "psi6icon:" in hover
    assert "background: " + tokens.color_hover in hover
    assert "QTabBar::close-button:pressed {" in css


def test_close_button_images_follow_the_theme_palette() -> None:
    """图形按当前 token 着色，换肤后重新生成另一份缓存文件。"""

    images = chrome_images(Tokens.light().resolve_states())
    assert "tab_close" in images
    assert "tab_close_on" in images
    assert images["tab_close"].startswith("psi6icon:")
    assert images["tab_close"] != images["tab_close_on"]

    dark = chrome_images(Tokens.dark().resolve_states())
    assert dark["tab_close"] != images["tab_close"]


def test_tab_view_close_button_is_painted_by_the_theme(qtbot: QtBot, tmp_path: Path) -> None:
    """组件目录 / 应用里实际生效：页签条的关闭按钮取主题图形。"""

    app = App("psi6-close-btn", theme="light", config_root=tmp_path)
    tabs = TabView()
    qtbot.addWidget(tabs)
    page = QLabel("内容")
    qtbot.addWidget(page)
    tabs.add_tab("a", "文档 A", page)
    assert "QTabBar::close-button" in app.qt_app.styleSheet()
    assert "psi6icon:" in app.qt_app.styleSheet()
