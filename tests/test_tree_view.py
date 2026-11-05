"""TreeView 层级节点与选择。"""

from __future__ import annotations

from PySide6.QtCore import QModelIndex, Qt
from pytestqt.qtbot import QtBot

from psi6.ui.tree_view import TreeColumn, TreeNode, TreeView


def _root() -> QModelIndex:
    return QModelIndex()


def _sample_tree() -> list[TreeNode]:
    return [
        TreeNode(
            id="src",
            data={"name": "src", "kind": "dir"},
            children=[
                TreeNode(id="a", data={"name": "a.py", "kind": "file"}),
                TreeNode(id="b", data={"name": "b.py", "kind": "file"}),
            ],
        ),
        TreeNode(id="docs", data={"name": "docs", "kind": "dir"}),
    ]


def test_tree_infers_columns_and_shows_nodes(qtbot: QtBot) -> None:
    tree = TreeView()
    qtbot.addWidget(tree)
    tree.set_nodes(_sample_tree())
    assert tree._model.rowCount() == 2
    src = tree._model.index(0, 0, _root())
    assert tree._model.rowCount(src) == 2


def test_fixed_columns_survive_clear(qtbot: QtBot) -> None:
    tree = TreeView([TreeColumn("name", "名称")])
    qtbot.addWidget(tree)
    tree.set_nodes(_sample_tree())
    tree.clear()
    assert tree._model.rowCount() == 0
    tree.set_nodes(_sample_tree())
    assert tree._model.rowCount() == 2
    assert tree._model.headerData(0, Qt.Orientation.Horizontal) == "名称"


def test_select_and_activate_node(qtbot: QtBot) -> None:
    tree = TreeView([TreeColumn("name", "名称", stretch=True)])
    qtbot.addWidget(tree)
    tree.set_nodes(_sample_tree())
    activated: list[TreeNode] = []
    tree.node_activated.connect(activated.append)
    tree.select_node("b")
    assert [node.id for node in tree.selected_nodes()] == ["b"]
    tree._tree.doubleClicked.emit(tree._find_index("b"))
    assert activated and activated[0].id == "b"


def test_expand_collapse_and_expand_to(qtbot: QtBot) -> None:
    tree = TreeView()
    qtbot.addWidget(tree)
    tree.set_nodes(_sample_tree())
    src_index = tree._find_index("src")
    tree._tree.expand(src_index)
    assert tree._tree.isExpanded(src_index)
    tree.collapse_all()
    assert not tree._tree.isExpanded(src_index)
    tree.expand_to("b")
    assert tree._tree.isExpanded(src_index)


def test_filter_keeps_ancestors(qtbot: QtBot) -> None:
    tree = TreeView([TreeColumn("name")])
    qtbot.addWidget(tree)
    tree.set_nodes(_sample_tree())
    tree.set_filter("b.py")
    assert tree._model.rowCount() == 1
    root = tree._model.index(0, 0, _root())
    assert root.internalPointer().id == "src"
    assert tree._model.rowCount(root) == 1
    assert tree._model.index(0, 0, root).internalPointer().id == "b"
    tree.set_filter("")


def test_filter_hides_unmatched_subtree(qtbot: QtBot) -> None:
    tree = TreeView([TreeColumn("name")])
    qtbot.addWidget(tree)
    tree.set_nodes(_sample_tree())
    tree.set_filter("docs")
    assert tree._model.rowCount() == 1
    assert tree._model.index(0, 0, _root()).internalPointer().id == "docs"


def test_display_text_hook(qtbot: QtBot) -> None:
    class KindTree(TreeView):
        def display_text(self, key: str, value: object) -> str:
            if key == "kind":
                return str(value).upper()
            return super().display_text(key, value)

    tree = KindTree([TreeColumn("name"), TreeColumn("kind")])
    qtbot.addWidget(tree)
    tree.set_nodes(_sample_tree())
    docs = tree._find_index("docs")
    assert tree._model.data(tree._model.index(docs.row(), 1, docs.parent())) == "DIR"


def test_empty_state_shows_without_nodes(qtbot: QtBot) -> None:
    tree = TreeView()
    qtbot.addWidget(tree)
    assert tree._stack.currentWidget() is tree._empty
    tree.set_nodes(_sample_tree())
    assert tree._stack.currentWidget() is tree._tree


def test_lazy_loading_fetches_on_expand(qtbot: QtBot) -> None:
    calls: list[str | None] = []

    def loader(node: TreeNode | None) -> list[TreeNode]:
        calls.append(None if node is None else node.id)
        if node is None:
            return [TreeNode(id="r", data={"name": "root"}, has_children=True)]
        if node.id == "r":
            return [
                TreeNode(id="c1", data={"name": "child1"}),
                TreeNode(id="c2", data={"name": "child2"}),
            ]
        return []

    tree = TreeView([TreeColumn("name")], child_loader=loader)
    qtbot.addWidget(tree)
    assert tree._model.rowCount() == 1
    root_index = tree._model.index(0, 0, _root())
    assert tree._model.hasChildren(root_index)
    assert tree._model.rowCount(root_index) == 0
    tree._tree.expand(root_index)
    # fetchMore 在视图重排时（事件循环里）触发，不是 expand 同步调用
    qtbot.waitUntil(lambda: tree._model.rowCount(root_index) == 2, timeout=2000)
    assert "r" in calls


def test_set_nodes_rejects_in_lazy_mode(qtbot: QtBot) -> None:
    tree = TreeView(child_loader=lambda n: [])
    qtbot.addWidget(tree)
    try:
        tree.set_nodes(_sample_tree())
    except RuntimeError:
        return
    raise AssertionError("懒加载模式下 set_nodes 应当报错")


def test_deep_hierarchy_parent_navigation(qtbot: QtBot) -> None:
    deep = [
        TreeNode(
            id="g",
            data={"name": "g"},
            children=[
                TreeNode(
                    id="src",
                    data={"name": "src"},
                    children=[
                        TreeNode(id="a", data={"name": "a.py"}),
                        TreeNode(id="b", data={"name": "b.py"}),
                        TreeNode(
                            id="pkg",
                            data={"name": "pkg"},
                            children=[TreeNode(id="c", data={"name": "c.py"})],
                        ),
                    ],
                )
            ],
        )
    ]
    tree = TreeView([TreeColumn("name")])
    qtbot.addWidget(tree)
    tree.set_nodes(deep)
    g_index = tree._model.index(0, 0, _root())
    assert tree._model.rowCount(g_index) == 1  # g -> src
    src = tree._model.index(0, 0, g_index)
    assert tree._model.rowCount(src) == 3  # src -> a, b, pkg
    pkg = tree._model.index(2, 0, src)
    assert tree._model.rowCount(pkg) == 1  # pkg -> c
    c = tree._model.index(0, 0, pkg)
    # 父链回溯：c -> pkg -> src -> g -> 无
    assert c.parent().internalPointer().id == "pkg"
    assert c.parent().parent().internalPointer().id == "src"
    assert c.parent().parent().parent().internalPointer().id == "g"
    assert not c.parent().parent().parent().parent().isValid()
    # expand_to 展开所有祖先
    tree.expand_to("c")
    assert tree._tree.isExpanded(g_index)
    assert tree._tree.isExpanded(src)
    assert tree._tree.isExpanded(pkg)
