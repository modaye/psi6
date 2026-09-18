"""自绘辅助：painter 生命周期、圆角路径、颜色混合。控件从此取，不要手写 QPainter.end。"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtGui import QColor, QPaintDevice, QPainter, QPainterPath


@contextmanager
def create_painter(
    device: QPaintDevice,
    *,
    antialias: bool = True,
    clear_pen: bool = True,
) -> Iterator[QPainter]:
    """打开 ``QPainter``，离开时 ``end``。自绘默认去掉 pen/brush。"""

    painter = QPainter(device)
    if antialias:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    if clear_pen:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
    try:
        yield painter
    finally:
        if painter.isActive():
            painter.end()


def as_color(value: str | QColor) -> QColor:
    """token 色字符串或 ``QColor`` 都收成可改的 ``QColor``。"""

    return QColor(value) if isinstance(value, str) else QColor(value)


def mix_color(start: str | QColor, end: str | QColor, amount: float) -> QColor:
    """线性插值。``amount`` 为 0 时用 ``start``。"""

    a = as_color(start)
    b = as_color(end)
    t = max(0.0, min(1.0, amount))
    return QColor(
        int(a.red() + (b.red() - a.red()) * t),
        int(a.green() + (b.green() - a.green()) * t),
        int(a.blue() + (b.blue() - a.blue()) * t),
        int(a.alpha() + (b.alpha() - a.alpha()) * t),
    )


def color_alpha(value: str | QColor, alpha: float) -> QColor:
    """改不透明度，``alpha`` 为 0..1。"""

    color = as_color(value)
    color.setAlphaF(max(0.0, min(1.0, alpha)))
    return color


def rounded_rect_path(
    rect: QRect | QRectF,
    radius: float | tuple[float, float, float, float],
) -> QPainterPath:
    """圆角矩形。四元组为左上、右上、右下、左下半径。"""

    box = QRectF(rect)
    path = QPainterPath()
    if isinstance(radius, tuple):
        half_w = max(0.0, box.width() / 2)
        half_h = max(0.0, box.height() / 2)
        top_left, top_right, bottom_right, bottom_left = (
            min(max(0.0, float(value)), half_w, half_h) for value in radius
        )
        path.moveTo(box.left() + top_left, box.top())
        path.lineTo(box.right() - top_right, box.top())
        if top_right > 0:
            path.arcTo(QRectF(box.right() - 2 * top_right, box.top(), 2 * top_right, 2 * top_right), 90, -90)
        else:
            path.lineTo(box.right(), box.top())
        path.lineTo(box.right(), box.bottom() - bottom_right)
        if bottom_right > 0:
            path.arcTo(
                QRectF(
                    box.right() - 2 * bottom_right,
                    box.bottom() - 2 * bottom_right,
                    2 * bottom_right,
                    2 * bottom_right,
                ),
                0,
                -90,
            )
        else:
            path.lineTo(box.right(), box.bottom())
        path.lineTo(box.left() + bottom_left, box.bottom())
        if bottom_left > 0:
            path.arcTo(
                QRectF(box.left(), box.bottom() - 2 * bottom_left, 2 * bottom_left, 2 * bottom_left),
                270,
                -90,
            )
        else:
            path.lineTo(box.left(), box.bottom())
        path.lineTo(box.left(), box.top() + top_left)
        if top_left > 0:
            path.arcTo(QRectF(box.left(), box.top(), 2 * top_left, 2 * top_left), 180, -90)
        else:
            path.lineTo(box.left(), box.top())
        path.closeSubpath()
        return path
    corner = max(0.0, float(radius))
    path.addRoundedRect(box, corner, corner)
    return path


def scale_around_center(painter: QPainter, rect: QRectF, scale: float) -> None:
    """绕矩形中心缩放。``1`` 为原大小。"""

    if abs(scale - 1.0) < 0.001:
        return
    center = rect.center()
    painter.translate(center)
    painter.scale(scale, scale)
    painter.translate(-center)
