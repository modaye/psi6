"""图标覆盖：register_icon 与主题 icon_dir。"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

from pytestqt.qtbot import QtBot

from psi6.icons.glyphs import GLYPHS
from psi6.icons.registry import clear_icon_overrides, register_icon, svg_for
from psi6.runtime.app import App
from psi6.theme.theme import Theme
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

    class Marked(Theme):
        name = "marked"
        icon_dir = str(folder)

    app = App("psi6-icon-dir", theme=Marked, config_root=tmp_path)
    assert app.qt_app is not None
    assert "<rect" in svg_for("search")
    app.set_theme("light")
    assert svg_for("search") == GLYPHS["search"]


def test_theme_module_icons_ignore_cwd(qtbot: QtBot, tmp_path: Path, monkeypatch) -> None:
    del qtbot
    pack = tmp_path / "pack"
    icons = pack / "icons"
    icons.mkdir(parents=True)
    icons.joinpath("search.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><circle cx="12" cy="12" r="8"/></svg>',
        encoding="utf-8",
    )
    source = pack / "midnight.py"
    source.write_text(
        "from psi6.theme import Theme\n"
        "\n"
        "class Midnight(Theme):\n"
        "    name = 'midnight'\n"
        "    base = 'dark'\n"
        "    color_primary = '#4d7c5a'\n",
        encoding="utf-8",
    )
    spec = importlib.util.spec_from_file_location("psi6_test_midnight", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    monkeypatch.chdir(tmp_path)
    assert Path(os.getcwd()) == tmp_path
    app = App("psi6-icon-pack", theme=module.Midnight, config_root=tmp_path / "cfg")
    assert app.tokens.color_primary == "#4d7c5a"
    assert Path(app.tokens.icon_dir) == icons.resolve()
    assert "<circle" in svg_for("search")
    app.set_theme("light")
    assert svg_for("search") == GLYPHS["search"]


def test_missing_explicit_icon_dir_raises(tmp_path: Path) -> None:
    class Missing(Theme):
        icon_dir = "no-such-icons"

    # 相对路径相对定义类的模块（本测试文件所在目录），不相对 tmp_path / cwd。
    del tmp_path
    try:
        Missing().tokens()
    except FileNotFoundError as exc:
        assert "no-such-icons" in str(exc)
    else:
        raise AssertionError("缺失的 icon_dir 应抛出 FileNotFoundError")


def test_light_tokens_have_no_icon_dir() -> None:
    assert Tokens.light().icon_dir == ""
