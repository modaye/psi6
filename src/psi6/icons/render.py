"""把描边 SVG 渲成带 token 颜色的 QIcon / QPixmap。"""

from __future__ import annotations

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QIcon, QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from psi6.icons.registry import svg_for

_CACHE: dict[tuple[str, int, str], QPixmap] = {}


def clear_icon_cache() -> None:
    """主题切换后丢掉着色缓存。"""

    _CACHE.clear()


def pixmap_for(name: str, *, color: str, size: int = 16) -> QPixmap:
    """按颜色渲染图标。``color`` 必须是 token 里的色值。"""

    key = (name, size, color.lower())
    cached = _CACHE.get(key)
    if cached is not None:
        return cached
    markup = svg_for(name).replace("currentColor", color)
    renderer = QSvgRenderer(QByteArray(markup.encode("utf-8")))
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    pix = QPixmap.fromImage(image)
    _CACHE[key] = pix
    return pix


def icon_for(name: str, *, color: str, size: int = 16) -> QIcon:
    """供按钮 ``setIcon`` 使用。"""

    return QIcon(pixmap_for(name, color=color, size=size))
