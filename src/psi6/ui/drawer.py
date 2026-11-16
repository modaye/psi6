"""盖住宿主窗口的右侧抽屉。

不进页面布局。从右边滑入，背后是一层遮罩。点遮罩或按 Esc 关闭。
打开时记住焦点，Tab 留在抽屉里，关闭后还回去。
关窗口、取消任务不是这件事。

遮罩用透明度效果，而不是半透明窗口。子控件的透明背景在 Windows 上会铺成一块黑。
面板和遮罩是兄弟，这样淡化遮罩时不会把面板一起淡掉。
"""

from __future__ import annotations

from PySide6.QtCore import Property, QEvent, QObject, Qt, Signal
from PySide6.QtGui import QColor, QKeyEvent, QKeySequence, QPalette, QShortcut
from PySide6.QtWidgets import (
    QApplication,
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


def _can_tab(widget: QWidget) -> bool:
    """看得见、能用、并且接受 Tab 的控件。"""

    if not widget.isVisible() or not widget.isEnabled():
        return False
    return bool(widget.focusPolicy() & Qt.FocusPolicy.TabFocus)


class _FocusTrap(QObject):
    """抽屉打开时，Tab 和 Shift+Tab 只在面板里的可聚焦控件之间循环。"""

    def __init__(self, drawer: Drawer) -> None:
        super().__init__(drawer)
        self._drawer = drawer

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        drawer = self._drawer
        if not drawer.isVisible():
            return False
        if event.type() != QEvent.Type.KeyPress or not isinstance(event, QKeyEvent):
            return False
        if event.key() not in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
            return False
        backward = event.key() == Qt.Key.Key_Backtab or bool(
            event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        )
        drawer.cycle_focus(backward)
        return True


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
        self._return_focus: QWidget | None = None
        self._trap = _FocusTrap(self)
        self._ink = QColor(27, 25, 22)
        self.setVisible(False)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._veil = QGraphicsOpacityEffect(self)
        self._veil.setOpacity(0.0)
        self.setGraphicsEffect(self._veil)
        host.installEventFilter(self)
        host.destroyed.connect(self._on_host_destroyed)

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
        """滑入并盖住宿主。减少动效时直接到位。

        第一次打开时记住当时的焦点。关闭后还回去。
        焦点放进面板内容里第一个可以 Tab 的控件。
        """

        if not self.isVisible():
            self._remember_focus()
        self._closing = False
        self._escape.setEnabled(True)
        self._relayout()
        self.setVisible(True)
        self._panel.setVisible(True)
        self.raise_()
        self._panel.raise_()
        self._install_trap()
        self._focus_entry()
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

    def cycle_focus(self, backward: bool) -> None:
        """在抽屉内把焦点移到下一项或上一项，到头之后绕回。"""

        items = self._focusables()
        if not items:
            self._panel.setFocus(Qt.FocusReason.TabFocusReason)
            return
        current = QApplication.focusWidget()
        if current in items:
            index = items.index(current)
            step = -1 if backward else 1
            target = items[(index + step) % len(items)]
        else:
            target = items[-1] if backward else items[0]
        reason = Qt.FocusReason.BacktabFocusReason if backward else Qt.FocusReason.TabFocusReason
        target.setFocus(reason)

    def _hide(self) -> None:
        # 打开会停掉正在退出的动画。Qt 的 stop 仍会发出 finished，这里用标志挡住。
        if not self._closing:
            return
        self._escape.setEnabled(False)
        self._remove_trap()
        self._panel.hide()
        self.setVisible(False)
        self._closing = False
        target = self._return_focus
        self._return_focus = None
        self._restore_focus(target)
        self.closed.emit()

    def _remember_focus(self) -> None:
        current = QApplication.focusWidget()
        if current is None or current is self or current is self._panel:
            self._return_focus = None
            return
        if self.isAncestorOf(current) or self._panel.isAncestorOf(current):
            return
        self._return_focus = current

    def _focus_entry(self) -> None:
        """内容区优先。没有可聚焦的内容时，落到关闭按钮。"""

        body = self._body.parentWidget()
        if body is not None:
            for widget in body.findChildren(QWidget):
                if _can_tab(widget):
                    widget.setFocus(Qt.FocusReason.TabFocusReason)
                    return
        for widget in self._focusables():
            widget.setFocus(Qt.FocusReason.TabFocusReason)
            return
        self._panel.setFocus(Qt.FocusReason.TabFocusReason)

    def _focusables(self) -> list[QWidget]:
        return [widget for widget in self._panel.findChildren(QWidget) if _can_tab(widget)]

    def _install_trap(self) -> None:
        app = QApplication.instance()
        if app is None:
            return
        app.removeEventFilter(self._trap)
        app.installEventFilter(self._trap)

    def _remove_trap(self) -> None:
        app = QApplication.instance()
        if app is not None:
            app.removeEventFilter(self._trap)

    def _restore_focus(self, target: QWidget | None) -> None:
        if target is None:
            return
        try:
            if target.isVisible() and target.isEnabled():
                target.setFocus()
        except RuntimeError:
            return

    def _on_host_destroyed(self) -> None:
        """宿主正在销毁。不再还焦点，也不把关闭动画跑完。"""

        self._return_focus = None
        self._closing = False
        self._remove_trap()
        motion.stop(self, "progress")
