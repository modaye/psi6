"""骨架屏：加载时的占位条。

底色是 ``color_hover``。一条宽度为一半的白色高光从左扫到右，两端透明、
中段叠在底色上，并裁在圆角里。高光不用表面色：浅色主题上表面色和悬停色
几乎一样，深色主题上表面色比悬停更暗，会扫出一条黑带。

扫光只在控件可见时循环，一圈是 ``motion_ms`` 的五倍，缓动为线性。
减少动效时停在底色上，不留一条停住的亮带。离开页面就停。
"""

from __future__ import annotations

from PySide6.QtCore import Property, QEvent, QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient
from PySide6.QtWidgets import QWidget

from psi6.theme.paint import color_alpha, create_painter, rounded_rect_path
from psi6.theme.runtime import token_color, token_int, token_ms
from psi6.ui import motion

# 高光中段不透明度，0..255。两端为 0。与扫光带宽（控件宽度的一半）一起决定软硬。
_SHEEN = "#ffffff"
_SHEEN_ALPHA = 150 / 255
_PERIOD = 5

_THEME_EVENTS = {QEvent.Type.PaletteChange, QEvent.Type.StyleChange}


class Skeleton(QWidget):
    """一条圆角占位。正方形配上半径的一半就是圆头像。"""

    def __init__(
        self,
        width: int = 200,
        height: int = 14,
        radius: int | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("psi6Skeleton")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._shimmer = 0.0
        self._radius = radius
        self.setFixedSize(max(1, int(width)), max(1, int(height)))

    def _get_shimmer(self) -> float:
        return self._shimmer

    def _set_shimmer(self, value: float) -> None:
        self._shimmer = float(value)
        self.update()

    shimmer = Property(float, _get_shimmer, _set_shimmer)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._start()

    def hideEvent(self, event) -> None:
        motion.stop(self, "shimmer")
        super().hideEvent(event)

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if event.type() in _THEME_EVENTS:
            self.update()

    def paintEvent(self, _event) -> None:
        rect = QRectF(self.rect())
        radius = self._corner_radius()
        path = rounded_rect_path(rect, radius)
        with create_painter(self) as painter:
            painter.setBrush(QColor(token_color("hover")))
            painter.drawPath(path)
            painter.setClipPath(path)
            band = max(rect.width() * 0.5, 1.0)
            origin = -band + (rect.width() + band) * self._shimmer
            gradient = QLinearGradient(origin, 0.0, origin + band, 0.0)
            gradient.setColorAt(0.0, color_alpha(_SHEEN, 0.0))
            gradient.setColorAt(0.5, color_alpha(_SHEEN, _SHEEN_ALPHA))
            gradient.setColorAt(1.0, color_alpha(_SHEEN, 0.0))
            painter.setBrush(gradient)
            painter.drawPath(path)

    def _corner_radius(self) -> float:
        """默认用 ``radius``。不超过短边的一半，避免圆角把细条撑破。"""

        requested = self._radius if self._radius is not None else token_int("radius")
        limit = min(self.width(), self.height()) / 2
        return float(max(0.0, min(float(requested), limit)))

    def _start(self) -> None:
        """可见时开扫。减少动效或时长为 0 时回到底色。"""

        if not motion.motion_enabled():
            motion.stop(self, "shimmer")
            self._shimmer = 0.0
            self.update()
            return
        motion.animate(
            self,
            "shimmer",
            0.0,
            1.0,
            duration=token_ms("normal") * _PERIOD,
            curve="linear",
            loop=-1,
        )
