"""样例工作台带进来的卡片、页签指示器、加载按钮、勾选焦点和石墨主题。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton
from pytestqt.qtbot import QtBot

from psi6 import App
from psi6.examples.showroom import Showroom
from psi6.icons.glyphs import icon_names
from psi6.theme.apply import build_stylesheet
from psi6.theme.builtin import Graphite
from psi6.theme.diagnose import contrast_notes
from psi6.theme.tokens import Tokens
from psi6.ui.buttons import is_loading, primary_button, set_loading
from psi6.ui.chrome import Card
from psi6.ui.underline_tabs import UnderlineTabs


def test_graphite_clears_contrast_notes() -> None:
    notes = contrast_notes(Graphite().tokens())
    assert notes == []
    assert Graphite.name == "graphite"


def test_card_is_flat_unless_asked_to_rise(qtbot: QtBot) -> None:
    flat = Card()
    qtbot.addWidget(flat)
    assert flat.objectName() == "psi6Card"
    assert flat.elevated() is False
    assert flat.graphicsEffect() is None
    raised = Card(elevated=True)
    qtbot.addWidget(raised)
    assert raised.elevated() is True
    assert raised.graphicsEffect() is not None


def test_indicator_focus_does_not_thicken_the_box() -> None:
    """焦点环在整行上。指示器的 :focus 不再加粗边框。"""

    tokens = Tokens.light().resolve_states()
    css = build_stylesheet(tokens)
    block = css.split("QCheckBox::indicator:focus", 1)[1].split("{", 1)[1].split("}", 1)[0]
    assert "border:" not in block
    row = css.split("QCheckBox:focus", 1)[1].split("{", 1)[1].split("}", 1)[0]
    assert f"border-color: {tokens.color_focus}" in row
    checked = css.split("QCheckBox::indicator:checked {", 1)[1].split("}", 1)[0]
    assert "image: url(psi6icon:" in checked


def test_loading_blocks_clicks_and_keeps_the_fill(qtbot: QtBot) -> None:
    button = primary_button("保存")
    qtbot.addWidget(button)
    button.show()
    seen: list[int] = []
    button.clicked.connect(lambda: seen.append(1))
    set_loading(button, True)
    assert is_loading(button)
    assert button.isEnabled()
    assert button.property("psi6Loading") is True
    qtbot.mouseClick(button, Qt.MouseButton.LeftButton)
    assert seen == []
    set_loading(button, False)
    assert is_loading(button) is False
    qtbot.mouseClick(button, Qt.MouseButton.LeftButton)
    assert seen == [1]


def test_underline_tabs_follow_the_selection(qtbot: QtBot) -> None:
    tabs = UnderlineTabs()
    qtbot.addWidget(tabs)
    tabs.add_tab("概览", QLabel("一"))
    tabs.add_tab("明细", QLabel("二"))
    assert tabs.current_index() == 0
    seen: list[int] = []
    tabs.current_changed.connect(seen.append)
    tabs.set_current(1)
    assert tabs.current_index() == 1
    assert seen == [1]
    tabs.set_current(1)
    assert seen == [1]


def test_new_glyphs_are_named() -> None:
    names = set(icon_names())
    assert {
        "home",
        "layers",
        "bell",
        "spark",
        "menu",
        "calendar",
        "arrow-left",
        "arrow-right",
    } <= names


def test_showroom_opens_on_the_overview(qtbot: QtBot, tmp_path: Path) -> None:
    app = App("psi6-showroom-test", theme="graphite", config_root=tmp_path)
    window = Showroom(app)
    qtbot.addWidget(window)
    window.resize(1100, 720)
    window.show()
    qtbot.waitExposed(window)
    assert window.shell.current_id() == "overview"
    assert app.focus_ring is False
    for page_id in ("buttons", "inputs", "data", "nav", "feedback", "containers", "motion"):
        window.shell.show_page(page_id)
        assert window.shell.current_id() == page_id
    assert window.shell.nav_accent() is True
    window.shell.set_nav_accent(False)
    assert window.shell.nav_accent() is False
    marks = [
        button.property("psi6NavAccent")
        for button in window.shell.sidebar.findChildren(QPushButton)
        if button.objectName() == "psi6NavItem"
    ]
    assert marks
    assert set(marks) == {"off"}
