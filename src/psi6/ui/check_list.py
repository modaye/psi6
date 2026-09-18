"""可勾选清单：带走的文件、密钥排除。不要在应用里堆 QListWidget。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


@dataclass(frozen=True)
class CheckItem:
    """一行。``id`` 稳定，标题给人看。"""

    id: str
    title: str
    hint: str = ""
    checked: bool = True


class CheckList(QWidget):
    """多行勾选。``toggled`` 给出 ``(id, checked)``。"""

    toggled = Signal(str, bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("psi6CheckList")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._host = QWidget()
        self._col = QVBoxLayout(self._host)
        self._col.setContentsMargins(0, 0, 0, 0)
        self._col.setSpacing(0)
        self._col.addStretch()
        scroll.setWidget(self._host)
        layout.addWidget(scroll)
        self._boxes: dict[str, QCheckBox] = {}
        self._items: list[CheckItem] = []

    def set_items(self, items: Sequence[CheckItem]) -> None:
        """重建列表。重复 ``id`` 只保留先出现的。"""

        while self._col.count() > 1:
            item = self._col.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.hide()
                widget.deleteLater()
        self._boxes.clear()
        unique: list[CheckItem] = []
        seen: set[str] = set()
        for row in items:
            key = str(row.id).strip()
            if not key or key in seen:
                continue
            seen.add(key)
            unique.append(CheckItem(key, row.title, row.hint, row.checked))
        self._items = unique
        for row in unique:
            self._col.insertWidget(self._col.count() - 1, self._make_row(row))

    def items(self) -> list[CheckItem]:
        """当前行，``checked`` 为界面上的值。"""

        result: list[CheckItem] = []
        for row in self._items:
            box = self._boxes.get(row.id)
            checked = box.isChecked() if box is not None else row.checked
            result.append(CheckItem(row.id, row.title, row.hint, checked))
        return result

    def checked_ids(self) -> list[str]:
        return [row.id for row in self.items() if row.checked]

    def set_checked(self, item_id: str, checked: bool) -> None:
        box = self._boxes.get(item_id)
        if box is not None:
            box.setChecked(checked)

    def _make_row(self, row: CheckItem) -> QWidget:
        host = QWidget()
        host.setObjectName("psi6CheckRow")
        host.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        line = QHBoxLayout(host)
        line.setContentsMargins(8, 8, 8, 8)
        line.setSpacing(10)
        box = QCheckBox()
        box.setChecked(row.checked)
        box.setAccessibleName(row.title)
        box.toggled.connect(lambda on, key=row.id: self.toggled.emit(key, on))
        self._boxes[row.id] = box
        line.addWidget(box, alignment=Qt.AlignmentFlag.AlignTop)
        text = QVBoxLayout()
        text.setContentsMargins(0, 0, 0, 0)
        text.setSpacing(2)
        title = QLabel(row.title)
        title.setObjectName("psi6SettingTitle")
        title.setWordWrap(True)
        text.addWidget(title)
        hint = QLabel(row.hint)
        hint.setObjectName("psi6Hint")
        hint.setWordWrap(True)
        text.addWidget(hint)
        if not row.hint:
            hint.hide()
        line.addLayout(text, stretch=1)
        return host
