"""只读数据表：列定义 + 行记录。用 ``QTableView`` 模型，避免为每一格创建 Item。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QStackedWidget,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from psi6.ui.busy import BusyOverlay
from psi6.ui.empty_state import EmptyState


@dataclass(frozen=True)
class TableColumn:
    """一列表头。"""

    key: str
    title: str | None = None
    stretch: bool = False

    @property
    def header(self) -> str:
        return self.title or self.key


def _as_mapping(row: Mapping[str, Any] | BaseModel) -> dict[str, Any]:
    if isinstance(row, BaseModel):
        return row.model_dump()
    return dict(row)


class _RowTableModel(QAbstractTableModel):
    """把行字典交给视图按需取文本。可见行才参与绘制。"""

    def __init__(self, host: DataTable) -> None:
        super().__init__(host)
        self._host = host

    def rowCount(self, parent: QModelIndex | None = None) -> int:
        if parent is not None and parent.isValid():
            return 0
        return len(self._host._visible)

    def columnCount(self, parent: QModelIndex | None = None) -> int:
        if parent is not None and parent.isValid():
            return 0
        return len(self._host._columns)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None
        rows = self._host._visible
        columns = self._host._columns
        if index.row() >= len(rows) or index.column() >= len(columns):
            return None
        column = columns[index.column()]
        value = rows[index.row()].get(column.key)
        text = self._host.display_text(column.key, value)
        if role in {Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.ToolTipRole}:
            return text
        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if orientation != Qt.Orientation.Horizontal or role != Qt.ItemDataRole.DisplayRole:
            return None
        if 0 <= section < len(self._host._columns):
            return self._host._columns[section].header
        return None

    def reload(self) -> None:
        self.beginResetModel()
        self.endResetModel()


class DataTable(QWidget):
    """行记录表格。适合预览结果、任务清单，不负责单元格编辑。"""

    row_activated = Signal(int)
    selection_changed = Signal()

    def __init__(
        self,
        columns: Sequence[TableColumn | str] | None = None,
        parent: QWidget | None = None,
        *,
        empty_title: str = "暂无数据",
        empty_hint: str = "运行任务后，结果会显示在这里。",
    ) -> None:
        super().__init__(parent)
        self._columns = [self._normalize(item) for item in columns] if columns else []
        self._rows: list[dict[str, Any]] = []
        self._visible: list[dict[str, Any]] = []
        self._filter = ""
        self._empty_title = empty_title
        self._empty_hint = empty_hint
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._model = _RowTableModel(self)
        self._table = QTableView()
        self._table.setModel(self._model)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.setWordWrap(False)
        self._table.setAccessibleName("结果表")
        self._table.verticalHeader().hide()
        self._table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        selection = self._table.selectionModel()
        if selection is not None:
            selection.selectionChanged.connect(lambda *_: self.selection_changed.emit())
        self._table.doubleClicked.connect(lambda index: self.row_activated.emit(index.row()))

        self._empty = EmptyState(empty_title, empty_hint)
        self._stack = QStackedWidget()
        self._stack.addWidget(self._table)
        self._stack.addWidget(self._empty)
        layout.addWidget(self._stack)
        self._busy = BusyOverlay(self)
        if self._columns:
            self._apply_headers()
        self._sync_empty()

    @staticmethod
    def _normalize(item: TableColumn | str) -> TableColumn:
        return item if isinstance(item, TableColumn) else TableColumn(key=item)

    def set_columns(self, columns: Sequence[TableColumn | str]) -> None:
        self._columns = [self._normalize(item) for item in columns]
        self._apply_headers()
        self._render()

    def set_rows(self, rows: Sequence[Mapping[str, Any] | BaseModel]) -> None:
        self._rows = [_as_mapping(row) for row in rows]
        if not self._columns and self._rows:
            self._columns = [TableColumn(key=key) for key in self._rows[0]]
            self._apply_headers()
        self._render()

    def set_filter(self, query: str) -> None:
        """按任意列文本做不区分大小写的包含筛选。不改变 ``rows()``。"""

        self._filter = query.strip()
        self._render()

    def rows(self) -> list[dict[str, Any]]:
        return list(self._rows)

    def visible_rows(self) -> list[dict[str, Any]]:
        """当前筛选后可见的行。"""

        return list(self._visible)

    def selected_indexes(self) -> list[int]:
        model = self._table.selectionModel()
        if model is None:
            return []
        return sorted({index.row() for index in model.selectedRows()})

    def selected_rows(self) -> list[dict[str, Any]]:
        return [self._visible[index] for index in self.selected_indexes() if index < len(self._visible)]

    def select_row(self, index: int) -> None:
        """按可见行号选中一行。"""

        if 0 <= index < self._model.rowCount():
            self._table.selectRow(index)

    def cell_text(self, row: int, column: int) -> str:
        """可见单元格的展示文本。测试与无障碍读法共用。"""

        index = self._model.index(row, column)
        value = self._model.data(index, Qt.ItemDataRole.DisplayRole)
        return "" if value is None else str(value)

    def clear(self) -> None:
        self._rows = []
        self._filter = ""
        self._render()

    def set_busy(self, busy: bool, message: str = "正在处理…") -> None:
        """任务运行时盖住表格，结束后必须关掉。"""

        if busy:
            self._busy.show_busy(message)
        else:
            self._busy.hide_busy()

    def display_text(self, key: str, value: Any) -> str:
        """单元格展示文本。子类可覆盖以格式化日期、字节等。"""

        del key
        return "" if value is None else str(value)

    def _filtered(self) -> list[dict[str, Any]]:
        if not self._filter:
            return list(self._rows)
        needle = self._filter.casefold()
        matched: list[dict[str, Any]] = []
        for row in self._rows:
            haystack = " ".join("" if value is None else str(value) for value in row.values())
            if needle in haystack.casefold():
                matched.append(row)
        return matched

    def _apply_headers(self) -> None:
        header = self._table.horizontalHeader()
        stretch_done = False
        for index, column in enumerate(self._columns):
            mode = (
                QHeaderView.ResizeMode.Stretch
                if column.stretch
                else QHeaderView.ResizeMode.ResizeToContents
            )
            header.setSectionResizeMode(index, mode)
            stretch_done = stretch_done or column.stretch
        if self._columns and not stretch_done:
            header.setStretchLastSection(True)

    def _render(self) -> None:
        self._visible = self._filtered()
        self._model.reload()
        self._sync_empty()

    def _sync_empty(self) -> None:
        if self._visible:
            self._stack.setCurrentWidget(self._table)
            return
        if self._filter and self._rows:
            self._empty.set_copy("无匹配项", "试试别的关键字。")
        else:
            self._empty.set_copy(self._empty_title, self._empty_hint)
        self._stack.setCurrentWidget(self._empty)
