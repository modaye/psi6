"""无边框窗口的圆角：Windows 11 走 DWM，其它环境用 mask 裁切。"""

from __future__ import annotations

import sys
from ctypes import Structure, byref, c_int, sizeof
from ctypes.wintypes import HWND

from PySide6.QtCore import QPoint, QRect, QRectF, QSize, Qt
from PySide6.QtGui import QGuiApplication, QPixmap, QRegion
from PySide6.QtWidgets import QApplication, QWidget

from psi6.theme.paint import create_painter, rounded_rect_path

DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWCP_DONOTROUND = 1
DWMWCP_ROUND = 2


class _MARGINS(Structure):
    _fields_ = [
        ("cxLeftWidth", c_int),
        ("cxRightWidth", c_int),
        ("cyTopHeight", c_int),
        ("cyBottomHeight", c_int),
    ]


def window_radius() -> int:
    """当前主题的窗口圆角。缺省 10，接近 Windows 11 主窗口。"""

    app = QApplication.instance()
    if app is not None:
        value = app.property("psi6WindowRadius")
        if isinstance(value, int) and value >= 0:
            return value
    return 10


def apply_native_round(widget: QWidget, *, rounded: bool) -> bool:
    """Win11 合成器圆角 + 细阴影。offscreen / 失败时返回 False。"""

    if sys.platform != "win32":
        return False
    if QGuiApplication.platformName() == "offscreen":
        return False
    try:
        from ctypes import windll

        hwnd = HWND(int(widget.winId()))
        dwmapi = windll.dwmapi
        preference = c_int(DWMWCP_ROUND if rounded else DWMWCP_DONOTROUND)
        result = dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_WINDOW_CORNER_PREFERENCE,
            byref(preference),
            sizeof(preference),
        )
        if result != 0:
            return False
        margins = _MARGINS(0, 0, 0, 1)
        dwmapi.DwmExtendFrameIntoClientArea(hwnd, byref(margins))
        return True
    except (AttributeError, OSError, ValueError):
        return False


def round_mask(rect: QRect, radius: int) -> QRegion:
    """给整窗做圆角裁切。最大化时应改用空 region（调用方 ``clearMask``）。"""

    if radius <= 0 or rect.width() <= 0 or rect.height() <= 0:
        return QRegion(rect)
    path = rounded_rect_path(rect, radius)
    return QRegion(path.toFillPolygon().toPolygon())


def supports_window_mask() -> bool:
    """offscreen 插件不能 ``setMask``。"""

    return QGuiApplication.platformName() != "offscreen"


def hit_resize_edge(
    pos: QPoint,
    size: QSize,
    *,
    thickness: int = 8,
    blocked: QRect | None = None,
) -> str | None:
    """按窗口坐标判断拉伸边。内容区与标题栏按钮返回 None。"""

    if blocked is not None and blocked.contains(pos):
        return None
    width = size.width()
    height = size.height()
    if width <= 0 or height <= 0:
        return None
    x = pos.x()
    y = pos.y()
    if x < 0 or y < 0 or x >= width or y >= height:
        return None
    left = x <= thickness
    right = x >= width - thickness
    top = y <= thickness
    bottom = y >= height - thickness
    if top and left:
        return "top-left"
    if top and right:
        return "top-right"
    if bottom and left:
        return "bottom-left"
    if bottom and right:
        return "bottom-right"
    if left:
        return "left"
    if right:
        return "right"
    if top:
        return "top"
    if bottom:
        return "bottom"
    return None


def grip_rects(
    size: QSize,
    *,
    thickness: int = 8,
    blocked: QRect | None = None,
) -> dict[str, QRect]:
    """四边与四角拉伸热区。``blocked`` 通常是标题栏按钮，避免盖住关闭。"""

    width = size.width()
    height = size.height()
    edge = thickness
    if width <= 0 or height <= 0:
        return {}
    top_width = max(0, width - 2 * edge)
    mid_height = max(0, height - 2 * edge)
    rects = {
        "left": QRect(0, edge, edge, mid_height),
        "right": QRect(width - edge, edge, edge, mid_height),
        "top": QRect(edge, 0, top_width, edge),
        "bottom": QRect(edge, height - edge, top_width, edge),
        "top-left": QRect(0, 0, edge, edge),
        "top-right": QRect(width - edge, 0, edge, edge),
        "bottom-left": QRect(0, height - edge, edge, edge),
        "bottom-right": QRect(width - edge, height - edge, edge, edge),
    }
    if blocked is not None and blocked.isValid():
        top = rects["top"]
        if top.intersects(blocked):
            top.setWidth(max(0, blocked.left() - top.left()))
            rects["top"] = top
        if rects["top-right"].intersects(blocked):
            rects["top-right"] = QRect()
        if rects["right"].intersects(blocked):
            right = rects["right"]
            right.setTop(max(right.top(), blocked.bottom()))
            rects["right"] = right
    return {name: rect for name, rect in rects.items() if rect.isValid() and rect.width() > 0 and rect.height() > 0}


def grab_rounded(widget: QWidget, *, radius: int | None = None) -> QPixmap:
    """截图时裁出圆角，供离屏 visual QA 使用。"""

    pixmap = widget.grab()
    size = window_radius() if radius is None else radius
    if size <= 0:
        return pixmap
    rounded = QPixmap(pixmap.size())
    rounded.fill(Qt.GlobalColor.transparent)
    with create_painter(rounded, clear_pen=False) as painter:
        painter.setClipPath(rounded_rect_path(QRectF(pixmap.rect()), float(size)))
        painter.drawPixmap(0, 0, pixmap)
    return rounded
