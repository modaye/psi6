"""迷你折线，给 StatCard / 监控用。"""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import QPointF
from PySide6.QtGui import QPainterPath, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from psi6.theme.paint import as_color, create_painter
from psi6.theme.runtime import token_color


class Sparkline(QWidget):
    """一串数字画成折线。颜色跟 token 的 primary。"""

    def __init__(
        self,
        values: Sequence[float] = (),
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("psi6Sparkline")
        self.setFixedHeight(28)
        self.setMinimumWidth(72)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._values = [float(item) for item in values]

    def set_values(self, values: Sequence[float]) -> None:
        self._values = [float(item) for item in values]
        self.update()

    def paintEvent(self, event) -> None:  # noqa: ANN001
        del event
        if len(self._values) < 2:
            return
        with create_painter(self, clear_pen=False) as painter:
            color = as_color(token_color("primary"))
            pen = QPen(color, 1.6)
            painter.setPen(pen)
            lo = min(self._values)
            hi = max(self._values)
            span = hi - lo or 1.0
            width = max(self.width() - 4, 1)
            height = max(self.height() - 6, 1)
            path = QPainterPath()
            for index, value in enumerate(self._values):
                x = 2 + width * index / (len(self._values) - 1)
                y = 3 + height * (1 - (value - lo) / span)
                point = QPointF(x, y)
                if index == 0:
                    path.moveTo(point)
                else:
                    path.lineTo(point)
            painter.drawPath(path)
