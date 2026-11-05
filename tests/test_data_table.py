"""DataTable 行记录与选择。"""

from __future__ import annotations

from pydantic import BaseModel
from pytestqt.qtbot import QtBot

from psi6.ui.data_table import DataTable, TableColumn


class Row(BaseModel):
    name: str
    size: int


def test_data_table_from_models(qtbot: QtBot) -> None:
    table = DataTable(
        [
            TableColumn("name", "名称", stretch=True),
            TableColumn("size", "大小"),
        ]
    )
    qtbot.addWidget(table)
    table.set_rows([Row(name="a.txt", size=3), Row(name="b.txt", size=8)])
    assert table.rows()[1]["name"] == "b.txt"
    table.select_row(1)
    assert table.selected_rows()[0]["size"] == 8


def test_inferred_columns_reset_when_the_next_rows_change(qtbot: QtBot) -> None:
    table = DataTable()
    qtbot.addWidget(table)
    table.set_rows([{"a": 1}])
    copied = table.rows()
    copied[0]["a"] = 9
    assert table.rows()[0]["a"] == 1
    table.set_filter("1")
    visible = table.visible_rows()
    visible[0]["a"] = 8
    assert table.visible_rows()[0]["a"] == 1
    table.set_filter("")
    table.clear()
    table.set_rows([{"b": 2}])
    assert table.rows() == [{"b": 2}]
    assert table.cell_text(0, 0) == "2"


def test_fixed_columns_survive_clear(qtbot: QtBot) -> None:
    table = DataTable(["a"])
    qtbot.addWidget(table)
    table.set_rows([{"a": 1}])
    table.clear()
    table.set_rows([{"b": 2}])
    assert table.cell_text(0, 0) == ""
    assert table.rows() == [{"b": 2}]


def test_data_table_infers_columns(qtbot: QtBot) -> None:
    table = DataTable()
    qtbot.addWidget(table)
    table.set_rows([{"id": 1, "title": "x"}])
    assert table.rows()[0]["id"] == 1
    table.clear()
    assert table.rows() == []


class SizeTable(DataTable):
    def display_text(self, key: str, value: object) -> str:
        if key == "size":
            return f"{value} B"
        return super().display_text(key, value)


def test_sort_reorders_visible_rows_and_keeps_source_order(qtbot: QtBot) -> None:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QHeaderView

    table = DataTable(("name", "n"))
    qtbot.addWidget(table)
    table.set_rows(
        [
            {"name": "b", "n": 2},
            {"name": "a", "n": 1},
            {"name": "", "n": None},
            {"name": "c", "n": 3},
        ]
    )
    table.set_filter("a")
    table.sort_by("name")
    assert [row["name"] for row in table.rows()] == ["b", "a", "", "c"]
    assert [row["name"] for row in table.visible_rows()] == ["a"]
    table.set_filter("")
    header = next(
        item
        for item in table.findChildren(QHeaderView)
        if item.orientation() == Qt.Orientation.Horizontal
    )
    header.sectionClicked.emit(1)
    assert [row["n"] for row in table.visible_rows()] == [1, 2, 3, None]
    header.sectionClicked.emit(1)
    assert [row["n"] for row in table.visible_rows()] == [3, 2, 1, None]
    header.sectionClicked.emit(1)
    assert [row["n"] for row in table.visible_rows()] == [2, 1, None, 3]
    assert not header.isSortIndicatorShown()


def test_sort_mixed_types_does_not_crash(qtbot: QtBot) -> None:
    table = DataTable(["x"])
    qtbot.addWidget(table)
    table.set_rows([{"x": 2}, {"x": "a"}, {"x": 1}, {"x": ""}])
    table.sort_by("x")
    assert [row["x"] for row in table.visible_rows()] == [1, 2, "a", ""]
    table.sort_by("x", descending=True)
    assert [row["x"] for row in table.visible_rows()] == ["a", 2, 1, ""]


def test_data_table_display_text_hook(qtbot: QtBot) -> None:
    table = SizeTable([TableColumn("name", "名称"), TableColumn("size", "大小")])
    qtbot.addWidget(table)
    table.set_rows([{"name": "a.txt", "size": 3}])
    assert table.cell_text(0, 1) == "3 B"


def test_data_table_model_scales_without_items(qtbot: QtBot) -> None:
    table = DataTable(["id", "name"])
    qtbot.addWidget(table)
    table.set_rows({"id": index, "name": f"r{index}"} for index in range(4000))
    assert len(table.rows()) == 4000
    assert table.cell_text(0, 0) == "0"
    assert table.cell_text(3999, 1) == "r3999"
    table.set_filter("r3999")
    assert len(table.visible_rows()) == 1


