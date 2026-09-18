"""只读属性表：查看选中行或对象，不负责编辑（编辑走 pydantic_form）。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from psi6.ui.empty_state import EmptyState


class PropertyList(QWidget):
    """两列键值表。适合点选结果行后展示详情。"""

    def __init__(
        self,
        *,
        empty_title: str = "未选择",
        empty_hint: str = "在结果表中点选一行查看详情。",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("psi6PropertyList")
        self._empty_title = empty_title
        self._empty_hint = empty_hint
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(("属性", "值"))
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().hide()
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._table.setAlternatingRowColors(True)

        self._empty = EmptyState(empty_title, empty_hint)
        self._stack = QStackedWidget()
        self._stack.addWidget(self._empty)
        self._stack.addWidget(self._table)
        layout.addWidget(self._stack)
        self._show_empty()

    def set_values(self, data: Mapping[str, Any] | BaseModel | None) -> None:
        """写入一组键值。``None`` 或空映射回到空态。"""

        mapping = _as_mapping(data)
        if not mapping:
            self._table.setRowCount(0)
            self._show_empty()
            return
        self._table.setRowCount(len(mapping))
        for row, (key, value) in enumerate(mapping.items()):
            key_item = QTableWidgetItem(str(key))
            value_text = "" if value is None else str(value)
            value_item = QTableWidgetItem(value_text)
            value_item.setToolTip(value_text)
            self._table.setItem(row, 0, key_item)
            self._table.setItem(row, 1, value_item)
        self._stack.setCurrentWidget(self._table)

    def values(self) -> dict[str, str]:
        """当前表中的键值（字符串化后）。"""

        result: dict[str, str] = {}
        for row in range(self._table.rowCount()):
            key_item = self._table.item(row, 0)
            value_item = self._table.item(row, 1)
            if key_item is None:
                continue
            result[key_item.text()] = "" if value_item is None else value_item.text()
        return result

    def clear(self) -> None:
        self.set_values(None)

    def _show_empty(self) -> None:
        self._empty.set_copy(self._empty_title, self._empty_hint)
        self._stack.setCurrentWidget(self._empty)


def _as_mapping(data: Mapping[str, Any] | BaseModel | None) -> dict[str, Any]:
    if data is None:
        return {}
    if isinstance(data, BaseModel):
        return data.model_dump()
    return dict(data)
