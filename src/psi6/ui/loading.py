"""加载指示。和确定进度条不是一回事。

``Spinner`` 是旋转圆弧，``BusyBar`` 是一条来回滑的不确定进度。
已知总量时用 ``QProgressBar`` 或 ``StatusProgress``，不要拿它们代替加载。
两者只在可见时循环。减少动效时停住，不转、不滑。
"""

from __future__ import annotations

from PySide6.QtCore import Property, QRectF, Qt
from PySide6.QtGui import QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from psi6.theme.paint import as_color, create_painter
from psi6.theme.runtime import token_color, token_ms
from psi6.ui import motion

_SPIN_TURNS = 4
_BAR_PERIOD = 5


class Spinner(QWidget):
    """一圈旋转的圆弧。``size`` 是边长。"""

    def __init__(self, size: int = 20, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("psi6Spinner")
        self._angle = 0.0
        extent = max(8, int(size))
        self.setFixedSize(extent, extent)

    def _get_angle(self) -> float:
        return self._angle

    def _set_angle(self, value: float) -> None:
        self._angle = float(value)
        self.update()

    angle = Property(float, _get_angle, _set_angle)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._start()

    def hideEvent(self, event) -> None:
        motion.stop(self, "angle")
        super().hideEvent(event)

    def paintEvent(self, _event) -> None:
        with create_painter(self, clear_pen=False) as painter:
            pen = QPen(as_color(token_color("primary")))
            pen.setWidthF(2.2)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            rect = QRectF(self.rect()).adjusted(2.0, 2.0, -2.0, -2.0)
            painter.drawArc(rect, int(-self._angle * 16), 300 * 16)

    def _start(self) -> None:
        duration = token_ms("normal") * _SPIN_TURNS
        if duration <= 0:
            motion.stop(self, "angle")
            self._angle = 0.0
            self.update()
            return
        motion.animate(
            self,
            "angle",
            0.0,
            360.0,
            duration=duration,
            curve="linear",
            loop=-1,
        )


class BusyBar(QWidget):
    """不确定进度：一段主色在轨道里滑过。宽度由调用方定。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("psi6BusyBar")
        self._phase = 0.0
        self.setFixedHeight(6)
        self.setMinimumWidth(120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def _get_phase(self) -> float:
        return self._phase

    def _set_phase(self, value: float) -> None:
        self._phase = float(value)
        self.update()

    phase = Property(float, _get_phase, _set_phase)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._start()

    def hideEvent(self, event) -> None:
        motion.stop(self, "phase")
        super().hideEvent(event)

    def paintEvent(self, _event) -> None:
        rect = QRectF(self.rect())
        radius = rect.height() / 2
        with create_painter(self) as painter:
            painter.setBrush(as_color(token_color("border_subtle")))
            painter.drawRoundedRect(rect, radius, radius)
            span = rect.width() * 0.35
            x = (rect.width() + span) * self._phase - span
            painter.setBrush(as_color(token_color("primary")))
            painter.drawRoundedRect(QRectF(x, 0, span, rect.height()), radius, radius)

    def _start(self) -> None:
        duration = token_ms("normal") * _BAR_PERIOD
        if duration <= 0:
            motion.stop(self, "phase")
            self._phase = 0.0
            self.update()
            return
        motion.animate(
            self,
            "phase",
            0.0,
            1.0,
            duration=duration,
            curve="in_out",
            loop=-1,
        )