def test_sort_and_filter_keep_selection_and_current_row(qtbot: QtBot) -> None:
    from PySide6.QtWidgets import QTableView

    table = DataTable(["name", "n"])
    qtbot.addWidget(table)
    table.set_rows([{"name": "b", "n": 2}, {"name": "a", "n": 1}, {"name": "c", "n": 3}])
    table.select_row(1)
    view = table.findChild(QTableView)
    assert view is not None
    assert view.currentIndex().row() == 1
    table.sort_by("name")
    assert table.selected_rows() == [{"name": "a", "n": 1}]
    assert view.currentIndex().row() == 0
    table.set_filter("a")
    assert table.selected_rows() == [{"name": "a", "n": 1}]
    assert view.currentIndex().row() == 0


def test_scroll_position_survives_sort(qtbot: QtBot) -> None:
    from PySide6.QtWidgets import QTableView

    table = DataTable(["n"])
    qtbot.addWidget(table)
    table.resize(240, 160)
    table.set_rows([{"n": index} for index in range(200)])
    table.show()
    view = table.findChild(QTableView)
    assert view is not None
    bar = view.verticalScrollBar()
    qtbot.waitUntil(lambda: bar.maximum() > 20, timeout=2000)
    bar.setValue(12)
    table.sort_by("n", descending=True)
    assert bar.value() == 12


def test_filter_matches_display_text(qtbot: QtBot) -> None:
    table = SizeTable([TableColumn("name", "名称"), TableColumn("size", "大小")])
    qtbot.addWidget(table)
    table.set_rows([{"name": "a.txt", "size": 3}, {"name": "b.txt", "size": 8}])
    table.set_filter("3 b")
    assert table.visible_rows() == [{"name": "a.txt", "size": 3}]


def test_double_click_emits_visible_index_and_record_copy(qtbot: QtBot) -> None:
    from PySide6.QtWidgets import QTableView

    table = DataTable(["name"])
    qtbot.addWidget(table)
    table.set_rows([{"name": "a"}, {"name": "b"}])
    view = table.findChild(QTableView)
    assert view is not None
    indexes: list[int] = []
    records: list[dict[str, object]] = []
    table.row_activated.connect(indexes.append)
    table.record_activated.connect(records.append)
    view.doubleClicked.emit(view.model().index(1, 0))
    assert indexes == [1]
    assert records == [{"name": "b"}]
    records[0]["name"] = "changed"
    assert table.rows() == [{"name": "a"}, {"name": "b"}]
    table.set_filter("b")
    view.doubleClicked.emit(view.model().index(0, 0))
    assert indexes == [1, 0]
    assert records[1] == {"name": "b"}


# --- 增量渲染（fetchMore）---


def test_model_publishes_rows_in_batches(qtbot: QtBot) -> None:
    from PySide6.QtCore import QModelIndex

    table = DataTable(["id", "name"])
    qtbot.addWidget(table)
    table.set_rows({"id": index, "name": f"r{index}"} for index in range(4000))
    model = table._model
    assert model.rowCount() == 512
    assert model.canFetchMore(QModelIndex())
    # 首屏之外没有为每一行算几何；公开 API 仍看得到全部行。
    assert len(table.visible_rows()) == 4000
    batches = 0
    while model.canFetchMore(QModelIndex()):
        model.fetchMore(QModelIndex())
        batches += 1
    assert batches > 1
    assert model.rowCount() == 4000
    assert not model.canFetchMore(QModelIndex())
    assert table.cell_text(3999, 1) == "r3999"


def test_visible_sequence_is_zero_copy_until_needed(qtbot: QtBot) -> None:
    table = DataTable(["id"])
    qtbot.addWidget(table)
    table.set_rows([{"id": index} for index in range(5000)])
    assert isinstance(table._visible, range)
    assert len(table._visible) == 5000
    table.set_filter("4999")
    assert isinstance(table._visible, list)
    assert list(table._visible) == [4999]
    assert table.visible_rows() == [{"id": 4999}]
    table.set_filter("")
    table.sort_by("id", descending=True)
    assert isinstance(table._visible, list)
    assert all(isinstance(index, int) for index in table._visible)
    assert table.visible_rows()[0] == {"id": 4999}


