"""分步向导指示条。内容页由业务自己切。"""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from psi6.ui.icon import Icon


class Stepper(QWidget):
    """水平步骤：当前步高亮，已完成显示勾。"""

    current_changed = Signal(int)

    def __init__(self, steps: Sequence[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("psi6Stepper")
        self._labels = tuple(steps)
        self._index = 0
        self._row = QHBoxLayout(self)
        self._row.setContentsMargins(0, 0, 0, 0)
        self._row.setSpacing(4)
        self._nodes: list[_StepNode] = []
        for index, title in enumerate(self._labels):
            if index:
                rule = QLabel("—")
                rule.setObjectName("psi6Hint")
                self._row.addWidget(rule)
            node = _StepNode(index + 1, title)
            self._nodes.append(node)
            self._row.addWidget(node)
        self._row.addStretch()
        self._sync()

    def set_current(self, index: int) -> None:
        bounded = max(0, min(index, len(self._labels) - 1)) if self._labels else 0
        if bounded == self._index:
            self._sync()
            return
        self._index = bounded
        self._sync()
        self.current_changed.emit(self._index)

    def current_index(self) -> int:
        return self._index

    def next(self) -> None:
        self.set_current(self._index + 1)

    def back(self) -> None:
        self.set_current(self._index - 1)

    def _sync(self) -> None:
        for index, node in enumerate(self._nodes):
            if index < self._index:
                node.set_state("done")
            elif index == self._index:
                node.set_state("current")
            else:
                node.set_state("todo")


class _StepNode(QWidget):
    def __init__(self, number: int, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("psi6StepNode")
        self._number = number
        row = QHBoxLayout(self)
        row.setContentsMargins(4, 2, 8, 2)
        row.setSpacing(6)
        self._mark = QLabel(str(number))
        self._mark.setObjectName("psi6StepMark")
        self._mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._mark.setFixedSize(20, 20)
        self._check = Icon("success", size=14, tone="success")
        row.addWidget(self._mark)
        row.addWidget(self._check)
        self._check.hide()
        self._title = QLabel(title)
        row.addWidget(self._title)

    def set_state(self, state: str) -> None:
        self.setProperty("state", state)
        done = state == "done"
        if done:
            self._mark.hide()
            self._check.show()
        else:
            self._check.hide()
            self._mark.show()
        self._title.setObjectName("psi6PageTitle" if state == "current" else "psi6Hint")
        style = self.style()
        style.unpolish(self)
        style.polish(self)
        self._title.style().unpolish(self._title)
        self._title.style().polish(self._title)
