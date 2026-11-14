"""叠在窗口右上角的短通知。不替代必须看见的对话框。"""

from __future__ import annotations

import contextlib
import time

from PySide6.QtCore import QEvent, QObject, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QAccessible
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from psi6.theme.runtime import token_ms
from psi6.ui._tone import set_tone
from psi6.ui.icon import IconButton
from psi6.ui.tone import Tone

try:  # 该事件在较新的 Qt 绑定里才有；读屏桥缺失时本就是 no-op
    from PySide6.QtGui import QAccessibleAnnouncementEvent
except ImportError:  # pragma: no cover - 取决于绑定版本
    QAccessibleAnnouncementEvent = None  # type: ignore[assignment]

_MAX_TOASTS = 4
_TOAST_WIDTH = 320
_CARD_GAP = 8


def _announce(widget: QWidget, message: str) -> None:
    """把这条通知播报给读屏软件（polite live region）。读屏桥缺失时静默失败。"""

    widget.setAccessibleName(message)
    if QAccessibleAnnouncementEvent is None:
        return
    with contextlib.suppress(Exception):  # 没有读屏桥时不该让通知崩
        QAccessible.updateAccessibility(QAccessibleAnnouncementEvent(widget, message))


def _ease_out_cubic(t: float) -> float:
    return 1.0 - (1.0 - t) ** 3


class ToastCard(QWidget):
    """单条 Toast。超时或点关闭后收起销毁。

    高度按换行后的正文计算并缓存到 ``_natural_h``。进出场动画通过让
    ``heightForWidth`` 返回随时间变化的 ``_current_h`` 并调用 ``updateGeometry``
    驱动：这样布局会按动画高度重新排布卡片，而不是被固定的几何尺寸顶住（在
    ``QVBoxLayout`` 里直接 ``setFixedHeight`` 会被布局覆盖，无法产生动画）。
    """

    closed = Signal()
    resized = Signal()

    def __init__(
        self,
        message: str,
        *,
        tone: Tone | str = "info",
        timeout_ms: int = 6000,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("psi6Toast")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        # 悬停暂停要收到 enter/leave，不设 WA_Hover 时子控件会吞掉鼠标移动。
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)
        set_tone(self, tone)

        self._dead = False
        self._gone = False
        self._current_h = 0
        self._anim_timer: QTimer | None = None
        self._anim_from = 0
        self._anim_to = 0
        self._anim_start = 0.0
        self._anim_duration = 0

        row = QHBoxLayout(self)
        row.setContentsMargins(12, 10, 8, 10)
        row.setSpacing(8)
        self._label = QLabel(message)
        self._label.setWordWrap(True)
        self._label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        row.addWidget(self._label, stretch=1)
        self._close = IconButton("x", label="关闭", size=14, extent=28)
        self._close.clicked.connect(self.dismiss)
        row.addWidget(self._close, alignment=Qt.AlignmentFlag.AlignTop)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.dismiss)
        # 悬停暂停用的剩余时长。用户把鼠标停在卡片上时停表，移开再按剩余时间接着走，
        # 而不是重新计满：长句子的通知不会因为看了一眼就再来一遍整个周期。
        self._timeout_ms = max(0, int(timeout_ms))
        self._remaining_ms = self._timeout_ms
        if self._timeout_ms > 0:
            self._timer.start(self._timeout_ms)
        # 高度按固定宽度算一次并缓存：析构期 sizeHint/heightForWidth 仍会被 Qt 调用，
        # 那时子控件（_label）可能已释放，访问它会触发 C 层段错误。缓存后热路径不再触碰子控件。
        self._natural_h = self._compute_natural_height(_TOAST_WIDTH)

    def _compute_natural_height(self, width: int) -> int:
        layout = self.layout()
        margins = layout.contentsMargins() if layout is not None else self.contentsMargins()
        close_w = self._close.width() or 28
        inner = max(64, width - margins.left() - margins.right() - close_w - 8)
        text_h = max(self._label.fontMetrics().height(), self._label.heightForWidth(inner))
        return margins.top() + margins.bottom() + max(text_h, self._close.height() or 28)

    def reveal(self) -> None:
        """从 0 高度展开显示。``reduced_motion`` 时直接显示，不做动画。"""

        if self._dead:
            return
        self._stop_anim()
        duration = token_ms("motion")
        if duration <= 0:
            self._current_h = self._natural_h
            self.updateGeometry()
            self.resized.emit()
            return
        self._start_anim(0, self._natural_h, duration)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._current_h

    def sizeHint(self) -> QSize:
        return QSize(_TOAST_WIDTH, self._natural_h)

    def minimumSizeHint(self) -> QSize:
        # 最小值必须随动画高度收缩，否则布局永远按 _natural_h 排，collapse 不生效。
        return QSize(_TOAST_WIDTH, self._current_h)

    def dismiss(self) -> None:
        """收起后销毁。"""

        if self._dead:
            return
        self._dead = True
        self._timer.stop()
        self._stop_anim()
        duration = token_ms("fast")
        if duration <= 0:
            self._delete()
            return
        self._start_anim(self._current_h, 0, duration)

    def enterEvent(self, event) -> None:  # type: ignore[override]
        """鼠标进入：停表并记住剩余时长。"""

        self._pause_timeout()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        """鼠标离开：按剩余时长接着计时，不重新计满。"""

        self._resume_timeout()
        super().leaveEvent(event)

    def _pause_timeout(self) -> None:
        """停表并记下还剩多少毫秒。已经结束或被销毁时不动。"""

        if self._dead or not self._timer.isActive():
            return
        self._remaining_ms = max(0, self._timer.remainingTime())
        self._timer.stop()

    def _resume_timeout(self) -> None:
        """按剩余时长继续计时。从未启动过（``timeout_ms <= 0``）时保持不动。"""

        if self._dead or self._timeout_ms <= 0 or self._timer.isActive():
            return
        self._timer.start(max(0, self._remaining_ms))

    def _start_anim(self, start: int, end: int, duration: int) -> None:
        self._anim_from = start
        self._anim_to = end
        self._anim_duration = duration
        self._anim_start = time.monotonic()
        self._current_h = start
        if self._anim_timer is None:
            self._anim_timer = QTimer(self)
            self._anim_timer.setInterval(16)
            self._anim_timer.timeout.connect(self._tick)
        self.updateGeometry()
        self.resized.emit()
        self._anim_timer.start()

    def _stop_anim(self) -> None:
        if self._anim_timer is not None and self._anim_timer.isActive():
            self._anim_timer.stop()

    def _tick(self) -> None:
        # _anim_duration 是毫秒（来自 token_ms），monotonic 是秒，必须换算。
        elapsed_ms = (time.monotonic() - self._anim_start) * 1000.0
        t = min(1.0, elapsed_ms / self._anim_duration) if self._anim_duration > 0 else 1.0
        eased = _ease_out_cubic(t)
        self._current_h = round(self._anim_from + (self._anim_to - self._anim_from) * eased)
        self.updateGeometry()
        self.resized.emit()
        if t >= 1.0:
            self._stop_anim()
            if self._anim_to == 0:
                self._delete()

    def _delete(self) -> None:
        if self._gone:
            return
        self._gone = True
        self._stop_anim()
        self.closed.emit()
        self.hide()
        self.deleteLater()


