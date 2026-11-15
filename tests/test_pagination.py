"""分页窗口：不超过 7 页全列，更多页保留首页、末页和当前页两侧。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton, QToolButton
from pytestqt.qtbot import QtBot

from psi6.ui.pagination import Pagination, page_window


def test_page_window_keeps_ends_past_seven() -> None:
    assert page_window(6, 4) == [1, 2, 3, 4, 5, 6]
    assert page_window(12, 1) == [1, 2, "…", 12]
    assert page_window(12, 6) == [1, "…", 5, 6, 7, "…", 12]
    assert page_window(12, 12) == [1, "…", 11, 12]


def _marks(pager: Pagination) -> list[str]:
    marks: list[str] = []
    layout = pager.layout()
    assert layout is not None
    for index in range(layout.count()):
        item = layout.itemAt(index)
        assert item is not None
        widget = item.widget()
        if isinstance(widget, QLabel):
            marks.append(widget.text())
        elif isinstance(widget, QToolButton):
            marks.append(widget.accessibleName())
        elif isinstance(widget, QPushButton):
            marks.append(widget.text())
    return marks


def test_twelve_pages_track_the_current_page(qtbot: QtBot) -> None:
    pager = Pagination(12)
    qtbot.addWidget(pager)
    seen: list[int] = []
    pager.page_changed.connect(seen.append)
    assert _marks(pager) == ["上一页", "1", "2", "…", "12", "下一页"]
    assert not pager.findChildren(QToolButton)[0].isEnabled()

    twelve = next(button for button in pager.findChildren(QPushButton) if button.text() == "12")
    qtbot.mouseClick(twelve, Qt.MouseButton.LeftButton)
    assert pager.current() == 12
    assert seen == [12]
    assert _marks(pager) == ["上一页", "1", "…", "11", "12", "下一页"]
    assert not pager.findChildren(QToolButton)[-1].isEnabled()

    pager.set_current(6)
    assert seen == [12, 6]
    assert _marks(pager) == ["上一页", "1", "…", "5", "6", "7", "…", "12", "下一页"]
    current = next(button for button in pager.findChildren(QPushButton) if button.text() == "6")
    assert current.objectName() == "psi6Primary"


def test_shrinking_the_total_clamps_the_current_page(qtbot: QtBot) -> None:
    pager = Pagination(12, current=9)
    qtbot.addWidget(pager)
    seen: list[int] = []
    pager.page_changed.connect(seen.append)
    pager.set_total(6)
    assert pager.current() == 6
    assert seen == [6]
    assert _marks(pager) == ["上一页", "1", "2", "3", "4", "5", "6", "下一页"]
