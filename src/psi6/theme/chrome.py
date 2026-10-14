"""QSS 用的图标：写成逻辑尺寸的 SVG，由样式表引擎按当前分辨率绘制。

位图在 QSS ``image`` 里的高 DPI 行为不可控：按 ``devicePixelRatio`` 出图会被
放大裁切、涂出控件边界；按逻辑像素出图会被引擎继续放大并留下毛边。SVG 在
绘制时才栅格化，任何缩放比例下几何都正确。路径用搜索前缀，Windows 上
``file:///`` 不会画出来。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtCore import QDir

from psi6.icons.registry import svg_for
from psi6.theme.tokens import Tokens

SEARCH_PREFIX = "psi6icon"


def cache_dir() -> Path:
    """主题箭头缓存目录。文件名含颜色，换肤写成另一份。"""

    folder = Path(tempfile.gettempdir()) / "psi6-qss-icons"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def qss_icon_ref(name: str, *, color: str, size: int) -> str:
    """着色后写成逻辑尺寸的 SVG，返回 ``psi6icon:file.svg`` 这种 QSS 前缀路径。"""

    extent = max(8, int(size))
    stem = f"{name}_{color.lstrip('#')}_{extent}"
    folder = cache_dir()
    QDir.setSearchPaths(SEARCH_PREFIX, [str(folder.resolve())])
    path = folder / f"{stem}.svg"
    markup = svg_for(name).replace("currentColor", color)
    markup = markup.replace('width="24" height="24"', f'width="{extent}" height="{extent}"', 1)
    path.write_text(markup, encoding="utf-8")
    return f"{SEARCH_PREFIX}:{path.name}"


def chrome_images(tokens: Tokens) -> dict[str, str]:
    """下拉与步进箭头的 QSS 图。"""

    size = max(12, min(tokens.icon_size, 16))
    return {
        "down": qss_icon_ref("chevron-down", color=tokens.color_muted, size=size),
        "up": qss_icon_ref("chevron-up", color=tokens.color_muted, size=size),
        "down_on": qss_icon_ref("chevron-up", color=tokens.color_text, size=size),
        "down_disabled": qss_icon_ref("chevron-down", color=tokens.color_disabled, size=size),
        "up_disabled": qss_icon_ref("chevron-up", color=tokens.color_disabled, size=size),
        "check_on": qss_icon_ref("check", color=tokens.color_on_primary, size=size),
        "minus_on": qss_icon_ref("minus", color=tokens.color_on_primary, size=size),
        "dot_on": qss_icon_ref("dot", color=tokens.color_on_primary, size=size),
        "check_muted": qss_icon_ref("check", color=tokens.color_muted, size=size),
        "dot_muted": qss_icon_ref("dot", color=tokens.color_muted, size=size),
    }