def test_cell_text_does_not_force_full_publish(qtbot: QtBot) -> None:
    table = DataTable(["id", "name"])
    qtbot.addWidget(table)
    table.set_rows({"id": index, "name": f"r{index}"} for index in range(4000))
    assert table.cell_text(3999, 1) == "r3999"
    assert table._model.rowCount() == 512


def test_select_row_publishes_only_up_to_that_row(qtbot: QtBot) -> None:
    table = DataTable(["id"])
    qtbot.addWidget(table)
    table.set_rows([{"id": index} for index in range(4000)])
    table.select_row(3000)
    assert table.selected_rows() == [{"id": 3000}]
    assert table._model.rowCount() == 3001


def test_sort_keeps_published_rows_and_scroll(qtbot: QtBot) -> None:
    from PySide6.QtCore import QModelIndex
    from PySide6.QtWidgets import QTableView

    table = DataTable(["n"])
    qtbot.addWidget(table)
    table.resize(240, 160)
    table.set_rows([{"n": index} for index in range(2000)])
    table.show()
    view = table.findChild(QTableView)
    assert view is not None
    model = view.model()
    assert model is not None
    assert model.rowCount() == 512
    while model.canFetchMore(QModelIndex()):
        model.fetchMore(QModelIndex())
    assert model.rowCount() == 2000
    bar = view.verticalScrollBar()
    qtbot.waitUntil(lambda: bar.maximum() > 1000, timeout=2000)
    bar.setValue(400)
    assert bar.value() == 400
    table.sort_by("n", descending=True)
    assert model.rowCount() == 2000
    assert bar.value() == 400
    assert table.visible_rows()[0] == {"n": 1999}


def test_view_fetches_more_when_scrolled_to_bottom(qtbot: QtBot) -> None:
    from PySide6.QtCore import QModelIndex
    from PySide6.QtWidgets import QTableView

    table = DataTable(["n"])
    qtbot.addWidget(table)
    table.resize(240, 200)
    table.set_rows([{"n": index} for index in range(4000)])
    table.show()
    view = table.findChild(QTableView)
    assert view is not None
    model = view.model()
    assert model is not None
    assert model.rowCount() == 512
    view.scrollToBottom()
    qtbot.waitUntil(lambda: model.rowCount() > 512, timeout=2000)
    assert model.canFetchMore(QModelIndex())


def test_move_rows_changes_source_order_and_can_undo(qtbot: QtBot) -> None:
    from psi6.ui.history import EditHistory

    table = DataTable(["n"])
    qtbot.addWidget(table)
    table.set_rows([{"n": "a"}, {"n": "b"}, {"n": "c"}])
    assert table.move_rows(0, 1, 3) is False
    table.set_reorderable(True)
    assert table._table.dragEnabled()
    history = EditHistory()
    table.set_history(history)
    moved: list[int] = []
    table.rows_reordered.connect(lambda: moved.append(1))
    assert table.move_rows(0, 1, 3)
    assert [row["n"] for row in table.rows()] == ["b", "c", "a"]
    assert table.selected_rows()[0]["n"] == "a"
    assert moved == [1]
    history.undo()
    assert [row["n"] for row in table.rows()] == ["a", "b", "c"]
    history.redo()
    assert [row["n"] for row in table.rows()] == ["b", "c", "a"]


def test_move_rows_refuses_while_sorted_or_filtered(qtbot: QtBot) -> None:
    table = DataTable(["n"])
    qtbot.addWidget(table)
    table.set_reorderable(True)
    table.set_rows([{"n": "b"}, {"n": "a"}])
    table._cycle_sort(0)
    assert table.move_rows(0, 1, 2) is False
    assert not table._table.dragEnabled()
    table._cycle_sort(0)
    table._cycle_sort(0)
    assert table._table.dragEnabled()
    table.set_filter("b")
    assert table.move_rows(0, 1, 1) is False
    table.set_filter("")
    assert table.move_rows(0, 1, 2)
    assert [row["n"] for row in table.rows()] == ["a", "b"]


def test_drop_uses_the_mime_source_row(qtbot: QtBot) -> None:
    from PySide6.QtCore import QMimeData, QModelIndex, Qt

    table = DataTable(["n"])
    qtbot.addWidget(table)
    table.set_reorderable(True)
    table.set_rows([{"n": "a"}, {"n": "b"}, {"n": "c"}])
    mime = QMimeData()
    mime.setData("application/x-psi6-row", b"0")
    assert table._model.dropMimeData(mime, Qt.DropAction.MoveAction, 3, 0, QModelIndex())
    assert [row["n"] for row in table.rows()] == ["b", "c", "a"]
