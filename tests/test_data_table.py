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
