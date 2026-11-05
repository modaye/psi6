"""右键上下文菜单：描述渲染、勾选 / 单选、命中目标、换肤重画。"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QLabel, QMenu, QWidget
from pytestqt.qtbot import QtBot

from psi6.ui.context_menu import MenuAction, MenuTarget, build_menu
from psi6.ui.data_table import DataTable, TableColumn
from psi6.ui.tab_view import TabView
from psi6.ui.tree_view import TreeColumn, TreeNode, TreeView


class _Host(QWidget):
    """最小宿主：菜单要先有父控件才能画图标。"""


def _menu(specs, host) -> QMenu:
    return build_menu(specs, host=host)


# -- 描述 -> QMenu ----------------------------------------------------------


def test_separator_and_line_helper(qtbot: QtBot) -> None:
    host = _Host()
    qtbot.addWidget(host)
    menu = _menu(
        [
            MenuAction("打开"),
            MenuAction.line(),
            MenuAction("删除", dangerous=True),
        ],
        host,
    )
    assert [action.text() for action in menu.actions() if not action.isSeparator()] == [
        "打开",
        "删除",
    ]
    assert sum(1 for action in menu.actions() if action.isSeparator()) == 1


def test_leading_and_trailing_separators_are_dropped(qtbot: QtBot) -> None:
    host = _Host()
    qtbot.addWidget(host)
    menu = _menu(
        [MenuAction.line(), MenuAction("打开"), MenuAction.line()],
        host,
    )
    # 开头和结尾的分隔线没有视觉意义，直接省掉。
    assert all(not action.isSeparator() for action in menu.actions())
    assert len(menu.actions()) == 1


def test_duplicate_separators_collapse(qtbot: QtBot) -> None:
    host = _Host()
    qtbot.addWidget(host)
    menu = _menu(
        [MenuAction("A"), MenuAction.line(), MenuAction.line(), MenuAction("B")],
        host,
    )
    assert sum(1 for action in menu.actions() if action.isSeparator()) == 1


def test_callbacks_fire_without_arguments(qtbot: QtBot) -> None:
    host = _Host()
    qtbot.addWidget(host)
    calls: list[str] = []
    menu = _menu(
        [
            MenuAction("A", lambda: calls.append("a")),
            MenuAction("B", lambda: calls.append("b")),
        ],
        host,
    )
    for action in menu.actions():
        action.trigger()
    assert calls == ["a", "b"]


def test_disabled_action_does_not_fire(qtbot: QtBot) -> None:
    host = _Host()
    qtbot.addWidget(host)
    calls: list[str] = []
    menu = _menu([MenuAction("A", lambda: calls.append("a"), enabled=False)], host)
    action = menu.actions()[0]
    assert action.isEnabled() is False
    action.trigger()
    assert calls == []


def test_checkable_actions_render_their_state(qtbot: QtBot) -> None:
    host = _Host()
    qtbot.addWidget(host)
    menu = _menu(
        [
            MenuAction("显示列", checked=True),
            MenuAction("显示状态", checked=False),
            MenuAction("普通项"),
        ],
        host,
    )
    on, off, plain = menu.actions()
    assert on.isCheckable() and on.isChecked()
    assert off.isCheckable() and not off.isChecked()
    assert not plain.isCheckable()


def test_group_actions_are_exclusive(qtbot: QtBot) -> None:
    host = _Host()
    qtbot.addWidget(host)
    menu = _menu(
        [
            MenuAction("按名称", checked=True, group="sort"),
            MenuAction("按时间", checked=False, group="sort"),
            MenuAction("刷新"),
        ],
        host,
    )
    first, second, _ = menu.actions()
    second.trigger()
    # 互斥组内点一项，另一项自动取消。
    assert second.isChecked()
    assert not first.isChecked()


def test_group_gets_its_own_separator(qtbot: QtBot) -> None:
    host = _Host()
    qtbot.addWidget(host)
    menu = _menu(
        [
            MenuAction("复制"),
            MenuAction("按名称", checked=True, group="sort"),
            MenuAction("按时间", checked=False, group="sort"),
        ],
        host,
    )
    texts = [None if action.isSeparator() else action.text() for action in menu.actions()]
    assert texts == ["复制", None, "按名称", "按时间"]
    assert menu.property("psi6HasMenuGroup") is True


def test_shortcut_is_hint_only(qtbot: QtBot) -> None:
    host = _Host()
    qtbot.addWidget(host)
    menu = _menu([MenuAction("复制", shortcut="Ctrl+C")], host)
    action = menu.actions()[0]
    # 只做展示提示，不注册全局快捷键，避免同一动作出现在多个菜单里冲突。
    assert action.shortcut().toString() == "Ctrl+C"


def test_icon_is_themed_and_follows_token(qtbot: QtBot, tmp_path: Path) -> None:
    from psi6.runtime.app import App

    App("psi6-menu-icon", theme="light", config_root=tmp_path)
    host = _Host()
    qtbot.addWidget(host)
    menu = _menu([MenuAction("删除", icon="trash", dangerous=True)], host)
    action = menu.actions()[0]
    assert not action.icon().isNull()
    assert action.property("psi6Icon") == "trash"
    assert action.property("psi6Dangerous") is True


def test_empty_specs_give_an_empty_menu(qtbot: QtBot) -> None:
    host = _Host()
    qtbot.addWidget(host)
    menu = _menu([], host)
    assert menu.actions() == []


def test_title_becomes_the_menu_title(qtbot: QtBot) -> None:
    host = _Host()
    qtbot.addWidget(host)
    menu = build_menu([MenuAction("A")], host=host, title="行操作")
    assert menu.title() == "行操作"


# -- MenuTarget -------------------------------------------------------------


def test_target_hit_reflects_key() -> None:
    assert MenuTarget("table", key=3, data={"id": 3}).hit is True
    assert MenuTarget("table").hit is False


# -- DataTable 挂载 ---------------------------------------------------------


def test_data_table_menu_reports_the_hit_row(qtbot: QtBot) -> None:
    table = DataTable([TableColumn("id", "id"), TableColumn("name", "名称", stretch=True)])
    qtbot.addWidget(table)
    table.resize(400, 300)
    table.set_rows({"id": index, "name": f"r{index}"} for index in range(20))
    table.show()

    seen: list[MenuTarget] = []
    view = table.context_menu(lambda target: seen.append(target) or [MenuAction("复制")])
    assert view.contextMenuPolicy() == Qt.ContextMenuPolicy.CustomContextMenu

    rect = view.visualRect(view.model().index(2, 0))
    pos = rect.center()
    target = table._context_menu_target(pos)
    assert target is not None
    assert target.kind == "table"
    assert target.key == 2
    assert target.data["name"] == "r2"


def test_data_table_right_click_selects_the_row(qtbot: QtBot) -> None:
    table = DataTable([TableColumn("id", "id"), TableColumn("name", "名称", stretch=True)])
    qtbot.addWidget(table)
    table.resize(400, 300)
    table.set_rows({"id": index, "name": f"r{index}"} for index in range(20))
    table.show()

    view = table._table
    pos = view.visualRect(view.model().index(4, 0)).center()
    table._context_menu_target(pos)
    # 右键落在未选中行：先选中，菜单里的「选中项」才和行为一致。
    assert table.selected_indexes() == [4]


def test_data_table_blank_area_has_no_hit(qtbot: QtBot) -> None:
    table = DataTable([TableColumn("id", "id"), TableColumn("name", "名称", stretch=True)])
    qtbot.addWidget(table)
    table.resize(400, 300)
    table.set_rows([{"id": 0, "name": "r0"}])
    table.show()

    target = table._context_menu_target(QPoint(10, 290))
    assert target is not None
    assert target.hit is False


# -- TreeView 挂载 ----------------------------------------------------------


def _tree(qtbot: QtBot) -> TreeView:
    tree = TreeView([TreeColumn("name", "名称", stretch=True)])
    qtbot.addWidget(tree)
    tree.resize(360, 260)
    root = TreeNode(id="src", data={"name": "src"})
    root.children = [
        TreeNode(id="a", data={"name": "a.py"}),
        TreeNode(id="b", data={"name": "b.py"}),
    ]
    tree.set_nodes([root])
    tree.show()
    return tree


def test_tree_view_menu_reports_the_hit_node(qtbot: QtBot) -> None:
    tree = _tree(qtbot)
    out = tree._tree
    view = tree.context_menu(lambda target: [MenuAction("打开")])
    assert view.contextMenuPolicy() == Qt.ContextMenuPolicy.CustomContextMenu

    tree.expand_to("a")
    index = tree._find_index("a")
    pos = out.visualRect(index).center()
    target = tree._context_menu_target(pos)
    assert target is not None
    assert target.kind == "tree"
    assert target.key == "a"
    assert target.data.id == "a"


def test_tree_view_right_click_selects_the_node(qtbot: QtBot) -> None:
    tree = _tree(qtbot)
    tree.expand_to("b")
    pos = tree._tree.visualRect(tree._find_index("b")).center()
    tree._context_menu_target(pos)
    assert [node.id for node in tree.selected_nodes()] == ["b"]


# -- TabView 挂载 -----------------------------------------------------------


def _tabs(qtbot: QtBot) -> TabView:
    tabs = TabView()
    qtbot.addWidget(tabs)
    tabs.resize(420, 280)
    for key in ("a", "b", "c"):
        tabs.add_tab(key, f"文档 {key.upper()}", QLabel(key))
    tabs.show()
    return tabs


def test_tab_view_menu_reports_the_hit_tab(qtbot: QtBot) -> None:
    tabs = _tabs(qtbot)
    bar = tabs.context_menu(lambda target: [MenuAction("关闭")])
    assert bar.contextMenuPolicy() == Qt.ContextMenuPolicy.CustomContextMenu

    rect = bar.tabRect(1)
    target = tabs._context_menu_target(rect.center())
    assert target is not None
    assert target.kind == "tabs"
    assert target.key == "b"
    assert target.data == "文档 B"


def test_tab_view_right_click_switches_to_the_tab(qtbot: QtBot) -> None:
    tabs = _tabs(qtbot)
    tabs.set_current("a")
    tabs._context_menu_target(tabs._tabs.tabBar().tabRect(2).center())
    assert tabs.current_key() == "c"


def test_tab_view_blank_bar_falls_back_to_current(qtbot: QtBot) -> None:
    tabs = _tabs(qtbot)
    tabs.set_current("b")
    # 页签条右侧空白：退回当前页签，不是「没命中」。
    target = tabs._context_menu_target(QPoint(tabs.width() - 4, 8))
    assert target is not None
    assert target.key == "b"


def test_tab_view_without_tabs_reports_no_hit(qtbot: QtBot) -> None:
    tabs = TabView()
    qtbot.addWidget(tabs)
    tabs.resize(420, 280)
    tabs.show()
    target = tabs._context_menu_target(QPoint(20, 8))
    assert target is not None
    assert target.hit is False


@pytest.mark.parametrize("kind", ["table", "tree", "tabs"])
def test_builder_returning_none_means_no_menu(qtbot: QtBot, kind: str) -> None:
    from psi6.ui.context_menu import menu_for

    host = _Host()
    qtbot.addWidget(host)
    assert menu_for(MenuTarget(kind), lambda _target: None, host=host) is None
    assert menu_for(MenuTarget(kind), lambda _target: [], host=host) is None


# -- 换肤 -------------------------------------------------------------------


def _dominant_color(image) -> str:
    """取不透明像素里出现最多的颜色。"""

    counts: dict[str, int] = {}
    for y in range(image.height()):
        for x in range(image.width()):
            color = image.pixelColor(x, y)
            if color.alpha() > 32:
                counts[color.name()] = counts.get(color.name(), 0) + 1
    return max(counts, key=counts.get) if counts else "none"


def test_menu_icon_is_recolored_after_theme_change(qtbot: QtBot, tmp_path: Path) -> None:
    """换肤后菜单图标要跟着重画，否则深色皮肤下会看不清。"""

    from PySide6.QtCore import QSize

    from psi6.runtime.app import App

    app = App("psi6-menu-recolor", theme="light", config_root=tmp_path)
    host = _Host()
    qtbot.addWidget(host)
    menu = _menu([MenuAction("删除", icon="trash", dangerous=True)], host)
    action = menu.actions()[0]

    before = _dominant_color(action.icon().pixmap(QSize(16, 16)).toImage())
    app.set_theme("dark")

    # 图标重画走 PaletteChange，等它落地而不是手动 pump 事件。
    qtbot.waitUntil(
        lambda: _dominant_color(action.icon().pixmap(QSize(16, 16)).toImage()) != before,
        timeout=2000,
    )
    after = _dominant_color(action.icon().pixmap(QSize(16, 16)).toImage())
    assert after != "none"
