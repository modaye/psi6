"""开关：设置项用它，表单里的是/否过滤仍可用 QCheckBox。"""

from __future__ import annotations

from PySide6.QtCore import Property, QEasingCurve, QEvent, QPropertyAnimation, QRectF, Qt
from PySide6.QtGui import QPaintEvent
from PySide6.QtWidgets import QAbstractButton, QSizePolicy, QWidget

from psi6.theme.paint import as_color, create_painter, mix_color, scale_around_center
from psi6.theme.runtime import token_color, token_int, token_ms
from psi6.ui.filters import install_press_scale


class Switch(QAbstractButton):
    """胶囊轨道 + 滑块。颜色、尺寸和时长走当前主题 token。"""

    def __init__(self, *, checked: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("psi6Switch")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.setAccessibleName("开关")
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._progress = 1.0 if checked else 0.0
        self._press_scale = 1.0
        self._motion = QPropertyAnimation(self, b"progress", self)
        self._motion.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._sync_metrics()
        self.blockSignals(True)
        self.setChecked(checked)
        self.blockSignals(False)
        self.toggled.connect(self._move_thumb)
        install_press_scale(self)

    def _get_progress(self) -> float:
        return self._progress

    def _set_progress(self, value: float) -> None:
        self._progress = max(0.0, min(1.0, float(value)))
        self.update()

    progress = Property(float, _get_progress, _set_progress)

    def set_press_scale(self, value: float) -> None:
        """按下缩小。由 ``PressScaleFilter`` 调用。"""

        self._press_scale = max(0.8, min(1.0, float(value)))
        self.update()

    def _sync_metrics(self) -> None:
        width = max(28, token_int("switch_width", 44))
        height = max(16, token_int("switch_height", 24))
        self.setFixedSize(width, height)

    def _move_thumb(self, checked: bool) -> None:
        """``toggled`` 之后滑动圆钮。时长 0 则立刻到位。"""

        self._motion.stop()
        target = 1.0 if checked else 0.0
        duration = token_ms("fast")
        if duration <= 0 or abs(target - self._progress) < 0.01:
            self._progress = target
            self.update()
            return
        self._motion.setDuration(duration)
        self._motion.setStartValue(self._progress)
        self._motion.setEndValue(target)
        self._motion.start()

    def changeEvent(self, event: QEvent) -> None:  # type: ignore[override]
        super().changeEvent(event)
        if event.type() in {QEvent.Type.PaletteChange, QEvent.Type.StyleChange}:
            self._sync_metrics()
            self.update()

    def paintEvent(self, event: QPaintEvent) -> None:  # type: ignore[override]
        del event
        with create_painter(self) as painter:
            scale_around_center(painter, QRectF(self.rect()), self._press_scale)
            enabled = self.isEnabled()
            amount = self._progress
            off = token_color("hover" if enabled else "disabled")
            on = token_color("primary" if enabled else "disabled")
            painter.setBrush(mix_color(off, on, amount))
            margin = max(1.0, self.height() * 0.08)
            groove = QRectF(margin, self.height() * 0.14, self.width() - margin * 2, self.height() * 0.72)
            radius = groove.height() / 2
            painter.drawRoundedRect(groove, radius, radius)
            if self.hasFocus() and enabled:
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.setPen(as_color(token_color("focus")))
                painter.drawRoundedRect(groove.adjusted(-1, -1, 1, 1), radius + 1, radius + 1)
            thumb = max(8.0, groove.height() - 4)
            pad = 2.0
            x = groove.x() + pad + amount * (groove.width() - thumb - pad * 2)
            y = groove.y() + (groove.height() - thumb) / 2
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(as_color(token_color("on_primary" if enabled else "sunken")))
            painter.drawEllipse(QRectF(x, y, thumb, thumb))
