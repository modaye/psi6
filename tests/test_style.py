"""控件可以在运行时各自指定字号、字重、字色和底色。"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication, QLabel
from pytestqt.qtbot import QtBot

from psi6.theme.apply import apply_theme
from psi6.theme.runtime import publish_tokens
from psi6.theme.tokens import Tokens
from psi6.ui.icon import Icon
from psi6.ui.style import Style, clear_style, resolve_color, set_style


def test_each_widget_keeps_its_own_style(qtbot: QtBot) -> None:
    title = QLabel("标题")
    note = QLabel("说明")
    qtbot.addWidget(title)
    qtbot.addWidget(note)
    set_style(title, size=25, weight=700, color="#188b7b")
    Style(size=11, color="muted").apply(note)
    set_style(title, fill="#eaf5f3", radius=8)
    assert "25px" in title.styleSheet()
    assert "700" in title.styleSheet()
    assert "#188b7b" in title.styleSheet()
    assert "#eaf5f3" in title.styleSheet()
    assert "11px" in note.styleSheet()
    assert "25px" not in note.styleSheet()
    clear_style(title)
    assert title.styleSheet() == ""
    assert "11px" in note.styleSheet()


def test_token_color_follows_the_theme_and_literal_color_stays(qtbot: QtBot) -> None:
    label = QLabel("指标")
    qtbot.addWidget(label)
    set_style(label, color="primary", fill="#eef2ff")
    app = QApplication.instance()
    assert app is not None
    publish_tokens(app, Tokens(color_primary="#188b7b"))
    app.sendEvent(label, QEvent(QEvent.Type.PaletteChange))
    sheet = label.styleSheet()
    assert "#188b7b" in sheet
    assert "#eef2ff" in sheet
    publish_tokens(app, Tokens(color_primary="#6275c8"))
    app.sendEvent(label, QEvent(QEvent.Type.PaletteChange))
    assert "#6275c8" in label.styleSheet()
    assert "#eef2ff" in label.styleSheet()


def test_theme_switch_restyles_each_widget_once(qtbot: QtBot) -> None:
    labels = [QLabel(str(index)) for index in range(20)]
    for label in labels:
        qtbot.addWidget(label)
        set_style(label, size=13, color="primary", fill="#eef2ff")
    app = QApplication.instance()
    assert app is not None
    apply_theme(app, Tokens(color_primary="#188b7b"), focus_ring=False)
    assert "#188b7b" in labels[0].styleSheet()
    assert "#eef2ff" in labels[0].styleSheet()
    apply_theme(app, Tokens(color_primary="#6275c8"), focus_ring=False)
    assert "#6275c8" in labels[0].styleSheet()
    assert "#eef2ff" in labels[0].styleSheet()
    assert "#188b7b" not in labels[0].styleSheet()


def test_unknown_color_is_rejected(qtbot: QtBot) -> None:
    label = QLabel("x")
    qtbot.addWidget(label)
    with pytest.raises(ValueError, match="无法识别的颜色"):
        set_style(label, color="not-a-color")


def test_icon_color_can_be_set_per_icon(qtbot: QtBot) -> None:
    icon = Icon("file", size=16)
    qtbot.addWidget(icon)
    icon.set_color("#6275c8")
    assert icon.property("psi6IconColor") == "#6275c8"
    icon.set_color("primary")
    assert icon.property("psi6IconColor") == resolve_color("primary")
    app = QApplication.instance()
    assert app is not None
    publish_tokens(app, Tokens(color_primary="#188b7b"))
    app.sendEvent(icon, QEvent(QEvent.Type.PaletteChange))
    assert icon.property("psi6IconColor") == "#188b7b"
    icon.set_color(None)
    assert icon.property("psi6IconColor") == ""
