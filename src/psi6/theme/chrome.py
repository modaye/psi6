"""QSS 用的图标：写成逻辑尺寸的 SVG，由样式表引擎按当前分辨率绘制。

位图在 QSS ``image`` 里的高 DPI 行为不可控：按 ``devicePixelRatio`` 出图会被
放大裁切、涂出控件边界；按逻辑像素出图会被引擎继续放大并留下毛边。SVG 在
绘制时才栅格化，任何缩放比例下几何都正确。路径用搜索前缀，Windows 上
``file:///`` 不会画出来。
"""

from __future__ import annotations

import hashlib
import tempfile
import time
from pathlib import Path

from PySide6.QtCore import QDir

from psi6.icons.registry import svg_for
from psi6.theme.tokens import Tokens

SEARCH_PREFIX = "psi6icon"
_CACHE_MAX_AGE = 30 * 24 * 60 * 60
_pruned = False
_IMAGES: dict[tuple[int, int], dict[str, str]] = {}


def cache_dir() -> Path:
    """主题箭头缓存目录。文件名含颜色，换肤写成另一份。"""

    folder = Path(tempfile.gettempdir()) / "psi6-qss-icons"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def cleanup_cache(*, max_age: float = _CACHE_MAX_AGE) -> int:
    """删掉长期不用的缓存 SVG，避免不断换肤把临时目录堆满。

    只清超过 ``max_age`` 秒的文件，并吞掉 Windows 上被占用的文件。
    """

    folder = Path(tempfile.gettempdir()) / "psi6-qss-icons"
    if not folder.is_dir():
        return 0
    cutoff = time.time() - max_age
    removed = 0
    for path in folder.glob("*.svg"):
        try:
            if path.stat().st_mtime >= cutoff:
                continue
            path.unlink()
            removed += 1
        except OSError:
            continue
    return removed


def _color_slug(color: str) -> str:
    text = color.strip().lower()
    if text.startswith("#") and len(text) > 1:
        return text[1:]
    return "c" + hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]


def qss_icon_ref(name: str, *, color: str, size: int) -> str:
    """着色后写成逻辑尺寸的 SVG，返回 ``psi6icon:file.svg`` 这种 QSS 前缀路径。"""

    global _pruned
    if not _pruned:
        _pruned = True
        cleanup_cache()
    extent = max(8, int(size))
    stem = f"{name}_{_color_slug(color)}_{extent}"
    folder = cache_dir()
    QDir.setSearchPaths(SEARCH_PREFIX, [str(folder.resolve())])
    path = folder / f"{stem}.svg"
    markup = svg_for(name).replace("currentColor", color)
    markup = markup.replace('width="24" height="24"', f'width="{extent}" height="{extent}"', 1)
    # 同一主题反复套用时不重写临时文件，减少磁盘抖动。
    if not path.is_file() or path.read_text(encoding="utf-8") != markup:
        path.write_text(markup, encoding="utf-8")
    return f"{SEARCH_PREFIX}:{path.name}"


def chrome_images(tokens: Tokens) -> dict[str, str]:
    """下拉与步进箭头的 QSS 图。同一套 token 只算一次，避免换肤时反复读盘比对。"""

    key = (hash(tokens.resolve_states()), tokens.icon_size)
    cached = _IMAGES.get(key)
    if cached is not None:
        return dict(cached)
    images = _build_chrome_images(tokens)
    if len(_IMAGES) > 16:
        _IMAGES.clear()
    _IMAGES[key] = dict(images)
    return images


def _build_chrome_images(tokens: Tokens) -> dict[str, str]:

    size = max(12, min(tokens.icon_size, 16))
    # 页签关闭按钮：QSS 一旦写 background / border / image 就会接管掉 Qt 原生
    # 的叉号，所以必须自己给一份图形。
    close = max(8, min(tokens.icon_size, 12))
    # 表头排序指示器比图标更小一档，否则会把表头文字挤开。
    small = max(8, min(tokens.icon_size - 4, 12))
    return {
        "down": qss_icon_ref("chevron-down", color=tokens.color_muted, size=size),
        "up": qss_icon_ref("chevron-up", color=tokens.color_muted, size=size),
        "down_on": qss_icon_ref("chevron-up", color=tokens.color_text, size=size),
        "down_disabled": qss_icon_ref("chevron-down", color=tokens.color_disabled, size=size),
        "up_disabled": qss_icon_ref("chevron-up", color=tokens.color_disabled, size=size),
        "check_on": qss_icon_ref("check", color=tokens.color_on_primary, size=size),
        "minus_on": qss_icon_ref("minus", color=tokens.color_on_primary, size=size),
        "dot_on": qss_icon_ref("dot", color=tokens.color_primary, size=size),
        "check_muted": qss_icon_ref("check", color=tokens.color_muted, size=size),
        "dot_muted": qss_icon_ref("dot", color=tokens.color_muted, size=size),
        "tab_close": qss_icon_ref("x", color=tokens.color_muted, size=close),
        "tab_close_on": qss_icon_ref("x", color=tokens.color_text, size=close),
        # 树的分支箭头：收起为右向、展开为下向。同一份图形在两种状态下着色，
        # 悬停和选中不改色，改的是行填充。
        "branch_closed": qss_icon_ref("chevron-right", color=tokens.color_muted, size=size),
        "branch_open": qss_icon_ref("chevron-down", color=tokens.color_muted, size=size),
        "branch_closed_disabled": qss_icon_ref(
            "chevron-right", color=tokens.color_disabled, size=size
        ),
        # 菜单的勾选与单选标记。QSS 一旦接管 QMenu::indicator，Qt 不再代画。
        "menu_check": qss_icon_ref("check", color=tokens.color_text, size=size),
        "menu_dot": qss_icon_ref("dot", color=tokens.color_text, size=size),
        "menu_check_disabled": qss_icon_ref("check", color=tokens.color_disabled, size=size),
        "menu_dot_disabled": qss_icon_ref("dot", color=tokens.color_disabled, size=size),
        # 表头排序指示器。Qt 原生三角在浅色主题下是灰块，与箭头语言不一致。
        "sort_asc": qss_icon_ref("chevron-up", color=tokens.color_muted, size=small),
        "sort_desc": qss_icon_ref("chevron-down", color=tokens.color_muted, size=small),
    }
