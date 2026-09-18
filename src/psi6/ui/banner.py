"""页内横幅：任务结果、空目录、可恢复错误。可带 1～2 个动作。"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from psi6.icons.glyphs import TONE_ICONS
from psi6.ui._tone import set_tone
from psi6.ui.buttons import ghost_button
from psi6.ui.icon import Icon, IconButton
from psi6.ui.tone import Tone

BannerAction = tuple[str, Callable[[], None]]


class Banner(QWidget):
    """贴在表单和结果之间的短通知。关闭后隐藏，不进日志。"""

    dismissed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("psi6Banner")
        self._row = QHBoxLayout(self)
        self._row.setContentsMargins(10, 6, 10, 6)
        self._row.setSpacing(8)
        self._icon = Icon("info", tone="info")
        self._row.addWidget(self._icon)
        self._label = QLabel()
        self._label.setWordWrap(True)
        self._row.addWidget(self._label, stretch=1)
        self._actions: list[QWidget] = []
        close = IconButton("x", label="关闭横幅")
        close.clicked.connect(self.clear)
        self._row.addWidget(close)
        self.hide()

    def set_notice(
        self,
        text: str,
        *,
        tone: Tone | str = "info",
        actions: Sequence[BannerAction] | None = None,
    ) -> None:
        """显示一条人话。``actions`` 最多两个按钮，例如「查看文件」「排除」。"""

        message = text.strip()
        if not message:
            self.clear()
            return
        self._label.setText(message)
        set_tone(self, tone)
        icon_name = TONE_ICONS.get(str(tone), "info")
        self._icon.set_name(icon_name)
        self._icon.set_tone(tone if tone != "neutral" else "info")
        self._rebuild_actions(actions or ())
        self.show()

    def clear(self) -> None:
        """隐藏横幅。"""

        self._label.clear()
        self._rebuild_actions(())
        self.hide()
        self.dismissed.emit()

    def _rebuild_actions(self, actions: Sequence[BannerAction]) -> None:
        for widget in self._actions:
            widget.hide()
            widget.deleteLater()
        self._actions.clear()
        close_at = self._row.count() - 1
        for label, slot in list(actions)[:2]:
            text = str(label).strip()
            if not text:
                continue
            button = ghost_button(text)
            button.setAccessibleName(text)
            button.clicked.connect(slot)
            self._row.insertWidget(close_at, button)
            self._actions.append(button)
            close_at += 1
