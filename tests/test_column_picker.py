"""列管理：显隐、顺序、持久化，以及与 DataTable 的配合。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPoint
from pytestqt.qtbot import QtBot

from psi6.runtime.config import ConfigStore
from psi6.ui.column_picker import ColumnPicker, ColumnState, column_toggle_menu
from psi6.ui.context_menu import MenuAction
from psi6.ui.data_table import DataTable, TableColumn


def _picker(qtbot: QtBot) -> ColumnPicker:
    picker = ColumnPicker()
    qtbot.addWidget(picker)
    picker.resize(240, 320)
    picker.show()
    return picker


def _table(qtbot: QtBot) -> DataTable:
    table = DataTable(
        [
            TableColumn("id", "编号"),
            TableColumn("name", "名称", stretch=True),
            TableColumn("state", "状态"),
        ]
    )
    qtbot.addWidget(table)
    table.resize(520, 260)
    table.set_rows(
        [{"id": 1, "name": "甲", "state": "就绪"}, {"id": 2, "name": "乙", "state": "等待"}]
    )
    table.show()
    return table


# -- ColumnPicker -----------------------------------------------------------


def test_set_columns_emits_visible_keys(qtbot: QtBot) -> None:
    picker = _picker(qtbot)
    seen: list[list[str]] = []
    picker.columns_changed.connect(lambda keys: seen.append(list(keys)))
    picker.set_columns(["id", "name", "state"])
    assert seen == [["id", "name", "state"]]
    assert picker.visible_columns() == ["id", "name", "state"]


def test_unchecking_hides_a_column(qtbot: QtBot) -> None:
    picker = _picker(qtbot)
    picker.set_columns(["id", "name", "state"])
    seen: list[list[str]] = []
    picker.columns_changed.connect(lambda keys: seen.append(list(keys)))
    picker.set_visible("name", False)
    assert picker.visible_columns() == ["id", "state"]
    assert seen == [["id", "state"]]


def test_hidden_column_keeps_its_place(qtbot: QtBot) -> None:
    picker = _picker(qtbot)
    picker.set_columns(["id", "name", "state"])
    picker.set_visible("name", False)
    # 隐藏后仍然保留原来的相对位置，重新显示会回到原处。
    assert [column.key for column in picker.columns()] == ["id", "name", "state"]
    picker.set_visible("name", True)
    assert picker.visible_columns() == ["id", "name", "state"]


def test_required_column_cannot_be_hidden(qtbot: QtBot) -> None:
    picker = _picker(qtbot)
    picker.set_columns([ColumnState("id", "编号", required=True), ColumnState("name", "名称")])
    picker.set_visible("id", False)
    assert "id" in picker.visible_columns()


def test_show_all_restores_every_column(qtbot: QtBot) -> None:
    picker = _picker(qtbot)
    picker.set_columns(["id", "name", "state"])
    picker.set_visible("name", False)
    picker.set_visible("state", False)
    picker.show_all()
    assert picker.visible_columns() == ["id", "name", "state"]


def test_move_reorders_columns(qtbot: QtBot) -> None:
    picker = _picker(qtbot)
    picker.set_columns(["id", "name", "state"])
    picker.move_column("state", -1)
    assert picker.visible_columns() == ["id", "state", "name"]


def test_move_at_boundary_is_ignored(qtbot: QtBot) -> None:
    picker = _picker(qtbot)
    picker.set_columns(["id", "name", "state"])
    picker.move_column("id", -1)
    assert picker.visible_columns() == ["id", "name", "state"]
    picker.move_column("state", 1)
    assert picker.visible_columns() == ["id", "name", "state"]


def test_move_unknown_key_is_ignored(qtbot: QtBot) -> None:
    picker = _picker(qtbot)
    picker.set_columns(["id", "name"])
    picker.move_column("ghost", 1)
    assert picker.visible_columns() == ["id", "name"]


def test_empty_columns_show_the_empty_state(qtbot: QtBot) -> None:
    picker = _picker(qtbot)
    picker.set_columns([])
    assert picker.visible_columns() == []
    assert picker._empty.isVisible() is True


def test_titles_are_used_when_given(qtbot: QtBot) -> None:
    picker = _picker(qtbot)
    picker.set_columns(["id", "name"], titles={"id": "编号", "name": "名称"})
    titles = [column.title for column in picker.columns()]
    assert titles == ["编号", "名称"]


# -- 状态往返 ---------------------------------------------------------------


def test_state_round_trip(qtbot: QtBot) -> None:
    picker = _picker(qtbot)
    picker.set_columns(["id", "name", "state"])
    picker.set_visible("name", False)
    picker.move_column("state", -1)
    state = picker.state()

    other = _picker(qtbot)
    other.set_columns(["id", "name", "state"])
    other.set_state(state)
    assert other.visible_columns() == ["id", "state"]
    assert [column.key for column in other.columns()] == ["id", "state", "name"]


def test_state_ignores_unknown_keys(qtbot: QtBot) -> None:
    picker = _picker(qtbot)
    picker.set_columns(["id", "name"])
    picker.set_state({"columns": [{"key": "ghost", "visible": False}, {"key": "id"}]})
    # 未知 key 跳过；文件里没提到的 name 保持原样（可见），不会被顺带隐藏。
    assert picker.visible_columns() == ["id", "name"]


def test_state_keeps_columns_missing_from_the_file(qtbot: QtBot) -> None:
    picker = _picker(qtbot)
    picker.set_columns(["id", "name", "state"])
    picker.set_state({"columns": [{"key": "name", "visible": False}]})
    # 文件里没写的列保持原样，不会因为少写就消失。
    assert picker.visible_columns() == ["id", "state"]
    assert [column.key for column in picker.columns()] == ["id", "name", "state"]


def test_state_with_bad_payload_is_ignored(qtbot: QtBot) -> None:
    picker = _picker(qtbot)
    picker.set_columns(["id", "name"])
    before = picker.visible_columns()
    picker.set_state({"columns": "not-a-list"})
    picker.set_state({})
    assert picker.visible_columns() == before


def test_save_and_restore_through_config_store(qtbot: QtBot, tmp_path: Path) -> None:
    store = ConfigStore(tmp_path)
    picker = _picker(qtbot)
    picker.set_columns(["id", "name", "state"])
    picker.set_visible("state", False)
    picker.save_state(store, "demo")

    other = _picker(qtbot)
    other.set_columns(["id", "name", "state"])
    assert other.restore_state(store, "demo") is True
    assert other.visible_columns() == ["id", "name"]


def test_restore_without_file_returns_false(qtbot: QtBot, tmp_path: Path) -> None:
    store = ConfigStore(tmp_path)
    picker = _picker(qtbot)
    picker.set_columns(["id"])
    assert picker.restore_state(store, "missing") is False


def test_state_file_name_can_be_overridden(qtbot: QtBot, tmp_path: Path) -> None:
    store = ConfigStore(tmp_path)
    picker = ColumnPicker(state_file="custom.json")
    qtbot.addWidget(picker)
    picker.set_columns(["id", "name"])
    picker.save_state(store, "demo")
    assert (tmp_path / "demo" / "custom.json").exists()


# -- 与 DataTable 配合 ------------------------------------------------------


def test_table_visible_columns_reflects_the_view(qtbot: QtBot) -> None:
    table = _table(qtbot)
    assert table.visible_columns() == ["id", "name", "state"]


def test_set_visible_columns_hides_and_reorders(qtbot: QtBot) -> None:
    table = _table(qtbot)
    table.set_visible_columns(["state", "id"])
    assert table.visible_columns() == ["state", "id"]
    assert (
        table._table.isColumnHidden(
            table._columns.index(next(column for column in table.columns() if column.key == "name"))
        )
        is True
    )


def test_hidden_columns_are_kept_in_the_column_list(qtbot: QtBot) -> None:
    table = _table(qtbot)
    table.set_visible_columns(["id"])
    # 隐藏的列不从列定义里删掉：cell_text 的列号语义保持不变。
    assert [column.key for column in table.columns()] == ["id", "name", "state"]


def test_cell_text_keeps_working_after_hiding(qtbot: QtBot) -> None:
    table = _table(qtbot)
    table.set_visible_columns(["id"])
    assert table.cell_text(0, 1) == "甲"
    assert table.cell_text(1, 2) == "等待"


def test_visibility_survives_a_data_refresh(qtbot: QtBot) -> None:
    table = _table(qtbot)
    table.set_visible_columns(["name", "id"])
    table.set_rows([{"id": 9, "name": "丙", "state": "失败"}])
    # 数据刷新后列管理的显隐与顺序继续有效。
    assert table.visible_columns() == ["name", "id"]


def test_picker_drives_the_table(qtbot: QtBot) -> None:
    table = _table(qtbot)
    picker = _picker(qtbot)
    picker.set_columns(table.columns())
    picker.columns_changed.connect(table.set_visible_columns)

    picker.set_visible("state", False)
    assert table.visible_columns() == ["id", "name"]

    picker.move_column("name", -1)
    assert table.visible_columns() == ["name", "id"]


def test_picker_accepts_table_columns_directly(qtbot: QtBot) -> None:
    """``DataTable`` 的 ``TableColumn`` 能直接传进来，不用手工转 key。"""

    table = _table(qtbot)
    picker = _picker(qtbot)
    picker.set_columns(table.columns())
    assert [column.key for column in picker.columns()] == ["id", "name", "state"]
    assert [column.title for column in picker.columns()] == ["编号", "名称", "状态"]


# -- 列头右键菜单 -----------------------------------------------------------


def test_column_header_menu_reports_the_hit_column(qtbot: QtBot) -> None:
    table = _table(qtbot)
    header = table.column_menu(lambda target: [MenuAction("固定此列")])
    assert header is table._table.horizontalHeader()

    # 用 section 的视口位置算列边界：QHeaderView.visualRect 要的是 model index，
    # 那是数据区的列，不是表头列。
    start = header.sectionViewportPosition(1)
    width = header.sectionSize(1)
    target = table._column_menu_target(QPoint(start + width // 2, 4))
    assert target is not None
    assert target.kind == "columns"
    assert target.key == "name"


def test_column_header_menu_on_blank_area_has_no_hit(qtbot: QtBot) -> None:
    table = _table(qtbot)
    header = table._table.horizontalHeader()
    # 表头右侧空白：在最后一列之后。
    blank = QPoint(header.sectionViewportPosition(2) + header.sectionSize(2) + 10, 4)
    target = table._column_menu_target(blank)
    assert target is not None
    assert target.hit is False


def test_column_toggle_menu_lists_all_columns(qtbot: QtBot) -> None:
    items = column_toggle_menu(
        ["id", "name", "state"], ["id", "state"], on_toggle=lambda _k, _v: None
    )
    assert [item.label for item in items] == ["id", "name", "state"]
    assert items[0].checked is True
    assert items[1].checked is False


def test_column_toggle_menu_calls_back_with_the_new_state(qtbot: QtBot) -> None:
    calls: list[tuple[str, bool]] = []
    items = column_toggle_menu(
        ["id", "name"], ["id"], on_toggle=lambda key, value: calls.append((key, value))
    )
    items[1].callback()
    # 原来不可见，点一下变成可见。
    assert calls == [("name", True)]


def test_required_column_is_not_toggleable(qtbot: QtBot) -> None:
    items = column_toggle_menu(
        [ColumnState("id", "编号", required=True), ColumnState("name", "名称")],
        ["id", "name"],
        on_toggle=lambda _k, _v: None,
    )
    # 必显列不给勾选框，用不可点的普通项表达「必须在」。
    assert items[0].checked is None
    assert items[0].enabled is False


def test_picker_keeps_qwidget_move(qtbot: QtBot) -> None:
    """列排序不能覆盖 ``QWidget.move()``，否则布局里的 ``widget.move(x, y)`` 会走偏。"""

    picker = _picker(qtbot)
    picker.set_columns(["id", "name"])
    # QWidget.move(int, int) 仍是 Qt 那个：移动自己的位置，而不是改列顺序。
    picker.move(11, 22)
    assert (picker.x(), picker.y()) == (11, 22)
    assert picker.visible_columns() == ["id", "name"]
