"""工具箱磁贴、Git 变更行 / 变更列表。"""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from psi6.ui.icon import Icon
from psi6.ui.status_badge import StatusBadge


class ToolTile(QWidget):
    """工具箱一格：图标、名称、一句说明。"""

    clicked = Signal()

    def __init__(
        self,
        title: str,
        hint: str,
        *,
        icon: str = "wrench",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("psi6ToolTile")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.setMinimumSize(220, 96)
        self.setMaximumHeight(124)
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(8)
        root.addWidget(Icon(icon, size=22, tone="info"))
        name = QLabel(title)
        name.setObjectName("psi6PageTitle")
        root.addWidget(name)
        desc = QLabel(hint)
        desc.setObjectName("psi6Hint")
        desc.setWordWrap(True)
        root.addWidget(desc)

    def mouseReleaseEvent(self, event) -> None:  # noqa: ANN001
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:  # noqa: ANN001
        if event.key() in {Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space}:
            self.clicked.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class ChangeRow(QWidget):
    """Git 风格的文件变更：状态徽标 + 路径。可点选。"""

    clicked = Signal(str)

    def __init__(
        self,
        path: str,
        *,
        kind: str = "modified",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("psi6ChangeRow")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self._path = path
        self._kind = kind
        self._selected = False
        row = QHBoxLayout(self)
        row.setContentsMargins(10, 8, 10, 8)
        row.setSpacing(10)
        tone, label, icon = _kind_meta(kind)
        row.addWidget(Icon(icon, tone=tone))
        self._badge = StatusBadge(label, tone=tone)
        row.addWidget(self._badge)
        name = QLabel(path)
        name.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        row.addWidget(name, stretch=1)

    def path(self) -> str:
        return self._path

    def kind(self) -> str:
        return self._kind

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self.setProperty("selected", selected)
        style = self.style()
        style.unpolish(self)
        style.polish(self)

    def is_selected(self) -> bool:
        return self._selected

    def mouseReleaseEvent(self, event) -> None:  # noqa: ANN001
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._path)
        super().mouseReleaseEvent(event)


class ChangeList(QWidget):
    """一组变更行，单选。``current_changed`` 给出路径。"""

    current_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("psi6ChangeList")
        self._column = QVBoxLayout(self)
        self._column.setContentsMargins(0, 0, 0, 0)
        self._column.setSpacing(6)
        self._rows: list[ChangeRow] = []
        self._current = ""
        self._column.addStretch()

    def set_changes(self, items: Sequence[tuple[str, str]]) -> None:
        while self._rows:
            row = self._rows.pop()
            self._column.removeWidget(row)
            row.hide()
            row.deleteLater()
        self._current = ""
        for path, kind in items:
            self.add_change(path, kind=kind)

    def add_change(self, path: str, *, kind: str = "modified") -> ChangeRow:
        row = ChangeRow(path, kind=kind)
        row.clicked.connect(self.set_current)
        self._rows.append(row)
        self._column.insertWidget(self._column.count() - 1, row)
        return row

    def set_current(self, path: str) -> None:
        self._current = path
        for row in self._rows:
            row.set_selected(row.path() == path)
        self.current_changed.emit(path)

    def current_path(self) -> str:
        return self._current


def _kind_meta(kind: str) -> tuple[str, str, str]:
    mapping = {
        "added": ("success", "新增", "file-plus"),
        "deleted": ("error", "删除", "trash"),
        "modified": ("warning", "修改", "file"),
        "renamed": ("info", "重命名", "copy"),
        "untracked": ("neutral", "未跟踪", "file"),
    }
    return mapping.get(kind, mapping["modified"])
