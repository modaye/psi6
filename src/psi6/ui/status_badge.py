"""状态徽标：成功/警告/错误计数或行状态。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QSizePolicy, QWidget

from psi6.ui._tone import set_tone
from psi6.ui.tone import Tone


class StatusBadge(QLabel):
    """一行里的短状态。不要用它替代对话框或日志。"""

    def __init__(
        self,
        text: str = "",
        *,
        tone: Tone = "neutral",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)
        self.setObjectName("psi6Badge")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        set_tone(self, tone)

    def set_status(self, text: str, *, tone: Tone | str = "neutral") -> None:
        """同时改文字和语气。"""

        self.setText(text)
        set_tone(self, tone)
