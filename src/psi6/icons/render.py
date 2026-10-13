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


def raster_px(logical: int, ratio: float) -> int:
    """逻辑像素换成位图像素。比例低于 1 时仍用逻辑尺寸，避免图标被缩没。"""

    extent = max(1, int(logical))
    return max(extent, round(extent * max(1.0, float(ratio))))


def device_ratio() -> float:
    """当前应用的设备像素比。没有应用时按 1。"""

    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        return 1.0
    return max(1.0, float(app.devicePixelRatio()))


def pixmap_for(name: str, *, color: str, size: int = 16, ratio: float = 1.0) -> QPixmap:
    """按颜色渲染图标。``color`` 必须是 token 里的色值。

    ``size`` 是逻辑像素。``ratio`` 大于 1 时位图更大，并设置 ``devicePixelRatio``，
    布局仍按逻辑尺寸占位。
    """

    scale = max(1.0, float(ratio))
    pixels = raster_px(size, scale)
    key = (name, pixels, color.lower(), scale)
    cached = _CACHE.get(key)
    if cached is not None:
        return cached
    markup = svg_for(name).replace("currentColor", color)
    renderer = QSvgRenderer(QByteArray(markup.encode("utf-8")))
    image = QImage(pixels, pixels, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    renderer.render(painter, QRectF(0, 0, pixels, pixels))
    painter.end()
    pix = QPixmap.fromImage(image)
    pix.setDevicePixelRatio(scale)
    _CACHE[key] = pix
    return pix


def icon_for(name: str, *, color: str, size: int = 16, ratio: float | None = None) -> QIcon:
    """供按钮 ``setIcon`` 使用。未给 ``ratio`` 时读取当前应用的设备像素比。"""

    return QIcon(pixmap_for(name, color=color, size=size, ratio=device_ratio() if ratio is None else ratio))
