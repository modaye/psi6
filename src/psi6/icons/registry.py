"""图标覆盖：代码注册优先，其次主题目录 / JSON，最后内置 glyph。"""

from __future__ import annotations

from pathlib import Path

from psi6.icons.glyphs import GLYPHS, _SVG

_USER: dict[str, str] = {}
_THEME: dict[str, str] = {}


def register_icon(name: str, svg: str) -> None:
    """用完整 SVG 或 path 片段覆盖一个图标名。主题切换不会清掉。"""

    _USER[name] = _normalize_svg(svg)
    from psi6.icons.render import clear_icon_cache

    clear_icon_cache()


def register_icon_dir(path: str | Path) -> None:
    """把目录里的 ``name.svg`` 注册为用户覆盖。"""

    folder = Path(path).expanduser()
    if not folder.is_dir():
        return
    for file in folder.glob("*.svg"):
        _USER[file.stem] = _normalize_svg(file.read_text(encoding="utf-8"))
    from psi6.icons.render import clear_icon_cache

    clear_icon_cache()


def clear_icon_overrides() -> None:
    """清掉代码注册的图标，不影响主题层。"""

    _USER.clear()
    from psi6.icons.render import clear_icon_cache

    clear_icon_cache()


def apply_theme_icons(*, icon_dir: str = "", icons: tuple[tuple[str, str], ...] = ()) -> None:
    """主题切换时重装主题层覆盖；不碰 ``register_icon``。"""

    _THEME.clear()
    if icon_dir:
        folder = Path(icon_dir).expanduser()
        if folder.is_dir():
            for file in folder.glob("*.svg"):
                _THEME[file.stem] = _normalize_svg(file.read_text(encoding="utf-8"))
    for name, markup in icons:
        _THEME[name] = _normalize_svg(markup)
    from psi6.icons.render import clear_icon_cache

    clear_icon_cache()


def svg_for(name: str) -> str:
    """解析最终 SVG：用户覆盖 > 主题 > 内置。未知名称回落到 ``circle-dot``。"""

    if name in _USER:
        return _USER[name]
    if name in _THEME:
        return _THEME[name]
    return GLYPHS.get(name, GLYPHS["circle-dot"])


def _normalize_svg(markup: str) -> str:
    text = markup.strip()
    if text.startswith("<svg"):
        return text
    return _SVG.format(body=text)