class ToastHost(QWidget):
    """窗口级 Toast 栈。只占右下角，按内容长高，互不挤压。"""

    def __init__(self, window: QWidget, parent: QWidget | None = None) -> None:
        super().__init__(parent or window)
        self.setObjectName("psi6ToastHost")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._window = window
        self._cards: list[ToastCard] = []
        self._column = QVBoxLayout(self)
        self._column.setContentsMargins(0, 0, 0, 0)
        self._column.setSpacing(_CARD_GAP)
        # 右下角堆叠：最新的在最下面，旧的往上顶。
        self._column.setAlignment(Qt.AlignmentFlag.AlignBottom)
        window.installEventFilter(self)
        self.setFixedWidth(_TOAST_WIDTH)
        self.hide()
        self._place()

    def push(
        self, message: str, *, tone: Tone | str = "info", timeout_ms: int = 6000
    ) -> ToastCard | None:
        """追加一条。空文本忽略。超过上限时丢掉最旧的。"""

        text = message.strip()
        if not text:
            return None
        while len(self._cards) >= _MAX_TOASTS:
            oldest = self._cards.pop(0)
            oldest.dismiss()
        card = ToastCard(text, tone=tone, timeout_ms=timeout_ms)
        card.hide()
        card.closed.connect(lambda item=card: self._forget(item))
        card.resized.connect(self._place)
        self._column.addWidget(card, alignment=Qt.AlignmentFlag.AlignBottom)
        self._cards.append(card)
        self.show()
        self._place()
        card.show()
        card.reveal()
        _announce(card, text)
        return card

    def clear(self) -> None:
        """清掉当前全部 Toast。"""

        for card in list(self._cards):
            card.dismiss()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self._window and event.type() in {QEvent.Type.Resize, QEvent.Type.Show}:
            self._place()
        return super().eventFilter(watched, event)

    def _forget(self, card: ToastCard) -> None:
        if card in self._cards:
            self._cards.remove(card)
        self._column.removeWidget(card)
        if not self._cards:
            self.hide()
        else:
            self._place()

    def _content_height(self) -> int:
        if not self._cards:
            return 0
        total = _CARD_GAP * (len(self._cards) - 1)
        for card in self._cards:
            total += card.heightForWidth(_TOAST_WIDTH)
        return total

    def _place(self) -> None:
        """贴在窗口右下角。堆栈向上长高，不盖住底栏和状态栏。"""

        host = self._window
        margin = 16
        needed = self._content_height()
        self.setFixedSize(_TOAST_WIDTH, max(0, needed))
        x = max(margin, host.width() - _TOAST_WIDTH - margin)
        # 底边让开状态栏：状态栏里可能放着 StatusProgress，通知不该压在进度上。
        status = getattr(host, "statusBar", None)
        status_h = 0
        if callable(status):
            bar = status()
            if bar is not None and bar.isVisible():
                status_h = bar.height()
        y = max(margin, host.height() - needed - margin - status_h)
        self.move(x, y)
        self.raise_()
