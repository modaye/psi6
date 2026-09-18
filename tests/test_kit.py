"""高频 UI 组件：空态、筛选、横幅、属性表、按钮。"""

from __future__ import annotations

from pydantic import BaseModel
from pytestqt.qtbot import QtBot
from PySide6.QtWidgets import QVBoxLayout, QWidget

from psi6.ui.banner import Banner
from psi6.ui.buttons import danger_button, primary_button
from psi6.ui.data_table import DataTable, TableColumn
from psi6.ui.empty_state import EmptyState
from psi6.ui.property_list import PropertyList
from psi6.ui.search_field import SearchField
from psi6.ui.section import Section
from psi6.ui.status_badge import StatusBadge
from psi6.ui.collapsible import Collapsible
from psi6.ui.tag import TagRow
from psi6.ui.toast import ToastHost


class Row(BaseModel):
    name: str
    size: int


def test_primary_button_uses_theme_object_name(qtbot: QtBot) -> None:
    button = primary_button("开始")
    qtbot.addWidget(button)
    assert button.objectName() == "psi6Primary"
    assert danger_button("取消").objectName() == "psi6Danger"
    from psi6.ui.buttons import ghost_button, text_button

    assert ghost_button("返回").objectName() == "psi6Ghost"
    assert text_button("粘贴代码").objectName() == "psi6Link"


def test_status_badge_and_banner(qtbot: QtBot) -> None:
    badge = StatusBadge("成功 0", tone="success")
    qtbot.addWidget(badge)
    assert badge.property("tone") == "success"
    badge.set_status("错误 2", tone="error")
    assert badge.text() == "错误 2"
    assert badge.property("tone") == "error"

    host = QWidget()
    qtbot.addWidget(host)
    layout = QVBoxLayout(host)
    banner = Banner()
    layout.addWidget(banner)
    banner.set_notice("目录为空", tone="warning")
    assert banner._label.text() == "目录为空"
    assert banner.property("tone") == "warning"
    banner.clear()
    assert banner._label.text() == ""
    assert not banner.isVisible()


def test_search_field_emits_query(qtbot: QtBot) -> None:
    field = SearchField()
    qtbot.addWidget(field)
    seen: list[str] = []
    field.query_changed.connect(seen.append)
    field.setText("readme")
    assert seen[-1] == "readme"
    assert field.query() == "readme"


def test_section_and_empty_state(qtbot: QtBot) -> None:
    section = Section("结果", description="任务输出")
    qtbot.addWidget(section)
    empty = EmptyState("暂无数据", "先运行任务")
    section.add_widget(empty)
    assert section.body.count() == 1
    clicked = []
    empty.action_clicked.connect(lambda: clicked.append(True))
    empty.set_copy("空", "提示", action_text="重试")
    empty._action.click()
    assert clicked == [True]


def test_property_list_from_model(qtbot: QtBot) -> None:
    panel = PropertyList()
    qtbot.addWidget(panel)
    panel.set_values(Row(name="a.txt", size=3))
    assert panel.values()["name"] == "a.txt"
    panel.clear()
    assert panel.values() == {}


def test_data_table_filter_and_empty(qtbot: QtBot) -> None:
    table = DataTable(
        [
            TableColumn("name", "名称", stretch=True),
            TableColumn("size", "大小"),
        ]
    )
    qtbot.addWidget(table)
    assert table._stack.currentWidget() is table._empty
    table.set_rows([Row(name="a.txt", size=3), Row(name="b.md", size=8)])
    assert table._stack.currentWidget() is table._table
    table.set_filter("md")
    assert table.rows()[0]["name"] == "a.txt"
    assert [row["name"] for row in table.visible_rows()] == ["b.md"]
    table.set_filter("zzz")
    assert table.visible_rows() == []
    assert table._empty._title.text() == "无匹配项"
    table.clear()
    assert table.rows() == []
    assert table._empty._title.text() == "暂无数据"


def test_collapsible_starts_collapsed(qtbot: QtBot) -> None:
    panel = Collapsible("高级选项")
    qtbot.addWidget(panel)
    assert not panel.is_expanded()
    panel.set_expanded(True)
    assert panel.is_expanded()
    assert not panel._body.isHidden()


def test_tag_row_exclusive_select(qtbot: QtBot) -> None:
    host = QWidget()
    qtbot.addWidget(host)
    layout = QVBoxLayout(host)
    row = TagRow()
    layout.addWidget(row)
    seen: list[str] = []
    row.tag_selected.connect(seen.append)
    row.set_labels((".md", ".log", ".md"))
    assert [tag.text() for tag in row._tags] == [".md", ".log"]
    row._tags[0].click()
    assert row.selected() == ".md"
    assert seen[-1] == ".md"
    row._tags[0].click()
    assert row.selected() == ""
    assert seen[-1] == ""


def test_data_table_busy_overlay(qtbot: QtBot) -> None:
    table = DataTable(["name"])
    qtbot.addWidget(table)
    table.set_rows([{"name": "a.txt"}])
    table.set_busy(True, "正在扫描…")
    assert table._busy.is_busy()
    assert table._busy._label.text() == "正在扫描…"
    table.set_busy(False)
    assert not table._busy.is_busy()


def test_toast_host_push_and_cap(qtbot: QtBot) -> None:
    window = QWidget()
    qtbot.addWidget(window)
    host = ToastHost(window)
    for index in range(5):
        host.push(f"msg-{index}", timeout_ms=60_000)
    assert len(host._cards) == 4

