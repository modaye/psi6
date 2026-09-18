"""统一 diff 视图：只负责着色展示，不做 git 解析。"""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget


class DiffView(QScrollArea):
    """每行 ``(标记, 文本)``。标记为 ``+`` / ``-`` / 空格。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("psi6DiffView")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.Shape.NoFrame)
        self._host = QWidget()
        self._host.setObjectName("psi6DiffHost")
        self._host.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._column = QVBoxLayout(self._host)
        self._column.setContentsMargins(8, 8, 8, 8)
        self._column.setSpacing(0)
        self._column.addStretch()
        self.setWidget(self._host)

    def set_lines(self, lines: Sequence[tuple[str, str]]) -> None:
        self.clear()
        for marker, text in lines:
            row = QLabel(f"{marker} {text}" if marker.strip() else f"  {text}")
            row.setObjectName(_row_name(marker))
            row.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self._column.insertWidget(self._column.count() - 1, row)

    def clear(self) -> None:
        while self._column.count() > 1:
            item = self._column.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.deleteLater()


def _row_name(marker: str) -> str:
    if marker == "+":
        return "psi6DiffAdd"
    if marker == "-":
        return "psi6DiffDel"
    return "psi6DiffCtx"
