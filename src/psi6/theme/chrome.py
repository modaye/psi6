"""原生下拉/步进箭头：QSS ``image`` 要用搜索前缀，Windows 上 ``file:///`` 不会画出来。"""

from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtCore import QDir
from PySide6.QtWidgets import QApplication

from psi6.icons.registry import svg_for
from psi6.theme.tokens import Tokens

SEARCH_PREFIX = "psi6icon"


def cache_dir() -> Path:
    """主题箭头缓存目录。文件名含颜色，换肤写成另一份。"""

    folder = Path(tempfile.gettempdir()) / "psi6-qss-icons"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def qss_icon_ref(name: str, *, color: str, size: int) -> str:
    """着色后写入缓存，返回 ``psi6icon:file.png`` 这种 QSS 前缀路径。"""

    extent = max(8, int(size))
    stem = f"{name}_{color.lstrip('#')}_{extent}"
    folder = cache_dir()
    QDir.setSearchPaths(SEARCH_PREFIX, [str(folder.resolve())])
    app = QApplication.instance()
    if app is not None:
        from psi6.icons.render import pixmap_for

        ratio = max(1.0, float(app.devicePixelRatio()))
        path = folder / f"{stem}.png"
        pixmap_for(name, color=color, size=max(extent, round(extent * ratio))).save(str(path), "PNG")
        return f"{SEARCH_PREFIX}:{path.name}"
    path = folder / f"{stem}.svg"
    path.write_text(svg_for(name).replace("currentColor", color), encoding="utf-8")
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
    }
