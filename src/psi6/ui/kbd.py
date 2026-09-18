"""键盘快捷键提示块，例如 ``Ctrl+K``。"""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QWidget


class KbdHint(QLabel):
    """等宽小标签，用来标快捷键，不是可点按钮。"""

    def __init__(self, keys: str, parent: QWidget | None = None) -> None:
        super().__init__(keys, parent)
        self.setObjectName("psi6Kbd")
