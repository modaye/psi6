"""图标覆盖：register_icon 与主题 icon_dir。"""

from __future__ import annotations

from pathlib import Path

from pytestqt.qtbot import QtBot

from psi6.icons.glyphs import GLYPHS
from psi6.icons.registry import clear_icon_overrides, register_icon, svg_for
from psi6.runtime.app import App
from psi6.theme.tokens import Tokens


def test_register_icon_overrides_builtin() -> None:
    original = svg_for("search")
    register_icon("search", '<circle cx="12" cy="12" r="4"/>')
    try:
        assert "r=\"4\"" in svg_for("search")
        assert svg_for("search") != original
    finally:
        clear_icon_overrides()
    assert svg_for("search") == GLYPHS["search"]


def test_theme_icon_dir_overrides(qtbot: QtBot, tmp_path: Path) -> None:
    del qtbot
    folder = tmp_path / "icons"
    folder.mkdir()
    folder.joinpath("search.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><rect width="24" height="24"/></svg>',
        encoding="utf-8",
    )
    theme = tmp_path / "theme.json"
    Tokens.light().overlay({"icon_dir": str(folder)}).dump(theme)
    app = App("psi6-icon-dir", theme=theme, config_root=tmp_path)
    assert app.qt_app is not None
    assert "<rect" in svg_for("search")
    app.set_theme("light")
    assert svg_for("search") == GLYPHS["search"]


def test_theme_pack_uses_same_name_svgs(qtbot: QtBot, tmp_path: Path) -> None:
    del qtbot
    pack = tmp_path / "ocean"
    icons = pack / "icons"
    icons.mkdir(parents=True)
    pack.joinpath("theme.toml").write_text('base = "dark"\ncolor_primary = "#4d7c5a"\n', encoding="utf-8")
    icons.joinpath("search.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><circle cx="12" cy="12" r="8"/></svg>',
        encoding="utf-8",
    )
    app = App("psi6-icon-pack", theme=pack, config_root=tmp_path)
    assert app.tokens.color_primary == "#4d7c5a"
    assert "<circle" in svg_for("search")
    app.set_theme("light")
    assert svg_for("search") == GLYPHS["search"]


def test_theme_file_uses_icons_stem_folder(tmp_path: Path) -> None:
    theme = tmp_path / "dark.toml"
    theme.write_text('base = "dark"\n', encoding="utf-8")
    named = tmp_path / "icons" / "dark"
    named.mkdir(parents=True)
    named.joinpath("play.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M8 6v12l10-6z"/></svg>',
        encoding="utf-8",
    )
    loaded = Tokens.load(theme)
    folder = Path(loaded.icon_dir)
    assert folder.name == "dark"
    assert folder.parent.name == "icons"
    app = App("psi6-icon-stem", theme=theme, config_root=tmp_path)
    assert "<path" in svg_for("play")
    app.set_theme("light")
