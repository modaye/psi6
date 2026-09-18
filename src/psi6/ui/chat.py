"""Agent 对话：气泡列表 + 输入条。不做流式协议，只提供桌面结构。"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from psi6.theme.runtime import token_int
from psi6.ui.buttons import primary_button
from psi6.ui.empty_state import EmptyState
from psi6.ui.icon import Icon, apply_button_icon
from psi6.ui._tone import set_tone


class MessageBubble(QWidget):
    """一条消息。``role`` 为 ``user`` 或 ``assistant``。"""

    def __init__(
        self,
        text: str,
        *,
        role: str = "assistant",
        timestamp: str = "",
        streaming: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("psi6Bubble")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        set_tone(self, "info" if role == "assistant" else "neutral")
        self.setProperty("role", role)
        self.setProperty("streaming", streaming)
        style = self.style()
        style.unpolish(self)
        style.polish(self)
        self.setMaximumWidth(560)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        icon_name = "bot" if role == "assistant" else "message"
        layout.addWidget(Icon(icon_name), alignment=Qt.AlignmentFlag.AlignTop)
        body_col = QVBoxLayout()
        body_col.setContentsMargins(0, 0, 0, 0)
        body_col.setSpacing(2)
        self._body = QLabel(text)
        self._body.setWordWrap(True)
        self._body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        body_col.addWidget(self._body)
        meta = QHBoxLayout()
        meta.setContentsMargins(0, 0, 0, 0)
        self._time = QLabel(timestamp)
        self._time.setObjectName("psi6Hint")
        meta.addWidget(self._time)
        if not timestamp:
            self._time.hide()
        self._stream = QLabel("正在生成…")
        self._stream.setObjectName("psi6Hint")
        meta.addWidget(self._stream)
        if not streaming:
            self._stream.hide()
        meta.addStretch()
        body_col.addLayout(meta)
        layout.addLayout(body_col, stretch=1)

    def set_text(self, text: str) -> None:
        self._body.setText(text)

    def set_streaming(self, streaming: bool) -> None:
        if streaming:
            self._stream.show()
        else:
            self._stream.hide()
        self.setProperty("streaming", streaming)
        style = self.style()
        style.unpolish(self)
        style.polish(self)

    def set_timestamp(self, timestamp: str) -> None:
        self._time.setText(timestamp)
        if timestamp:
            self._time.show()
        else:
            self._time.hide()


class MessageList(QWidget):
    """自上而下的对话记录。空列表显示占位。

    新气泡先隐藏，``insertWidget`` 挂上父对象并排好位置后再显示，避免在容器顶部闪一帧。
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("psi6MessageList")
        self._count = 0
        self._rows: list[QWidget] = []
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        self._stack = QStackedWidget()
        root.addWidget(self._stack)

        self._empty = EmptyState("还没有消息", "在下方输入，Enter 发送。", icon="message", tone="info")
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self._host = QWidget()
        self._column = QVBoxLayout(self._host)
        self._column.setContentsMargins(0, 0, 0, 0)
        self._column.setSpacing(8)
        self._column.addStretch()
        self._scroll.setWidget(self._host)
        self._stack.addWidget(self._empty)
        self._stack.addWidget(self._scroll)

    def add_message(
        self,
        text: str,
        *,
        role: str = "assistant",
        timestamp: str = "",
        streaming: bool = False,
    ) -> MessageBubble:
        wrap = QWidget()
        wrap.hide()
        wrap.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        row = QHBoxLayout(wrap)
        row.setContentsMargins(0, 0, 0, 0)
        bubble = MessageBubble(text, role=role, timestamp=timestamp, streaming=streaming)
        if role == "user":
            row.addStretch()
            row.addWidget(bubble)
        else:
            row.addWidget(bubble)
            row.addStretch()
        self._column.insertWidget(self._column.count() - 1, wrap)
        self._column.activate()
        self._host.adjustSize()
        wrap.show()
        self._rows.append(wrap)
        self._count += 1
        self._stack.setCurrentWidget(self._scroll)
        self._scroll_to_end()
        return bubble

    def clear(self) -> None:
        for wrap in self._rows:
            self._column.removeWidget(wrap)
            wrap.hide()
            wrap.deleteLater()
        self._rows.clear()
        self._count = 0
        self._stack.setCurrentWidget(self._empty)

    def is_empty(self) -> bool:
        return self._count == 0

    def _scroll_to_end(self) -> None:
        bar = self._scroll.verticalScrollBar()
        bar.setValue(bar.maximum())
        QTimer.singleShot(0, self, self._apply_scroll_end)

    def _apply_scroll_end(self) -> None:
        bar = self._scroll.verticalScrollBar()
        bar.setValue(bar.maximum())


class Composer(QWidget):
    """输入 + 发送。Enter 发送，Shift+Enter 换行。"""

    sent = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("psi6Composer")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        row = QHBoxLayout(self)
        row.setContentsMargins(8, 8, 8, 8)
        row.setSpacing(8)
        self._edit = _ComposerEdit()
        self._edit.setPlaceholderText("输入消息，Enter 发送")
        self._edit.setFixedHeight(72)
        self._edit.submit.connect(self._submit)
        row.addWidget(self._edit, stretch=1)
        send = primary_button("发送")
        apply_button_icon(send, "send")
        send.setFixedHeight(max(32, token_int("control_height", 32)))
        send.clicked.connect(self._submit)
        row.addWidget(send, alignment=Qt.AlignmentFlag.AlignBottom)
        self._send = send

    def set_placeholder(self, text: str) -> None:
        self._edit.setPlaceholderText(text)

    def set_enabled(self, enabled: bool) -> None:
        self._edit.setEnabled(enabled)
        self._send.setEnabled(enabled)

    def _submit(self) -> None:
        text = self._edit.toPlainText().strip()
        if not text:
            return
        self._edit.clear()
        self.sent.emit(text)


class _ComposerEdit(QTextEdit):
    submit = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in {Qt.Key.Key_Return, Qt.Key.Key_Enter} and not (
            event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        ):
            self.submit.emit()
            event.accept()
            return
        super().keyPressEvent(event)
