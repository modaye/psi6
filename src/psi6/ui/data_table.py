"""只读数据表：列定义 + 行记录。用 ``QTableView`` 模型，避免为每一格创建 Item。

行字典只存一份；筛选 / 排序只重排**原始行索引**，视图通过 ``fetchMore`` 按需取行，
几万行也不会在首屏为每一行计算列宽和几何。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel
from PySide6.QtCore import (
    QAbstractTableModel,
    QItemSelectionModel,
    QMimeData,
    QModelIndex,
    QPersistentModelIndex,
    QPoint,
    Qt,
    Signal,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QStackedWidget,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from psi6.ui.busy import BusyOverlay
from psi6.ui.context_menu import MenuAction, MenuTarget, attach_context_menu
from psi6.ui.empty_state import EmptyState
from psi6.ui.history import EditHistory

# 视图按需取行：首屏只发布一批，滚到接近底部时由 QTableView 触发 fetchMore。
_INITIAL_ROWS = 512
_FETCH_BATCH = 256


@dataclass(frozen=True)
class TableColumn:
    """一列表头。"""

    key: str
    title: str | None = None
    stretch: bool = False

    @property
    def header(self) -> str:
        return self.title or self.key


def _sort_value(value: Any) -> tuple[bool, int, str | float]:
    """空值永远排在最后。

    中间一位是类型分组：数字、文本各自成组，避免同一列里 ``str`` 和
    ``float`` 直接比较。``True``/``False`` 按文本比较，和展示一致。
    """

    if value is None or value == "":
        return (True, 0, "")
    if isinstance(value, bool):
        return (False, 1, str(value).casefold())
    if isinstance(value, (int, float)):
        return (False, 0, float(value))
    return (False, 1, str(value).casefold())


def _columns_from_rows(rows: Sequence[Mapping[str, Any]]) -> list[TableColumn]:
    if not rows:
        return []
    return [TableColumn(key=key) for key in rows[0]]


def _as_mapping(row: Mapping[str, Any] | BaseModel) -> dict[str, Any]:
    if isinstance(row, BaseModel):
        return row.model_dump()
    return dict(row)


class _RowTableModel(QAbstractTableModel):
    """把行字典交给视图按需取文本，并用 ``fetchMore`` 分批发布行。

    ``DataTable._visible`` 是**原始行索引**的有序序列，不再复制行字典；无筛选无排序时
    直接是 ``range``，构造是 O(1)。模型只把前 ``_fetched`` 行暴露给视图，``QTableView``
    滚动到接近底部时会调用 ``canFetchMore`` / ``fetchMore`` 再取一批，于是几万行也不会
    在首屏为每一行计算列宽和几何。按绝对行号选中 / 恢复视图状态时先用 ``ensure_rows``
    把对应行发布出来。
    """

    def __init__(self, host: DataTable) -> None:
        super().__init__(host)
        self._host = host
        self._fetched = 0

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex | None = None) -> int:
        if parent is not None and parent.isValid():
            return 0
        return min(self._fetched, len(self._host._visible))

    def columnCount(self, parent: QModelIndex | QPersistentModelIndex | None = None) -> int:
        if parent is not None and parent.isValid():
            return 0
        return len(self._host._columns)

    def data(
        self,
        index: QModelIndex | QPersistentModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if not index.isValid():
            return None
        visible = self._host._visible
        columns = self._host._columns
        row_number = index.row()
        if row_number >= len(visible) or index.column() >= len(columns):
            return None
        column = columns[index.column()]
        value = self._host._rows[visible[row_number]].get(column.key)
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

    def canFetchMore(self, parent: QModelIndex | QPersistentModelIndex | None = None) -> bool:
        if parent is not None and parent.isValid():
            return False
        return self._fetched < len(self._host._visible)

    def fetchMore(self, parent: QModelIndex | QPersistentModelIndex | None = None) -> None:
        if parent is not None and parent.isValid():
            return
        self.ensure_rows(self._fetched + _FETCH_BATCH)

    def ensure_rows(self, count: int) -> None:
        """至少发布前 ``count`` 行，供按绝对行号选中 / 恢复视图状态使用。"""

        total = len(self._host._visible)
        target = min(max(count, self._fetched), total)
        if target <= self._fetched:
            return
        first = self._fetched
        self.beginInsertRows(QModelIndex(), first, target - 1)
        self._fetched = target
        self.endInsertRows()

    def reload(self, *, initial: int | None = None) -> None:
        """重建结果后只发布首批；其余等视图来取，不再一次 reset 全部行。

        ``initial`` 是排序 / 筛选前已经发布的行数。带着它重建可以避免滚动条范围
        突然收缩、把已经滚到中部的视图弹回顶部；换整批数据时传 ``None``。
        """

        first = _INITIAL_ROWS if initial is None else max(_INITIAL_ROWS, initial)
        self._fetched = min(first, len(self._host._visible))
        self.beginResetModel()
        self.endResetModel()

    def flags(self, index: QModelIndex | QPersistentModelIndex) -> Qt.ItemFlag:
        if not self._host._drag_allowed():
            return super().flags(index)
        if not index.isValid():
            return Qt.ItemFlag.ItemIsDropEnabled
        return super().flags(index) | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsDropEnabled

    def supportedDropActions(self) -> Qt.DropAction:  # type: ignore[override]
        return Qt.DropAction.MoveAction

    def supportedDragActions(self) -> Qt.DropAction:  # type: ignore[override]
        return Qt.DropAction.MoveAction

    def mimeTypes(self) -> list[str]:
        return ["application/x-psi6-row"]

    def mimeData(self, indexes: list[QModelIndex]) -> QMimeData:  # type: ignore[override]
        mime = QMimeData()
        rows = sorted({index.row() for index in indexes if index.isValid()})
        current = self._host._table.currentIndex().row()
        source = current if current in rows else (rows[0] if rows else -1)
        mime.setData("application/x-psi6-row", str(source).encode("ascii"))
        return mime

    def dropMimeData(
        self,
        data: QMimeData,
        action: Qt.DropAction,
        row: int,
        column: int,
        parent: QModelIndex | QPersistentModelIndex,
    ) -> bool:
        """把拖动的那一行插到落下的位置。排序或筛选进行中时拒绝。"""

        del column
        if action != Qt.DropAction.MoveAction or not self._host._drag_allowed():
            return False
        payload = data.data("application/x-psi6-row") if data is not None else None
        raw = b"" if payload is None or payload.isEmpty() else bytes(payload.data())
        try:
            source = int(raw)
        except ValueError:
            return False
        if row >= 0:
            destination = row
        elif parent.isValid():
            destination = parent.row()
        else:
            destination = len(self._host._visible)
        return self._host.move_rows(source, 1, destination)


class DataTable(QWidget):
    """结果表：固定列或按本次数据推导列。适合预览和任务清单，不负责分页和单元格编辑。

    行只存一份 ``_rows``；筛选 / 排序只维护一份**原始行索引**的顺序（无操作时是
    ``range``，零拷贝）。模型通过 ``fetchMore`` 分批把行发布给 ``QTableView``，
    几万行也不会在首屏为每行计算列宽和几何。

    需要调整原始行顺序时调用 ``set_reorderable(True)``，然后可以拖动一行。
    排序或筛选进行中时拖动无效，避免和当前的可见顺序打架。
    """

    row_activated = Signal(int)
    record_activated = Signal(object)
    selection_changed = Signal()
    rows_reordered = Signal()

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
        self._columns_locked = bool(self._columns)
        # 列管理设过的可见列（key 列表）。None 表示「从没设过，全部可见」。
        self._visible_keys: list[str] | None = None
        self._rows: list[dict[str, Any]] = []
        self._sort_key: str | None = None
        self._sort_descending = False
        # 可见行的原始行索引（有序）。range 时零拷贝；排序/筛选后才落成 list。
        self._visible: Sequence[int] = range(0)
        self._filter = ""
        self._reselecting = False
        self._reorderable = False
        self._busy_on = False
        self._history: EditHistory | None = None
        self._move_epoch = 0
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
        self._table.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self._table.setDefaultDropAction(Qt.DropAction.MoveAction)
        self._table.setDragDropOverwriteMode(False)
        self._table.setDragEnabled(False)
        self._table.setAcceptDrops(False)
        selection = self._table.selectionModel()
        if selection is not None:
            selection.selectionChanged.connect(self._on_selection_changed)
        self._table.horizontalHeader().sectionClicked.connect(self._cycle_sort)
        self._table.doubleClicked.connect(self._activate_row)

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
        """固定列。之后 ``clear`` 和 ``set_rows`` 不再按数据改列。"""

        self._columns_locked = True
        self._columns = [self._normalize(item) for item in columns]
        self._apply_headers()
        self._render()

    # -- 列状态（列管理用） ------------------------------------------------

    def columns(self) -> list[TableColumn]:
        """当前列定义，按显示顺序。副本，改了不影响表格。"""

        return list(self._columns)

    def visible_columns(self) -> list[str]:
        """当前可见列的 key，按显示顺序。"""

        return [
            column.key
            for index, column in enumerate(self._columns)
            if not self._table.isColumnHidden(index)
        ]

    def set_visible_columns(self, keys: Sequence[str]) -> None:
        """按 key 列表决定显示哪几列、什么顺序。

        只在**可见列**里重排：隐藏列保留原来的相对位置，重新显示时回到原处。
        没在 ``keys`` 里的列被隐藏，但不会从 ``_columns`` 里删掉——``cell_text``
        的列号语义因此保持不变。
        """

        wanted = [str(key) for key in keys]
        known = {column.key for column in self._columns}
        visible = [key for key in wanted if key in known]
        # 完整顺序 = 可见列（按要求） + 隐藏列（保持原相对位置）。
        by_key = {column.key: column for column in self._columns}
        ordered: list[TableColumn] = [by_key[key] for key in visible]
        ordered.extend(column for column in self._columns if column.key not in visible)
        self._columns = ordered
        self._apply_headers()
        self._visible_keys = list(visible)
        self._reapply_visibility(visible)
        self._render()

    def _reapply_visibility(self, visible: Sequence[str] | None = None) -> None:
        """按已记录的可见列重新设置隐藏状态。

        ``visible`` 为 ``None`` 时沿用上次记录的 ``_visible_keys``——数据刷新后
        列管理设过的显隐要继续有效。``_visible_keys`` 为 ``None`` 表示从没设过，
        此时全部列可见。
        """

        if visible is None:
            visible = self._visible_keys
        if visible is None:
            return
        keys = set(visible)
        for index, column in enumerate(self._columns):
            self._table.setColumnHidden(index, column.key not in keys)

    def set_rows(self, rows: Sequence[Mapping[str, Any] | BaseModel]) -> None:
        self._move_epoch += 1
        self._rows = [_as_mapping(row) for row in rows]
        if not self._columns_locked:
            # 自动推导列时保留已有的显隐与顺序：新数据多出来的列追加在末尾，
            # 少掉的列直接消失，剩下��按原来的相对位置排列。
            previous = {column.key: column for column in self._columns}
            derived = _columns_from_rows(self._rows)
            kept = [column for column in derived if column.key in previous]
            kept.sort(key=lambda column: list(previous).index(column.key))
            self._columns = kept + [column for column in derived if column.key not in previous]
            self._apply_headers()
            self._reapply_visibility()
        if self._sort_key is not None and not any(
            column.key == self._sort_key for column in self._columns
        ):
            self._sort_key = None
            self._sort_descending = False
        self._render(keep_view=False)

    def sort_by(self, key: str, *, descending: bool = False) -> None:
        """按列排序可见行。之后的 ``set_rows`` 会沿用同一规则。空值排在最后。

        ``rows()`` 仍按调用方给出的原始顺序返回；排序只影响表格和
        ``visible_rows()``。排序前后保留选中的行、当前行和滚动位置。
        """

        self._sort_key = key
        self._sort_descending = descending
        self._render()

    def set_filter(self, query: str) -> None:
        """按各列展示文本做不区分大小写的包含筛选。不改变 ``rows()``。

        筛选和排序一样保留选中的行、当前行和滚动位置；行被筛掉时选中随之消失。
        """

        self._filter = query.strip()
        self._render()

    def set_reorderable(self, enabled: bool) -> None:
        """允许拖动一行来改变 ``rows()`` 的原始顺序。默认关闭。"""

        self._reorderable = bool(enabled)
        self._sync_reorder()

    def reorderable(self) -> bool:
        return self._reorderable

    def set_history(self, history: EditHistory | None) -> None:
        """拖动换序记入这本撤销栈。换一批行（``set_rows`` / ``clear``）后，旧步骤会失效。"""

        self._history = history

    def move_rows(self, start: int, count: int, destination: int) -> bool:
        """把连续的可见行挪到 ``destination`` 之前。

        下标都是移动前的可见行号，``destination`` 可以等于行数（表示放到末尾）。
        还没打开拖放、或者当前有排序 / 筛选时返回 ``False``，不改数据。
        挪到原位返回 ``True``。
        """

        if not self._reorderable or self._filter or self._sort_key is not None:
            return False
        total = len(self._rows)
        if (
            count <= 0
            or start < 0
            or start + count > total
            or destination < 0
            or destination > total
        ):
            return False
        if destination == start or destination == start + count:
            return True
        new_start = destination if destination < start else destination - count
        undo_dest = start if destination > start else start + count
        epoch = self._move_epoch

        def apply() -> None:
            if self._move_epoch != epoch:
                return
            self._relocate(start, count, destination)

        def revert() -> None:
            if self._move_epoch != epoch:
                return
            self._relocate(new_start, count, undo_dest)

        if self._history is None:
            apply()
        else:
            self._history.push("调整行顺序", apply=apply, revert=revert)
        return True

    def _drag_allowed(self) -> bool:
        return (
            self._reorderable and not self._filter and self._sort_key is None and not self._busy_on
        )

    def _sync_reorder(self) -> None:
        enabled = self._drag_allowed()
        self._table.setDragEnabled(enabled)
        self._table.setAcceptDrops(enabled)
        self._table.setDropIndicatorShown(enabled)

    def _relocate(self, start: int, count: int, destination: int) -> None:
        total = len(self._rows)
        if (
            count <= 0
            or start < 0
            or start + count > total
            or destination < 0
            or destination > total
            or destination == start
            or destination == start + count
        ):
            return
        moving = self._rows[start : start + count]
        del self._rows[start : start + count]
        insert_at = destination if destination < start else destination - count
        self._rows[insert_at:insert_at] = moving
        wanted = {id(row) for row in moving}
        self._render(keep_view=False)
        visible = [
            number for number, raw in enumerate(self._visible) if id(self._rows[raw]) in wanted
        ]
        self._select_visible(visible)
        self.rows_reordered.emit()

    def _select_visible(self, rows: list[int]) -> None:
        if not rows:
            return
        self._model.ensure_rows(max(rows) + 1)
        selection = self._table.selectionModel()
        if selection is None:
            return
        self._reselecting = True
        try:
            first = True
            for row in rows:
                flag = (
                    QItemSelectionModel.SelectionFlag.ClearAndSelect
                    if first
                    else QItemSelectionModel.SelectionFlag.Select
                )
                selection.select(
                    self._model.index(row, 0),
                    flag | QItemSelectionModel.SelectionFlag.Rows,
                )
                first = False
            selection.setCurrentIndex(
                self._model.index(rows[0], 0),
                QItemSelectionModel.SelectionFlag.NoUpdate,
            )
        finally:
            self._reselecting = False

    def rows(self) -> list[dict[str, Any]]:
        """行的副本。改返回值不会改表格里的数据。"""

        return [dict(row) for row in self._rows]

    def visible_rows(self) -> list[dict[str, Any]]:
        """当前筛选后可见的行，同样是副本。"""

        return [dict(self._rows[index]) for index in self._visible]

    def selected_indexes(self) -> list[int]:
        model = self._table.selectionModel()
        if model is None:
            return []
        return sorted({index.row() for index in model.selectedRows()})

    def selected_rows(self) -> list[dict[str, Any]]:
        return [
            dict(self._rows[self._visible[index]])
            for index in self.selected_indexes()
            if 0 <= index < len(self._visible)
        ]

    def context_menu(
        self, builder: Callable[[MenuTarget], Sequence[MenuAction] | None]
    ) -> QTableView:
        """挂右键菜单，返回底层的 ``QTableView``。

        ``builder`` 拿到命中行的 ``MenuTarget``：``key`` 是可见行号，``data`` 是行副本，
        右键落在空白处时 ``target.hit`` 为 ``False``。
        """

        return attach_context_menu(self, builder)  # type: ignore[return-value]

    def _context_menu_source(self) -> QWidget:
        return self._table

    def column_menu(
        self, builder: Callable[[MenuTarget], Sequence[MenuAction] | None]
    ) -> QHeaderView:
        """在**列头**上挂右键菜单，返回 ``QHeaderView``。

        命中的列在 ``MenuTarget.key`` 里（列的 key，不是列号），``kind`` 是
        ``columns``。菜单里常用 ``MenuAction(checked=...)`` 做列的显隐开关。
        """

        return attach_context_menu(  # type: ignore[return-value]
            self, builder, source=self._table.horizontalHeader()
        )

    def _column_menu_target(self, pos: QPoint) -> MenuTarget | None:
        """列头右键的命中目标。"""

        header = self._table.horizontalHeader()
        section = header.logicalIndexAt(pos)
        if not 0 <= section < len(self._columns):
            return MenuTarget("columns", position=pos)
        column = self._columns[section]
        return MenuTarget("columns", key=column.key, data=column, position=pos)

    def _context_menu_target(self, pos: QPoint) -> MenuTarget | None:
        index = self._table.indexAt(pos)
        if not index.isValid():
            return MenuTarget("table", position=pos)
        row = index.row()
        if not 0 <= row < len(self._visible):
            return None
        # 右键落在未选中的行：先选中它，菜单里的「选中项」才和行为一致。
        if row not in self.selected_indexes():
            self.select_row(row)
        return MenuTarget("table", key=row, data=dict(self._rows[self._visible[row]]), position=pos)

    def select_row(self, index: int) -> None:
        """按可见行号选中一行，并把它设为当前行。

        行号允许落在还没发布给视图的区间，这里先把对应行发布出来。
        """

        if 0 <= index < len(self._visible):
            self._model.ensure_rows(index + 1)
            self._table.selectRow(index)
            selection = self._table.selectionModel()
            if selection is not None:
                selection.setCurrentIndex(
                    self._model.index(index, 0),
                    QItemSelectionModel.SelectionFlag.NoUpdate,
                )

    def cell_text(self, row: int, column: int) -> str:
        """可见单元格的展示文本。测试与无障碍读法共用。

        直接按索引取 ``_rows``，不走 ``QAbstractTableModel.index()``：那条路径受
        ``rowCount()`` 限制，为了读第 3999 行就得先把前面所有行发布给视图。
        """

        if not 0 <= row < len(self._visible) or not 0 <= column < len(self._columns):
            return ""
        column_def = self._columns[column]
        value = self._rows[self._visible[row]].get(column_def.key)
        return self.display_text(column_def.key, value)

    def clear(self) -> None:
        """清空行。没有调用 ``set_columns`` 时，自动推导的列一并丢掉。"""

        self._move_epoch += 1
        self._rows = []
        self._filter = ""
        self._sort_key = None
        self._sort_descending = False
        if not self._columns_locked:
            self._columns = []
        self._render(keep_view=False)

    def set_busy(self, busy: bool, message: str = "正在处理…") -> None:
        """任务运行时盖住表格，结束后必须关掉。"""

        self._busy_on = bool(busy)
        if busy:
            self._busy.show_busy(message)
        else:
            self._busy.hide_busy()
        self._sync_reorder()

    def display_text(self, key: str, value: Any) -> str:
        """单元格展示文本。子类可覆盖以格式化日期、字节等。"""

        del key
        return "" if value is None else str(value)

    def _filtered(self) -> Sequence[int]:
        """通过筛选的行在 ``_rows`` 里的原始索引；无筛选时零拷贝。"""

        if not self._filter:
            return range(len(self._rows))
        needle = self._filter.casefold()
        matched: list[int] = []
        for index, row in enumerate(self._rows):
            haystack = " ".join(
                self.display_text(column.key, row.get(column.key)) for column in self._columns
            )
            if needle in haystack.casefold():
                matched.append(index)
        return matched

    def _apply_headers(self) -> None:
        header = self._table.horizontalHeader()
        # 表头与单元格统一左对齐：默认居中会让被拉伸的宽列表头飘离内容
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
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

    def _cycle_sort(self, section: int) -> None:
        if section < 0 or section >= len(self._columns):
            return
        key = self._columns[section].key
        if self._sort_key != key:
            self.sort_by(key, descending=False)
            return
        if not self._sort_descending:
            self.sort_by(key, descending=True)
            return
        self._sort_key = None
        self._sort_descending = False
        self._render()

    def _sorted(self, indexes: Sequence[int]) -> Sequence[int]:
        """按当前规则返回排序后的**原始行索引**序列。不改变 ``_rows`` 的原始顺序。"""

        if self._sort_key is None:
            return indexes
        key = self._sort_key
        # 每行只算一次排序键：几万行时避免 sort 的 O(N log N) 次重复取值。
        values = {index: _sort_value(self._rows[index].get(key)) for index in indexes}
        present = [index for index in indexes if not values[index][0]]
        missing = [index for index in indexes if values[index][0]]
        # 类型分组位参与排序，同列混合数字和文本也不会比较不同类型。
        present.sort(key=lambda index: values[index][1:], reverse=self._sort_descending)
        return present + missing

    def _apply_sort_indicator(self) -> None:
        header = self._table.horizontalHeader()
        if self._sort_key is None:
            header.setSortIndicatorShown(False)
            return
        index = next(
            (
                position
                for position, column in enumerate(self._columns)
                if column.key == self._sort_key
            ),
            None,
        )
        if index is None:
            header.setSortIndicatorShown(False)
            return
        header.setSortIndicatorShown(True)
        order = (
            Qt.SortOrder.DescendingOrder if self._sort_descending else Qt.SortOrder.AscendingOrder
        )
        header.setSortIndicator(index, order)

    def _render(self, *, keep_view: bool = True) -> None:
        """重建可见行。排序和筛选时保住选中行、当前行与滚动位置。

        行身份用 ``_rows`` 的原始索引而不是 ``id(row)``：索引在重建后依然稳定，
        也不需要把行字典复制进 ``_visible``。
        """

        selected: set[int] = set()
        current_raw: int | None = None
        scroll = 0
        published = 0
        if keep_view:
            selected = set(self._selected_raw())
            current = self._table.currentIndex()
            if current.isValid() and 0 <= current.row() < len(self._visible):
                current_raw = self._visible[current.row()]
            scroll = self._table.verticalScrollBar().value()
            published = self._model.rowCount()
        self._visible = self._sorted(self._filtered())
        self._reselecting = True
        try:
            self._model.reload(initial=published if keep_view else None)
            self._restore_view(selected, current_raw, scroll)
        finally:
            self._reselecting = False
        self._apply_sort_indicator()
        self._sync_empty()
        self._sync_reorder()

    def _selected_raw(self) -> list[int]:
        """当前选中行对应的 ``_rows`` 原始索引。"""

        selection = self._table.selectionModel()
        if selection is None:
            return []
        return [
            self._visible[index.row()]
            for index in selection.selectedRows()
            if 0 <= index.row() < len(self._visible)
        ]

    def _restore_view(
        self,
        selected: set[int],
        current_raw: int | None,
        scroll: int,
    ) -> None:
        # 选中 / 当前行可能落在首屏发布范围之外，先一次把这些行发布出来，
        # 否则 self._model.index(...) 会返回无效索引。
        wanted = [
            row_number
            for row_number, raw in enumerate(self._visible)
            if raw in selected or (current_raw is not None and raw == current_raw)
        ]
        if wanted:
            self._model.ensure_rows(max(wanted) + 1)
        selection = self._table.selectionModel()
        if selection is not None:
            flags = (
                QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows
            )
            found_current = -1
            for row_number, raw in enumerate(self._visible):
                if raw in selected:
                    selection.select(self._model.index(row_number, 0), flags)
                if current_raw is not None and raw == current_raw:
                    found_current = row_number
            if found_current >= 0:
                selection.setCurrentIndex(
                    self._model.index(found_current, 0),
                    QItemSelectionModel.SelectionFlag.NoUpdate,
                )
        self._table.verticalScrollBar().setValue(scroll)

    def _on_selection_changed(self) -> None:
        if not self._reselecting:
            self.selection_changed.emit()

    def _activate_row(self, index: QModelIndex) -> None:
        if not index.isValid() or not 0 <= index.row() < len(self._visible):
            return
        self.row_activated.emit(index.row())
        self.record_activated.emit(dict(self._rows[self._visible[index.row()]]))

    def _sync_empty(self) -> None:
        if len(self._visible) > 0:
            self._stack.setCurrentWidget(self._table)
            return
        if self._filter and self._rows:
            self._empty.set_copy("无匹配项", "试试别的关键字。")
        else:
            self._empty.set_copy(self._empty_title, self._empty_hint)
        self._stack.setCurrentWidget(self._empty)
