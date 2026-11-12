"""分步向导指示条。内容页由业务自己切。"""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from psi6.theme.runtime import token_color
from psi6.ui.icon import Icon


class Stepper(QWidget):
    """水平步骤：当前步高亮，已完成显示勾。

    点击某一步发出 ``clicked``，不自己改当前步。页面决定能不能跳。
    """

    current_changed = Signal(int)
    clicked = Signal(int)

    def __init__(
        self,
        steps: Sequence[str | tuple[str, str]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("psi6Stepper")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        pairs = [_step_pair(step) for step in steps]
        self._labels = tuple(title for title, _caption in pairs)
        self._index = 0
        self._row = QHBoxLayout(self)
        self._row.setContentsMargins(12, 10, 12, 10)
        self._row.setSpacing(8)
        self._nodes: list[_StepNode] = []
        for index, (title, caption) in enumerate(pairs):
            if index:
                rule = QFrame()
                rule.setObjectName("psi6Rule")
                rule.setFrameShape(QFrame.Shape.HLine)
                self._row.addWidget(rule, stretch=1)
            node = _StepNode(index + 1, title, caption)
            node.clicked.connect(lambda i=index: self.clicked.emit(i))
            self._nodes.append(node)
            self._row.addWidget(node, stretch=2)
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


def _step_pair(step: str | tuple[str, str]) -> tuple[str, str]:
    if isinstance(step, tuple):
        return step[0], step[1]
    return str(step), ""


class _StepNode(QWidget):
    clicked = Signal()

    def __init__(
        self,
        number: int,
        title: str,
        caption: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("psi6StepNode")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._number = number
        row = QHBoxLayout(self)
        row.setContentsMargins(4, 2, 8, 2)
        row.setSpacing(6)
        self._mark = QLabel(f"{number:02d}")
        self._mark.setObjectName("psi6StepMark")
        self._mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._mark.setFixedSize(26, 26)
        self._check = Icon("check", size=14, parent=self._mark)
        self._check.move(6, 6)
        self._check.hide()
        text = QVBoxLayout()
        text.setContentsMargins(0, 0, 0, 0)
        text.setSpacing(0)
        row.addWidget(self._mark)
        self._title = QLabel(title)
        self._title.setObjectName("psi6StepTitle")
        text.addWidget(self._title)
        self._caption = QLabel(caption)
        self._caption.setObjectName("psi6Hint")
        text.addWidget(self._caption)
        if not caption:
            self._caption.hide()
        row.addLayout(text)

    def mouseReleaseEvent(self, event) -> None:
        inside = self.rect().contains(event.position().toPoint())
        if event.button() == Qt.MouseButton.LeftButton and inside:
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    def set_state(self, state: str) -> None:
        self.setProperty("state", state)
        done = state == "done"
        self._mark.show()
        self._check.setProperty("psi6IconColor", token_color("color_on_primary"))
        self._check.update()
        self._check.setVisible(done)
        style = self.style()
        style.unpolish(self)
        style.polish(self)
        self._mark.style().unpolish(self._mark)
        self._mark.style().polish(self._mark)
        self._title.style().unpolish(self._title)
        self._title.style().polish(self._title)
