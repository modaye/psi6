"""列管理：勾选列的显隐、调整列的顺序，并把这个状态持久化。

按 ADR 0003 的约定，列管理**单独成控件**，不塞进 ``DataTable``：结果表只负责
「按什么顺序显示哪几列」，这个控件负责「用户想看哪几列、什么顺序」。

用法：

    picker = ColumnPicker()
    picker.set_columns(table.columns())
    picker.columns_changed.connect(lambda cols: table.set_visible_columns(cols))
    picker.save_state(store, "my-app")

``ColumnState`` 只记 **列 key 的顺序和显隐**，不记标题和宽度：标题会随数据变，
宽度属于视图不属于配置。文件里少写几个 key 或者写了已经不存在的 key，都会被
安全跳过，不会让表格少显示内容。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from functools import partial
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from psi6.runtime.config import ConfigStore
from psi6.ui.buttons import ghost_button
from psi6.ui.context_menu import MenuAction
from psi6.ui.empty_state import EmptyState

_DEFAULT_STATE_FILE = "columns.json"


@dataclass(frozen=True)
class ColumnState:
    """一列的显示状态。

    ``visible=False`` 表示这一列被隐藏，但**顺序仍然保留**——隐藏后再显示会回到
    原来的位置，而不是跑到末尾。
    """

    key: str
    title: str
    visible: bool = True
    required: bool = False


def _read_column(item: Any) -> tuple[str, str]:
    """从一项里读出 ``(key, title)``。

    接受字符串，也接受任何带 ``key`` 属性的对象——``DataTable`` 的 ``TableColumn``
    可以直接传进来。读不到 ``key`` 的当作字符串处理。
    """

    if isinstance(item, str):
        return item, ""
    key = getattr(item, "key", None)
    if not isinstance(key, str) or not key:
        return str(item), ""
    title = getattr(item, "title", None)
    if not isinstance(title, str) or not title:
        title = getattr(item, "header", None)
    return key, title if isinstance(title, str) else ""


class ColumnPicker(QWidget):
    """列的显隐与顺序。

    ``columns_changed`` 给出当前可见且已排序的列 key 列表。控件本身不碰表格：
    由调用方把结果接到 ``DataTable.set_visible_columns()`` 上。
    """

    columns_changed = Signal(list)

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        empty_title: str = "没有可配置的列",
        empty_hint: str = "表格还没推导出来列。",
        state_file: str = _DEFAULT_STATE_FILE,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("psi6ColumnPicker")
        self._state_file = state_file
        self._columns: list[ColumnState] = []
        self._updating = False

        self._list = QListWidget()
        self._list.setObjectName("psi6ColumnPickerList")
        self._list.setAccessibleName("列列表")
        self._list.itemChanged.connect(self._on_item_changed)
        self._list.currentRowChanged.connect(self._on_current_changed)

        self._empty = EmptyState(empty_title, empty_hint)

        self._up = ghost_button("上移")
        self._up.setObjectName("psi6ColumnPickerUp")
        self._up.clicked.connect(lambda: self._move(-1))
        self._down = ghost_button("下移")
        self._down.setObjectName("psi6ColumnPickerDown")
        self._down.clicked.connect(lambda: self._move(1))
        self._reset = ghost_button("全部显示")
        self._reset.setObjectName("psi6ColumnPickerReset")
        self._reset.clicked.connect(self.show_all)

        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.setSpacing(8)
        buttons.addWidget(self._up)
        buttons.addWidget(self._down)
        buttons.addStretch()
        buttons.addWidget(self._reset)

        self._hint = QLabel("勾选决定显示哪几列，上下移动调整顺序。")
        self._hint.setObjectName("psi6Hint")
        self._hint.setWordWrap(True)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(8)
        body_layout.addWidget(self._list, stretch=1)
        body_layout.addLayout(buttons)
        body_layout.addWidget(self._hint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(body, stretch=1)
        layout.addWidget(self._empty)
        self._empty.hide()
        self._list.hide()

    # -- 列清单 ------------------------------------------------------------

    def columns(self) -> list[ColumnState]:
        """当前列状态（按显示顺序）。副本，改了不影响控件。"""

        return list(self._columns)

    def visible_columns(self) -> list[str]:
        """当前可见列的 key，按显示顺序。"""

        return [column.key for column in self._columns if column.visible]

    def set_columns(
        self,
        columns: Sequence[ColumnState | str | Any],
        *,
        titles: Mapping[str, str] | None = None,
    ) -> None:
        """设置列清单。

        每一项可以是 ``ColumnState``、列 key 字符串，或者任何带 ``key`` 属性的
        对象（``DataTable`` 的 ``TableColumn`` 就能直接传进来，读它的 ``key`` 与
        ``title``）。

        ``required=True`` 的列不可隐藏（通常是主键列），仍会出现在列表里但勾选框
        被禁用。``titles`` 给没有标题的列补显示名。

        **不重置显隐**：清单里已经有的 key 会保留当前的显隐状态，只有新出现的列
        默认可见。所以「先设清单再恢复状态」和「先恢复状态再设清单」都成立。
        """

        states: list[ColumnState] = []
        for item in columns:
            if isinstance(item, ColumnState):
                states.append(item)
                continue
            key, title = _read_column(item)
            if titles and key in titles:
                title = titles[key]
            states.append(ColumnState(key=key, title=title if title else key))

        previous = {column.key: column.visible for column in self._columns}
        self._columns = [
            ColumnState(
                key=column.key,
                title=column.title,
                visible=previous.get(column.key, column.visible),
                required=column.required,
            )
            for column in states
        ]
        self._rebuild()
        self.columns_changed.emit(self.visible_columns())

    def set_visible(self, key: str, visible: bool) -> None:
        """显隐一列。``required`` 的列忽略隐藏请求。找不到 key 则忽略。"""

        for index, column in enumerate(self._columns):
            if column.key != key:
                continue
            if column.required and not visible:
                return
            if column.visible == visible:
                return
            updated = list(self._columns)
            updated[index] = ColumnState(
                key=column.key,
                title=column.title,
                visible=visible,
                required=column.required,
            )
            self._columns = updated
            self._rebuild()
            self.columns_changed.emit(self.visible_columns())
            return

    def show_all(self) -> None:
        """全部显示。已经有变化时才发信号。"""

        if all(column.visible for column in self._columns):
            return
        self._columns = [
            ColumnState(column.key, column.title, visible=True, required=column.required)
            for column in self._columns
        ]
        self._rebuild()
        self.columns_changed.emit(self.visible_columns())

    def move_column(self, key: str, offset: int) -> None:
        """把一列往上（``offset < 0``）或往下移一格。已经在边界则忽略。

        名字带 ``_column`` 后缀：``QWidget.move()`` 已被 Qt 占用，覆盖它会让布局
        里的 ``widget.move(x, y)`` 悄悄改成调列排序。
        """

        if not self._columns:
            return
        index = next((i for i, column in enumerate(self._columns) if column.key == key), -1)
        if index < 0:
            return
        target = index + (1 if offset > 0 else -1)
        if not 0 <= target < len(self._columns):
            return
        columns = list(self._columns)
        columns[index], columns[target] = columns[target], columns[index]
        self._columns = columns
        self._rebuild()
        self._list.setCurrentRow(target)
        self.columns_changed.emit(self.visible_columns())

    # -- 状态 --------------------------------------------------------------

    def state(self) -> dict[str, Any]:
        """导出状态。只记 key 的顺序和显隐，不记标题。"""

        return {
            "columns": [{"key": column.key, "visible": column.visible} for column in self._columns]
        }

    def set_state(self, state: Mapping[str, Any]) -> None:
        """恢复状态。

        文件里写了但当前没有的 key 跳过；当前有但文件里没写的列保持原样并留在
        原有位置。少写几个 key 不会让列凭空消失。
        """

        raw = state.get("columns")
        if not isinstance(raw, (list, tuple)):
            return
        saved: dict[str, bool] = {}
        order: list[str] = []
        for item in raw:
            if not isinstance(item, Mapping):
                continue
            key = item.get("key")
            if not isinstance(key, str) or key in saved:
                continue
            saved[key] = bool(item.get("visible", True))
            order.append(key)

        known = {column.key for column in self._columns}
        original = [column.key for column in self._columns]
        # 文件提到的列按文件顺序；没提到的列保持彼此原有的相对顺序。
        mentioned = [key for key in order if key in known]
        rest = [key for key in original if key not in set(mentioned)]

        # 按原始位置交错合并：原来是什么位置，现在还是什么位置，
        # 只是「文件提到的那些」内部按文件重排了。
        mentioned_set = set(mentioned)
        merged: list[str] = []
        mi = 0
        ri = 0
        for key in original:
            if key in mentioned_set:
                merged.append(mentioned[mi])
                mi += 1
            else:
                merged.append(rest[ri])
                ri += 1

        by_key = {column.key: column for column in self._columns}
        self._columns = [
            ColumnState(
                key=key,
                title=by_key[key].title,
                visible=saved.get(key, by_key[key].visible),
                required=by_key[key].required,
            )
            for key in merged
        ]
        self._rebuild()
        self.columns_changed.emit(self.visible_columns())

    def save_state(self, store: ConfigStore, app_name: str) -> None:
        store.save_data(app_name, self._state_file, self.state())

    def restore_state(self, store: ConfigStore, app_name: str) -> bool:
        payload = store.load_data(app_name, self._state_file)
        if not payload:
            return False
        self.set_state(payload)
        return True

    # -- 内部 --------------------------------------------------------------

    def _rebuild(self) -> None:
        """按 ``_columns`` 重建列表项。"""

        self._updating = True
        self._list.clear()
        for column in self._columns:
            item = QListWidgetItem(column.title)
            item.setData(Qt.ItemDataRole.UserRole, column.key)
            item.setFlags(
                item.flags()
                | Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsEnabled
            )
            item.setCheckState(Qt.CheckState.Checked if column.visible else Qt.CheckState.Unchecked)
            if column.required:
                # 主键列不能藏：勾选框禁用，但保持选中。
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked)
            self._list.addItem(item)
        self._updating = False
        self._sync_empty()
        self._update_buttons()

    def _sync_empty(self) -> None:
        has_columns = bool(self._columns)
        self._list.setVisible(has_columns)
        self._empty.setVisible(not has_columns)

    def _update_buttons(self) -> None:
        row = self._list.currentRow()
        has_selection = 0 <= row < len(self._columns)
        self._up.setEnabled(has_selection and row > 0)
        self._down.setEnabled(has_selection and row < len(self._columns) - 1)

    def _on_item_changed(self, item: QListWidgetItem) -> None:
        if self._updating:
            return
        key = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(key, str):
            return
        visible = item.checkState() == Qt.CheckState.Checked
        self.set_visible(key, visible)

    def _on_current_changed(self, _row: int) -> None:
        self._update_buttons()

    def _move(self, offset: int) -> None:
        row = self._list.currentRow()
        if not 0 <= row < len(self._columns):
            return
        self.move_column(self._columns[row].key, offset)


def _toggle_call(key: str, turn_on: bool, on_toggle: Callable[[str, bool], None]) -> None:
    """``MenuAction`` 回调的适配器：把「切到反状态」算成明确的新状态。"""

    on_toggle(key, turn_on)


def column_toggle_menu(
    columns: Sequence[Any],
    visible: Sequence[str],
    *,
    on_toggle: Callable[[str, bool], None],
    title: str = "显示哪些列",
) -> list[MenuAction]:
    """列头右键用的「勾选显示哪些列」菜单。

    每列一项，勾选状态是当前是否可见；点一下调用 ``on_toggle(key, 新状态)``。
    ``required`` 的列不可隐藏，所以不显示勾选框（用 ``MenuAction`` 的普通项表达
    「必须在」）。
    """

    shown = set(visible)
    items: list[MenuAction] = []
    for item in columns:
        if isinstance(item, ColumnState):
            state = item
        else:
            key, item_title = _read_column(item)
            state = ColumnState(key=key, title=item_title or key)
        if state.required:
            items.append(MenuAction(state.title, enabled=False))
            continue
        is_visible = state.key in shown
        items.append(
            MenuAction(
                state.title,
                partial(_toggle_call, state.key, not is_visible, on_toggle),
                checked=is_visible,
            )
        )
    return items
