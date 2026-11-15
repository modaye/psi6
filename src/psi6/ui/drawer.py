"""盖住宿主窗口的右侧抽屉。

不进页面布局。从右边滑入，背后是一层遮罩。点遮罩或按 Esc 关闭。
关窗口、取消任务不是这件事。

遮罩用透明度效果，而不是半透明窗口。子控件的透明背景在 Windows 上会铺成一块黑。
面板和遮罩是兄弟，这样淡化遮罩时不会把面板一起淡掉。
"""

from __future__ import annotations

from PySide6.QtCore import Property, QEvent, QObject, Qt, Signal
from PySide6.QtGui import QColor, QKeySequence, QPalette, QShortcut
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from psi6.theme.colors import parse_color
from psi6.theme.runtime import token_color
from psi6.ui import motion
from psi6.ui.chrome import Card, HLine
from psi6.ui.icon import IconButton


class Drawer(QWidget):
    """右侧滑入的面板。``host`` 是被盖住的窗口或页面。"""

    closed = Signal()

    def __init__(self, title: str, host: QWidget, *, width: int = 360) -> None:
        super().__init__(host)
        self.setObjectName("psi6Drawer")
        self._title = title
        self._host = host
        self._width = max(240, int(width))
        self._progress = 0.0
        self._closing = False
        self._ink = QColor(27, 25, 22)
        self.setVisible(False)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._veil = QGraphicsOpacityEffect(self)
        self._veil.setOpacity(0.0)
        self.setGraphicsEffect(self._veil)
        host.installEventFilter(self)

        self._panel = Card(elevated=True, parent=host)
        self._panel.hide()
        layout = self._panel.body
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        header = QWidget()
        row = QHBoxLayout(header)
        row.setContentsMargins(18, 14, 12, 14)
        row.setSpacing(8)
        heading = QLabel(title)
        heading.setObjectName("psi6DialogTitle")
        row.addWidget(heading)
        row.addStretch(1)
        close = IconButton("x", label="关闭", extent=28)
        close.clicked.connect(self.close_drawer)
        row.addWidget(close)
        layout.addWidget(header)
        layout.addWidget(HLine())
        body_host = QWidget()
        self._body = QVBoxLayout(body_host)
        self._body.setContentsMargins(18, 18, 18, 18)
        self._body.setSpacing(12)
        layout.addWidget(body_host, stretch=1)

        self._escape = QShortcut(QKeySequence(Qt.Key.Key_Escape), host)
        self._escape.setContext(Qt.ShortcutContext.WindowShortcut)
        self._escape.setEnabled(False)
        self._escape.activated.connect(self.close_drawer)

    def body(self) -> QVBoxLayout:
        """面板里的内容布局。打开之前把控件加进来。"""

        return self._body

    def _get_progress(self) -> float:
        return self._progress

    def _set_progress(self, value: float) -> None:
        self._progress = float(value)
        self._relayout()
        self.update()

    progress = Property(float, _get_progress, _set_progress)

    def open(self) -> None:
        """滑入并盖住宿主。减少动效时直接到位。"""

        self._closing = False
        self._escape.setEnabled(True)
        self._relayout()
        self.setVisible(True)
        self._panel.setVisible(True)
        self.raise_()
        self._panel.raise_()
        self._panel.setFocus()
        motion.animate(self, "progress", self._progress, 1.0, speed="normal", curve="enter")

    def close_drawer(self) -> None:
        """滑出。结束后隐藏，并发出 ``closed``。"""

        if self._closing or not self.isVisible():
            return
        self._closing = True
        motion.animate(
            self,
            "progress",
            self._progress,
            0.0,
            speed="normal",
            curve="exit",
            on_finish=self._hide,
        )

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self._host and event.type() == QEvent.Type.Resize and self.isVisible():
            self._relayout()
        return super().eventFilter(watched, event)

    def mousePressEvent(self, event) -> None:
        self.close_drawer()
        super().mousePressEvent(event)

    def _relayout(self) -> None:
        host = self.parentWidget()
        if host is None:
            return
        parsed = parse_color(token_color("overlay")) or (27, 25, 22, 150)
        red, green, blue, alpha = parsed
        amount = (alpha / 255) * max(0.0, min(1.0, self._progress))
        self._ink = QColor(red, green, blue)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, self._ink)
        self.setPalette(palette)
        self.setAutoFillBackground(True)
        self._veil.setOpacity(amount)
        self.setGeometry(0, 0, host.width(), host.height())
        span = min(self._width, max(0, host.width()))
        x = host.width() - span * self._progress
        self._panel.setGeometry(int(x), 0, span, host.height())

    def _hide(self) -> None:
        # 打开会停掉正在退出的动画。Qt 的 stop 仍会发出 finished，这里用标志挡住。
        if not self._closing:
            return
        self._escape.setEnabled(False)
        self._panel.hide()
        self.setVisible(False)
        self._closing = False
        self.closed.emit()
