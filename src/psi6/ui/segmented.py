"""分段开关：确认页二选一 / 三选一，不要退回 QComboBox。"""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QPushButton, QSizePolicy, QWidget


class SegmentedControl(QWidget):
    """N 段互斥。``changed`` 给出 0-based 下标。"""

    changed = Signal(int)

    def __init__(self, labels: Sequence[str], *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        texts = [str(item).strip() for item in labels if str(item).strip()]
        if len(texts) < 2:
            raise ValueError("SegmentedControl 至少需要 2 段文案")
        self.setObjectName("psi6Segmented")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        row = QHBoxLayout(self)
        row.setContentsMargins(4, 4, 4, 4)
        row.setSpacing(0)
        self._buttons: list[QPushButton] = []
        for index, text in enumerate(texts):
            button = QPushButton(text)
            button.setObjectName("psi6Segment")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
            button.setAccessibleName(text)
            self._group.addButton(button, index)
            row.addWidget(button, stretch=1)
            self._buttons.append(button)
        self._buttons[0].setChecked(True)
        self._group.buttonClicked.connect(lambda _button: self.changed.emit(self.index()))

    def count(self) -> int:
        return len(self._buttons)

    def index(self) -> int:
        current = self._group.checkedId()
        return 0 if current < 0 else current

    def set_index(self, index: int) -> None:
        """选中一段。越界忽略。不重复发 ``changed`` 如果未变。"""

        if index < 0 or index >= len(self._buttons):
            return
        if index == self.index():
            self._buttons[index].setChecked(True)
            return
        self._buttons[index].setChecked(True)

    def label(self, index: int | None = None) -> str:
        """当前或指定段的文案。"""

        at = self.index() if index is None else index
        if 0 <= at < len(self._buttons):
            return self._buttons[at].text()
        return ""
