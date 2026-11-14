"""页内文字页签。底部一条主色指示器滑到当前项。

文档页签仍用 ``TabView``（可关闭、可重排）。这里是分段说明用的标签，
不带关闭按钮，也不包一层盒子。
"""

from __future__ import annotations

from PySide6.QtCore import Property, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QFontMetrics, QKeyEvent, QMouseEvent, QPaintEvent, QPen
from PySide6.QtWidgets import QSizePolicy, QStackedWidget, QVBoxLayout, QWidget

from psi6.theme.paint import as_color, create_painter
from psi6.theme.runtime import token_color, token_int
from psi6.ui import motion


class _UnderlineBar(QWidget):
    """只画标签和滑动指示器。内容页由外层栈持有。"""

    current_changed = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("psi6UnderlineBar")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._labels: list[str] = []
        self._current = 0
        self._hover = -1
        self._x = 0.0
        self._w = 0.0

    def _get_x(self) -> float:
        return self._x

    def _set_x(self, value: float) -> None:
        self._x = float(value)
        self.update()

    def _get_w(self) -> float:
        return self._w

    def _set_w(self, value: float) -> None:
        self._w = float(value)
        self.update()

    markX = Property(float, _get_x, _set_x)
    markW = Property(float, _get_w, _set_w)

    def add_label(self, title: str) -> int:
        """追加一个标签。第一项成为当前项，之后追加不切换。"""

        self._labels.append(title)
        if len(self._labels) == 1:
            self._place(False)
        self.updateGeometry()
        self.update()
        return len(self._labels) - 1

    def set_current(self, index: int) -> None:
        """切到 ``index``。指示器在 ``motion_ms`` 内滑过去。"""

        if not 0 <= index < len(self._labels) or index == self._current:
            return
        self._current = index
        self._place(True)
        self.current_changed.emit(index)
        self.update()

    def current_index(self) -> int:
        return self._current if self._labels else -1

    def _rects(self) -> list[QRectF]:
        metrics = QFontMetrics(self.font())
        pad = token_int("space_md")
        rects: list[QRectF] = []
        x = 0.0
        height = float(self.height() or token_int("control_height"))
        for label in self._labels:
            width = metrics.horizontalAdvance(label) + pad * 2
            rects.append(QRectF(x, 0, width, height))
            x += width
        return rects

    def _place(self, animate: bool) -> None:
        if not self._labels:
            return
        rects = self._rects()
        rect = rects[self._current]
        inset = float(token_int("space_md"))
        target_x = rect.x() + inset
        target_w = max(8.0, rect.width() - inset * 2)
        if not animate:
            motion.stop(self, "markX")
            motion.stop(self, "markW")
            self._x = target_x
            self._w = target_w
            self.update()
            return
        motion.animate(self, "markX", self._x, target_x, speed="normal")
        motion.animate(self, "markW", self._w, target_w, speed="normal")

    def sizeHint(self) -> QSize:
        height = token_int("control_height")
        rects = self._rects()
        width = int(rects[-1].right()) if rects else 0
        return QSize(width, height)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        self._place(False)
        super().resizeEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        for index, rect in enumerate(self._rects()):
            if rect.contains(event.position()):
                self.set_current(index)
                break
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        hover = -1
        for index, rect in enumerate(self._rects()):
            if rect.contains(event.position()):
                hover = index
                break
        if hover != self._hover:
            self._hover = hover
            self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        self._hover = -1
        self.update()
        super().leaveEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Right:
            self.set_current(min(self._current + 1, len(self._labels) - 1))
        elif event.key() == Qt.Key.Key_Left:
            self.set_current(max(self._current - 1, 0))
        else:
            super().keyPressEvent(event)

    def paintEvent(self, _event: QPaintEvent) -> None:
        primary = as_color(token_color("color_primary"))
        muted = as_color(token_color("color_muted"))
        hover = as_color(token_color("color_hover"))
        line = as_color(token_color("color_border_subtle"))
        focus = as_color(token_color("color_focus"))
        radius = token_int("radius")
        with create_painter(self, clear_pen=False) as painter:
            painter.setFont(self.font())
            rects = self._rects()
            for index, (label, rect) in enumerate(zip(self._labels, rects, strict=True)):
                if index == self._hover and index != self._current:
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(hover)
                    bubble = rect.adjusted(6, 6, -6, -6)
                    painter.drawRoundedRect(bubble, radius, radius)
                selected = index == self._current
                painter.setPen(primary if selected else muted)
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)
                if selected and self.hasFocus():
                    pen = QPen(focus)
                    pen.setWidth(token_int("focus_ring_width"))
                    painter.setPen(pen)
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    ring = rect.adjusted(4, 4, -4, -6)
                    painter.drawRoundedRect(ring, radius, radius)
            painter.setPen(line)
            painter.drawLine(0, self.height() - 1, self.width(), self.height() - 1)
            if self._w > 0:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(primary)
                bar = QRectF(self._x, self.height() - 3, self._w, 2)
                painter.drawRoundedRect(bar, 1, 1)


class UnderlineTabs(QWidget):
    """文字页签加内容栈。当前项底下的主色条会滑过去。"""

    current_changed = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("psi6UnderlineTabs")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._bar = _UnderlineBar()
        self._stack = QStackedWidget()
        layout.addWidget(self._bar)
        layout.addWidget(self._stack, stretch=1)
        self._bar.current_changed.connect(self._on_bar)

    def add_tab(self, title: str, widget: QWidget) -> int:
        """追加一页。``title`` 是页签文字，``widget`` 是对应内容。"""

        self._stack.addWidget(widget)
        return self._bar.add_label(title)

    def set_current(self, index: int) -> None:
        """按序号切换。越界时保持原样。"""

        self._bar.set_current(index)

    def current_index(self) -> int:
        return self._bar.current_index()

    def _on_bar(self, index: int) -> None:
        self._stack.setCurrentIndex(index)
        self.current_changed.emit(index)
