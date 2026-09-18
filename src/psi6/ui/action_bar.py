"""工具行：左侧状态、右侧操作，避免每页手写 QHBoxLayout。"""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QWidget


class ActionBar(QWidget):
    """一条工具栏。左侧放状态/筛选，右侧放按钮。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("psi6ActionBar")
        self._row = QHBoxLayout(self)
        self._row.setContentsMargins(0, 0, 0, 0)
        self._row.setSpacing(8)
        self._right_at = 0
        self._row.addStretch()

    def add_left(self, widget: QWidget) -> None:
        """加到伸展项左侧。"""

        self._row.insertWidget(self._right_at, widget)
        self._right_at += 1

    def add_right(self, widget: QWidget) -> None:
        """加到伸展项右侧。"""

        self._row.addWidget(widget)
