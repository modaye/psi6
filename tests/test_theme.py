"""主题 token 进入样式表，组件不写死 hex。"""

from __future__ import annotations

from pathlib import Path

from pytestqt.qtbot import QtBot
import pytest

from psi6.runtime.app import App
from psi6.theme.apply import build_stylesheet
from psi6.theme.tokens import DEFAULT_TOKENS, Tokens


def test_stylesheet_uses_tokens() -> None:
    css = build_stylesheet(DEFAULT_TOKENS)
    assert DEFAULT_TOKENS.color_primary in css
    assert DEFAULT_TOKENS.color_danger in css
    assert "psi6Primary" in css
    assert f"border-radius: {DEFAULT_TOKENS.window_radius}px" in css


def test_stylesheet_covers_native_widgets() -> None:
    css = build_stylesheet(Tokens.light())
    for selector in (
        "QScrollBar",
        "QTabBar",
        "QMenu",
        "QToolTip",
        "QSplitter",
        "QTreeView",
        "psi6Toast",
        "psi6BusyOverlay",
        "psi6DiffHost",
        "psi6DiffView",
        "psi6Switch",
        "psi6SettingRow",
        "QDateTimeEdit",
        "QDateEdit",
        "QComboBox::down-arrow",
        "QAbstractSpinBox::up-arrow",
        "psi6Ghost",
        "psi6Link",
        "psi6DropZone",
        "psi6Segmented",
        "psi6CheckList",
        "psi6ContentDialog",
        "psi6ImageWell",
    ):
        assert selector in css
    assert "padding: 0" in css
    assert "psi6icon:" in css


def test_dark_stylesheet_does_not_use_light_canvas() -> None:
    dark = Tokens.dark()
    css = build_stylesheet(dark)
    assert dark.color_bg in css
    assert dark.color_primary in css
    assert Tokens.light().color_bg not in css


def test_tokens_overlay_rejects_unknown_keys() -> None:
    dark = Tokens.dark().overlay({"color_primary": "#7a9e7e", "radius": 8, "motion_fast_ms": 80})
    assert dark.color_primary == "#7a9e7e"
    assert dark.radius == 8
    assert dark.button_radius == 8
    assert dark.motion_fast_ms == 80
    assert dark.color_bg == Tokens.dark().color_bg
    with pytest.raises(ValueError, match="未知 token"):
        Tokens.light().overlay({"color_primry": "#fff"})


def test_density_and_nested_button_tokens() -> None:
    compact = Tokens.light().overlay({"density": "compact"})
    assert compact.density == "compact"
    assert compact.control_height == 28
    assert compact.icon_size == 14
    assert compact.sidebar_compact_width == 52
    sized = Tokens.light().overlay(
        {"density": "compact", "control_height": 36, "button": {"radius": 10}}
    )
    assert sized.control_height == 36
    assert sized.button_radius == 10
    reduced = Tokens.light().overlay({"reduced_motion": 1})
    assert reduced.motion_fast_ms == 0
    assert reduced.motion_ms == 0


def test_python_theme_overrides_and_rejects_typos() -> None:
    from psi6.theme.builtin import Brass, Compact
    from psi6.theme.theme import Theme
    from psi6.theme.tokens import resolve_tokens

    brass = resolve_tokens(Brass)
    assert brass.color_primary == "#6b542e"
    assert brass.color_bg == "#f3efe6"
    compact = Compact().tokens()
    assert compact.density == "compact"
    assert compact.control_height == 28

    class Midnight(Theme):
        name = "midnight"
        base = "dark"
        color_primary = "#4d7c5a"
        button_radius = 8

    loaded = resolve_tokens(Midnight)
    assert loaded.color_primary == "#4d7c5a"
    assert loaded.button_radius == 8
    assert loaded.color_bg == Tokens.dark().color_bg

    with pytest.raises(TypeError, match="未知 token"):

        class Broken(Theme):
            color_primry = "#fff"

        Broken().tokens()


def test_theme_file_paths_are_rejected(tmp_path: Path) -> None:
    from psi6.theme.tokens import resolve_tokens

    path = tmp_path / "user.toml"
    path.write_text('base = "dark"\n', encoding="utf-8")
    with pytest.raises(TypeError, match="Python"):
        resolve_tokens(path)
    with pytest.raises(TypeError, match="Python"):
        resolve_tokens("theme.yaml")


def test_app_switches_light_and_dark_theme(qtbot: QtBot, tmp_path: Path) -> None:
    app = App("psi6-theme-switch", theme="dark", config_root=tmp_path)
    assert Tokens.dark().color_bg in app.qt_app.styleSheet()
    app.set_theme("light")
    assert Tokens.light().color_bg in app.qt_app.styleSheet()
    assert app.tokens.color_bg == Tokens.light().color_bg


def test_app_auto_theme_follows_system(qtbot: QtBot, tmp_path: Path) -> None:
    from psi6.theme.system import system_prefers_dark
    from psi6.theme.tokens import Tokens

    app = App("psi6-auto-theme", theme="auto", config_root=tmp_path)
    expected = Tokens.dark() if system_prefers_dark() else Tokens.light()
    assert app.tokens.color_bg == expected.color_bg


def test_icon_button_recolors_when_theme_switches(qtbot: QtBot, tmp_path: Path) -> None:
    from psi6.ui.icon import IconButton, token_color

    app = App("psi6-icon-theme", theme="light", config_root=tmp_path)
    button = IconButton("play", label="播放")
    qtbot.addWidget(button)
    assert token_color(button) == Tokens.light().color_text
    app.set_theme("dark")
    assert token_color(button) == Tokens.dark().color_text
    assert not button.icon().isNull()
    app.set_theme("light")


def test_combo_down_arrow_uses_themed_chevron(qtbot: QtBot, tmp_path: Path) -> None:
    from PySide6.QtWidgets import QComboBox

    app = App("psi6-combo-arrow", theme="light", config_root=tmp_path)
    css = app.qt_app.styleSheet()
    assert "QComboBox::down-arrow" in css
    assert "psi6icon:chevron-down" in css
    combo = QComboBox()
    combo.addItems(["浅色", "深色"])
    combo.setFixedSize(180, 32)
    qtbot.addWidget(combo)
    combo.show()
    qtbot.waitExposed(combo)
    image = combo.grab().toImage()
    mid = image.height() // 2
    ink = [
        image.pixelColor(x, mid)
        for x in range(max(0, image.width() - 22), max(0, image.width() - 6))
    ]
    assert any(pixel.alpha() > 50 and pixel.red() < 160 for pixel in ink)


def test_apply_theme_publishes_size_tokens(qtbot: QtBot, tmp_path: Path) -> None:
    from psi6.theme.runtime import token_int

    app = App("psi6-size-tokens", theme="light", config_root=tmp_path)
    assert app.qt_app.property("psi6ControlHeight") == 32
    assert token_int("control_height") == 32
    app.set_theme(Tokens.light().overlay({"density": "compact"}))
    assert token_int("control_height") == 28
    assert token_int("icon_size") == 14
    css = app.qt_app.styleSheet()
    assert "min-height: 28px" in css
    app.set_theme("light")
