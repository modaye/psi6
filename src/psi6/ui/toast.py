"""叠在窗口右上角的短通知。不替代必须看见的对话框。"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QSize, Qt, QTimer, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from psi6.ui._tone import set_tone
from psi6.ui.icon import IconButton
from psi6.ui.tone import Tone

_MAX_TOASTS = 4
_TOAST_WIDTH = 320
_CARD_GAP = 8


class ToastCard(QWidget):
    """单条 Toast。超时或点关闭后销毁。高度按换行后的正文计算，不允许被压扁。"""

    closed = Signal()

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
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)
        set_tone(self, tone)
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
        if timeout_ms > 0:
            self._timer.start(timeout_ms)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        margins = self.layout().contentsMargins()
        inner = max(64, width - margins.left() - margins.right() - self._close.width() - 8)
        text_h = max(self._label.fontMetrics().height(), self._label.heightForWidth(inner))
        return margins.top() + margins.bottom() + max(text_h, self._close.height())

    def sizeHint(self) -> QSize:
        return QSize(_TOAST_WIDTH, self.heightForWidth(_TOAST_WIDTH))

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def dismiss(self) -> None:
        """立刻关掉这条通知。"""

        self._timer.stop()
        self.closed.emit()
        self.hide()
        self.deleteLater()


class ToastHost(QWidget):
    """窗口级 Toast 栈。只占右上角，按内容长高，互不挤压。"""

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
        self._column.setAlignment(Qt.AlignmentFlag.AlignTop)
        window.installEventFilter(self)
        self.hide()
        self._place()

    def push(self, message: str, *, tone: Tone | str = "info", timeout_ms: int = 6000) -> ToastCard | None:
        """追加一条。空文本忽略。超过上限时丢掉最旧的。"""

        text = message.strip()
        if not text:
            return None
        while len(self._cards) >= _MAX_TOASTS:
            oldest = self._cards[0]
            oldest.dismiss()
        card = ToastCard(text, tone=tone, timeout_ms=timeout_ms)
        card.hide()
        card.closed.connect(lambda item=card: self._forget(item))
        card.setFixedWidth(_TOAST_WIDTH)
        card.setMinimumHeight(card.heightForWidth(_TOAST_WIDTH))
        self._column.addWidget(card, alignment=Qt.AlignmentFlag.AlignTop)
        self._cards.append(card)
        self.show()
        self._place()
        card.show()
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
        host = self._window
        margin = 16
        y = margin
        title = getattr(host, "title_bar", None)
        if title is not None and title.isVisible():
            y = title.height() + margin
        needed = self._content_height()
        self.setFixedSize(_TOAST_WIDTH, max(0, needed))
        x = max(margin, host.width() - _TOAST_WIDTH - margin)
        self.move(x, y)
        self.raise_()
