"""可挂到任意控件上的事件过滤器。不要为此再包一层业务控件。"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from PySide6.QtCore import Property, QEasingCurve, QEvent, QObject, QPropertyAnimation, Qt
from PySide6.QtWidgets import QWidget

from psi6.theme.runtime import token_ms


class PressScaleFilter(QObject):
    """按下时把宿主缩到 ``pressed``，松开还原。宿主实现 ``set_press_scale``。"""

    def __init__(self, host: QWidget, *, pressed: float = 0.94) -> None:
        super().__init__(host)
        self._host = host
        self._rest = 1.0
        self._down = pressed
        self._scale = 1.0
        self._motion = QPropertyAnimation(self, b"scale", self)
        self._motion.setEasingCurve(QEasingCurve.Type.OutCubic)
        host.installEventFilter(self)

    def _get_scale(self) -> float:
        return self._scale

    def _set_scale(self, value: float) -> None:
        self._scale = float(value)
        setter = getattr(self._host, "set_press_scale", None)
        if callable(setter):
            setter(self._scale)

    scale = Property(float, _get_scale, _set_scale)

    def _go(self, target: float) -> None:
        duration = token_ms("fast")
        self._motion.stop()
        if duration <= 0 or abs(target - self._scale) < 0.002:
            self._set_scale(target)
            return
        self._motion.setDuration(duration)
        self._motion.setStartValue(self._scale)
        self._motion.setEndValue(target)
        self._motion.start()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # type: ignore[override]
        if watched is not self._host:
            return False
        kind = event.type()
        if kind in {QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonDblClick}:
            button = getattr(event, "button", lambda: Qt.MouseButton.NoButton)()
            if button == Qt.MouseButton.LeftButton:
                self._go(self._down)
        elif kind == QEvent.Type.MouseButtonRelease:
            self._go(self._rest)
        elif kind in {QEvent.Type.Leave, QEvent.Type.FocusOut}:
            self._go(self._rest)
        return False


def install_press_scale(widget: QWidget, *, pressed: float = 0.94) -> PressScaleFilter:
    """给已有 ``set_press_scale`` 的控件装上按下缩小。重复调用返回已有过滤器。"""

    for child in widget.findChildren(PressScaleFilter):
        if child.parent() is widget:
            return child
    return PressScaleFilter(widget, pressed=pressed)


class DebugEventFilter(QObject):
    """记录事件名，默认不打印。调试时把 ``sink`` 设成 ``print``。"""

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        ignore: Sequence[QEvent.Type] = (),
        sink: Callable[[str], None] | None = None,
        keep: int = 64,
    ) -> None:
        super().__init__(parent)
        self._ignore = set(ignore)
        self._sink = sink
        self._keep = max(8, keep)
        self.events: list[str] = []

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # type: ignore[override]
        kind = event.type()
        if kind in self._ignore:
            return False
        label = kind.name if hasattr(kind, "name") else str(int(kind))
        name = watched.objectName() or type(watched).__name__
        line = f"{name} {label}"
        self.events.append(line)
        if len(self.events) > self._keep:
            del self.events[0 : len(self.events) - self._keep]
        if self._sink is not None:
            self._sink(line)
        return False
