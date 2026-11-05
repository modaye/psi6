"""只读树视图：列定义 + 层级节点。

用 ``QTreeView`` + 自定义 ``QAbstractItemModel``，避免为每一格创建 ``QStandardItem``。
定位与 ``DataTable`` 一致——**结果浏览**，不做单元格编辑、不做分页。需要树表时另起控件。

典型用法：

    root = TreeNode(id="src", data={"name": "src"})
    root.children = [TreeNode(id="a", data={"name": "a.py"}),
                     TreeNode(id="b", data={"name": "b.py"})]
    tree = TreeView([TreeColumn("name", "名称", stretch=True)])
    tree.set_nodes([root])
    tree.node_activated.connect(on_open)

非常大的树（如文件系统）用 ``child_loader`` 走懒加载，展开节点时才取子节点。
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from PySide6.QtCore import (
    QAbstractItemModel,
    QModelIndex,
    QPoint,
    Qt,
    Signal,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QStackedWidget,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from psi6.ui.busy import BusyOverlay
from psi6.ui.context_menu import MenuAction, MenuTarget, attach_context_menu
from psi6.ui.empty_state import EmptyState

# 根节点的父键。用 0 是因为没有节点的 id 会是 0（id() 不会返回 0 给对象）。
_ROOT_KEY = 0


@dataclass
class TreeColumn:
    """一列。``key`` 对应节点 ``data`` 的字段名。"""

    key: str
    title: str | None = None
    stretch: bool = False

    @property
    def header(self) -> str:
        return self.title or self.key


@dataclass
class TreeNode:
    """树里的一个节点。

    ``id`` 必须在整棵树内唯一，用于选中持久化与懒加载索引。
    ``children`` 是子节点；懒加载模式下可先留空，由 ``child_loader`` 在展开时填充。
    ``has_children`` 只在懒加载模式下使用：标记为 ``True`` 的节点会显示展开箭头，
    展开时调用 ``child_loader(node)``；叶子设 ``False`` 以免出现空箭头。
    """

    id: str
    data: dict[str, Any] = field(default_factory=dict)
    children: list[TreeNode] = field(default_factory=list)
    has_children: bool = True


class _TreeModel(QAbstractItemModel):
    """把层级节点交给视图按需绘制。只画可见行，全量数据存在 ``_source`` 里。"""

    def __init__(self, host: TreeView) -> None:
        super().__init__(host)
        self._host = host
        # id(node) -> 原始子节点（用户给的，或懒加载取回的）
        self._source: dict[int, list[TreeNode]] = {_ROOT_KEY: []}
        # id(node) -> 当前筛选下显示的子节点
        self._display: dict[int, list[TreeNode]] = {_ROOT_KEY: []}
        # id(node) -> 父节点（根节点为 None）
        self._parents: dict[int, TreeNode | None] = {}
        # id(node) -> node 本身，便于由父键找回节点
        self._by_id: dict[int, TreeNode] = {}
        self._roots: list[TreeNode] = []

    # -- 数据写入 ----------------------------------------------------------
    def load_source(self, roots: Sequence[TreeNode], *, reset: bool = True) -> None:
        self._source = {_ROOT_KEY: list(roots)}
        self._by_id = {}
        for node in roots:
            self._index_subtree(node)
        self._rebuild_display(reset=reset)

    def _index_subtree(self, node: TreeNode) -> None:
        self._by_id[id(node)] = node
        for child in node.children:
            self._index_subtree(child)

    # -- 筛选后的显示结构 ------------------------------------------------
    def _rebuild_display(self, *, reset: bool) -> None:
        if reset:
            self.beginResetModel()
        self._display = {_ROOT_KEY: []}
        self._parents = {}
        self._roots = self._filter_children(self._source[_ROOT_KEY], None)
        if reset:
            self.endResetModel()

    def _filter_children(
        self, children: Sequence[TreeNode], parent: TreeNode | None
    ) -> list[TreeNode]:
        out: list[TreeNode] = []
        for node in children:
            kids = self._filter_children(node.children, node)
            if self._host._node_matches(node) or kids:
                self._display[id(node)] = kids
                self._parents[id(node)] = parent
                out.append(node)
        return out

    # -- QAbstractItemModel 实现 -----------------------------------------
    def index(self, row: int, column: int, parent: QModelIndex | None = None) -> QModelIndex:
        if parent is None or not parent.isValid():
            siblings = self._roots
        else:
            siblings = self._display.get(id(parent.internalPointer()), [])
        if 0 <= row < len(siblings):
            return self.createIndex(row, column, siblings[row])
        return QModelIndex()

    def parent(self, index: QModelIndex) -> QModelIndex:
        if not index.isValid():
            return QModelIndex()
        node = index.internalPointer()
        parent_node = self._parents.get(id(node))
        if parent_node is None:
            return QModelIndex()
        grandparent_node = self._parents.get(id(parent_node))
        siblings = (
            self._roots if grandparent_node is None else self._display.get(id(grandparent_node), [])
        )
        if parent_node in siblings:
            # 用「父节点自身」在其兄弟中的行号，而不是子节点的行号
            return self.createIndex(siblings.index(parent_node), 0, parent_node)
        return QModelIndex()

    def rowCount(self, parent: QModelIndex | None = None) -> int:
        if parent is None or not parent.isValid():
            return len(self._roots)
        return len(self._display.get(id(parent.internalPointer()), []))

    def columnCount(self, parent: QModelIndex | None = None) -> int:
        del parent
        return len(self._host._columns)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None
        node = index.internalPointer()
        column = self._host._columns[index.column()]
        if role in {Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.ToolTipRole}:
            return self._host.display_text(column.key, node.data.get(column.key))
        if role == Qt.ItemDataRole.UserRole:
            return node
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

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def hasChildren(self, parent: QModelIndex | None = None) -> bool:
        if parent is None or not parent.isValid():
            return bool(self._roots)
        node = parent.internalPointer()
        if self._host._loader is not None:
            return node.has_children
        return bool(self._display.get(id(node)))

    def canFetchMore(self, parent: QModelIndex | None = None) -> bool:
        if self._host._loader is None:
            return False
        node = None if (parent is None or not parent.isValid()) else parent.internalPointer()
        key = _ROOT_KEY if node is None else id(node)
        # 根已在构造时加载；其余节点只有尚未取过子节点时才需要取。
        return key not in self._source

    def fetchMore(self, parent: QModelIndex | None = None) -> None:
        if self._host._loader is None:
            return
        node = None if (parent is None or not parent.isValid()) else parent.internalPointer()
        key = _ROOT_KEY if node is None else id(node)
        if key in self._source:
            return
        children = list(self._host._loader(node))
        if node is not None:
            node.has_children = bool(children)
        first = self.rowCount(parent)
        last = first + len(children) - 1
        # 定向插入，不动整棵树，已展开的父节点保持展开。懒加载模式下不做筛选。
        if last >= first:
            self.beginInsertRows(parent if parent is not None else QModelIndex(), first, last)
        self._source[key] = list(children)
        for child in children:
            self._index_subtree(child)
        self._display[key] = list(children)
        if node is None:
            self._roots = list(children)
            self._parents.update({id(c): None for c in children})
        else:
            self._parents.update({id(c): node for c in children})
        if last >= first:
            self.endInsertRows()


class TreeView(QWidget):
    """层级结果视图：固定列或多列，按嵌套 ``TreeNode`` 展示。

    适合文件树、依赖树、大纲这类层级浏览。不负责编辑、分页或树表。
    """

    node_activated = Signal(object)
    selection_changed = Signal()

    def __init__(
        self,
        columns: Sequence[TreeColumn | str] | None = None,
        parent: QWidget | None = None,
        *,
        empty_title: str = "暂无数据",
        empty_hint: str = "运行任务后，结果会显示在这里。",
        child_loader: Callable[[TreeNode | None], Sequence[TreeNode]] | None = None,
    ) -> None:
        super().__init__(parent)
        self._columns = [self._normalize(item) for item in columns] if columns else []
        self._columns_locked = bool(self._columns)
        self._filter = ""
        self._loader = child_loader
        self._empty_title = empty_title
        self._empty_hint = empty_hint
        self._expanded: set[str] = set()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._model = _TreeModel(self)
        self._tree = QTreeView()
        self._tree.setModel(self._model)
        self._tree.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._tree.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tree.setUniformRowHeights(True)
        self._tree.setWordWrap(False)
        self._tree.setAccessibleName("树视图")
        self._tree.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self._tree.doubleClicked.connect(self._activate_index)
        selection = self._tree.selectionModel()
        if selection is not None:
            selection.selectionChanged.connect(self._on_selection_changed)
        self._tree.expanded.connect(self._on_expanded)
        self._tree.collapsed.connect(self._on_collapsed)

        self._empty = EmptyState(empty_title, empty_hint)
        self._stack = QStackedWidget()
        self._stack.addWidget(self._tree)
        self._stack.addWidget(self._empty)
        layout.addWidget(self._stack)
        self._busy = BusyOverlay(self)
        if self._columns:
            self._apply_headers()
        if self._loader is not None:
            self._model.load_source(list(self._loader(None)))
        self._sync_empty()

    @staticmethod
    def _normalize(item: TreeColumn | str) -> TreeColumn:
        return item if isinstance(item, TreeColumn) else TreeColumn(key=item)

    # -- 数据 --------------------------------------------------------------
    def set_columns(self, columns: Sequence[TreeColumn | str]) -> None:
        """固定列。之后 ``set_nodes`` / 懒加载不再按数据改列。"""

        self._columns_locked = True
        self._columns = [self._normalize(item) for item in columns]
        self._apply_headers()
        self._model._rebuild_display(reset=True)
        self._sync_empty()

    def set_nodes(self, nodes: Sequence[TreeNode]) -> None:
        """用完整的嵌套节点树替换内容。懒加载模式下不要用它。"""

        if self._loader is not None:
            raise RuntimeError("child_loader 模式下请用懒加载，不要调用 set_nodes")
        if not self._columns_locked:
            self._columns = self._columns_from_nodes(nodes)
            self._apply_headers()
        self._model.load_source(nodes)
        self._sync_empty()

    def clear(self) -> None:
        """清空所有节点。"""

        self._filter = ""
        self._model.load_source([])
        self._sync_empty()

    # -- 筛选 --------------------------------------------------------------
    def set_filter(self, query: str) -> None:
        """按各列展示文本做不区分大小写的包含筛选，并保留命中节点的祖先链。

        行被筛掉时选中随之消失；筛选清空后恢复。懒加载模式下只筛已加载的节点。
        """

        self._filter = query.strip()
        self._model._rebuild_display(reset=True)
        # 非懒加载才展开全部以露出命中项；懒加载模式若 expandAll 会触发全树抓取。
        if self._filter and self._loader is None:
            self._tree.expandAll()

    def _node_matches(self, node: TreeNode) -> bool:
        if not self._filter:
            return True
        needle = self._filter.casefold()
        return any(
            needle in str(self.display_text(column.key, node.data.get(column.key))).casefold()
            for column in self._columns
        )

    # -- 选中与激活 --------------------------------------------------------
    def selected_nodes(self) -> list[TreeNode]:
        """选中的节点列表（按视图顺序）。"""

        model = self._tree.selectionModel()
        if model is None:
            return []
        return [index.internalPointer() for index in model.selectedRows()]

    def context_menu(
        self, builder: Callable[[MenuTarget], Sequence[MenuAction] | None]
    ) -> QTreeView:
        """挂右键菜单，返回底层的 ``QTreeView``。

        ``builder`` 拿到命中节点的 ``MenuTarget``：``key`` 是节点 id，``data`` 是
        ``TreeNode``；右键落在空白处时 ``target.hit`` 为 ``False``。
        """

        return attach_context_menu(self, builder)  # type: ignore[return-value]

    def _context_menu_source(self) -> QWidget:
        return self._tree

    def _context_menu_target(self, pos: QPoint) -> MenuTarget | None:
        index = self._tree.indexAt(pos)
        if not index.isValid():
            return MenuTarget("tree", position=pos)
        node = index.internalPointer()
        if not isinstance(node, TreeNode):
            return None
        # 右键落在未选中的节点：先选中它，菜单里的「选中项」才和行为一致。
        if node not in self.selected_nodes():
            self.select_node(node.id)
        return MenuTarget("tree", key=node.id, data=node, position=pos)

    def select_node(self, node_id: str) -> None:
        """按节点 ``id`` 选中一个节点并设为当前项；找不到则清空选中。"""

        index = self._find_index(node_id)
        selection = self._tree.selectionModel()
        if selection is None:
            return
        if index.isValid():
            self._tree.setCurrentIndex(index)
            selection.select(
                index,
                (selection.SelectionFlag.ClearAndSelect | selection.SelectionFlag.Rows),
            )
        else:
            selection.clear()

    def expand_to(self, node_id: str) -> None:
        """展开节点的所有祖先，使其可见。

        只展开祖先、不展开节点自身：在刚展开父节点后立刻展开一个叶子节点，
        Qt 会把父节点收起，所以这里避免对末级节点调用 ``expand``。
        """

        chain: list[QModelIndex] = []
        index = self._find_index(node_id)
        while index.isValid():
            chain.append(index)
            index = index.parent()
        # chain[0] 是节点自身，chain[1:] 是祖先；自顶向下展开祖先即可让节点可见
        for item in reversed(chain[1:]):
            self._tree.expand(item)

    def expand_all(self) -> None:
        self._tree.expandAll()

    def collapse_all(self) -> None:
        self._tree.collapseAll()

    # -- 忙态 --------------------------------------------------------------
    def set_busy(self, busy: bool, message: str = "正在处理…") -> None:
        if busy:
            self._busy.show_busy(message)
        else:
            self._busy.hide_busy()

    # -- 子类可覆盖 --------------------------------------------------------
    def display_text(self, key: str, value: Any) -> str:
        """单元格展示文本。子类可覆盖以格式化日期、字节等。"""

        del key
        return "" if value is None else str(value)

    # -- 内部 --------------------------------------------------------------
    def _columns_from_nodes(self, nodes: Sequence[TreeNode]) -> list[TreeColumn]:
        if not nodes:
            return []
        keys: list[str] = []
        for node in nodes:
            for key in node.data:
                if key not in keys:
                    keys.append(key)
        return [TreeColumn(key=key) for key in keys]

    def _apply_headers(self) -> None:
        header = self._tree.header()
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

    def _find_index(self, node_id: str) -> QModelIndex:
        return self._search(QModelIndex(), node_id)

    def _search(self, parent: QModelIndex, node_id: str) -> QModelIndex:
        for row in range(self._model.rowCount(parent)):
            index = self._model.index(row, 0, parent)
            node = index.internalPointer()
            if node is not None and node.id == node_id:
                return index
            deeper = self._search(index, node_id)
            if deeper.isValid():
                return deeper
        return QModelIndex()

    def _activate_index(self, index: QModelIndex) -> None:
        node = index.internalPointer()
        if isinstance(node, TreeNode):
            self.node_activated.emit(node)

    def _on_selection_changed(self) -> None:
        self.selection_changed.emit()

    def _on_expanded(self, index: QModelIndex) -> None:
        node = index.internalPointer()
        if isinstance(node, TreeNode):
            self._expanded.add(node.id)

    def _on_collapsed(self, index: QModelIndex) -> None:
        node = index.internalPointer()
        if isinstance(node, TreeNode):
            self._expanded.discard(node.id)

    def _sync_empty(self) -> None:
        if self._model._roots:
            self._stack.setCurrentWidget(self._tree)
            return
        if self._filter:
            self._empty.set_copy("无匹配项", "试试别的关键字。")
        else:
            self._empty.set_copy(self._empty_title, self._empty_hint)
        self._stack.setCurrentWidget(self._empty)
