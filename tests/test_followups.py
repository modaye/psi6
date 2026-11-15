"""加载、通知图标、表内底色、可拖列宽、抽屉和页签外框。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QHeaderView, QLabel, QWidget
from pytestqt.qtbot import QtBot

from psi6 import App
from psi6.theme.tokens import Tokens
from psi6.ui.data_table import DataTable, TableColumn
from psi6.ui.drawer import Drawer
from psi6.ui.icon import Icon
from psi6.ui.loading import BusyBar, Spinner
from psi6.ui.tag import Tag
from psi6.ui.toast import ToastCard
from psi6.ui.underline_tabs import UnderlineTabs


def _pixel(image, widget, x: int, y: int) -> QColor:
    scale = image.width() / max(widget.width(), 1)
    return image.pixelColor(int((x + 0.5) * scale), int((y + 0.5) * scale))


def test_loading_widgets_are_not_progress_bars(qtbot: QtBot, tmp_path: Path) -> None:
    app = App("psi6-loading", theme="light", config_root=tmp_path, reduced_motion=True)
    del app
    spin = Spinner(24)
    bar = BusyBar()
    qtbot.addWidget(spin)
    qtbot.addWidget(bar)
    spin.show()
    bar.resize(200, 6)
    bar.show()
    qtbot.wait(30)
    assert spin.width() == 24
    assert spin.property("angle") == 0.0
    assert bar.height() == 6
    assert bar.property("phase") == 0.0


def test_toast_puts_an_icon_on_the_left(qtbot: QtBot) -> None:
    card = ToastCard("已经保存", tone="success")
    qtbot.addWidget(card)
    icon = card.findChild(Icon)
    assert icon is not None
    assert icon.name() == "check"
    assert card.layout().itemAt(0).widget() is icon
    assert card.layout().indexOf(icon) < card.layout().indexOf(card.findChild(QLabel))


def test_table_interior_is_surface_and_columns_can_resize(qtbot: QtBot, tmp_path: Path) -> None:
    app = App("psi6-table-resize", theme="graphite", config_root=tmp_path)
    del app
    table = DataTable(
        (TableColumn("name", "任务", stretch=True), TableColumn("owner", "负责人"))
    )
    table.set_rows(({"name": "设计令牌", "owner": "林悦"},))
    qtbot.addWidget(table)
    table.resize(640, 240)
    table.show()
    qtbot.wait(20)
    header = table._table.horizontalHeader()
    assert header.sectionResizeMode(0) == QHeaderView.ResizeMode.Interactive
    assert header.sectionResizeMode(1) == QHeaderView.ResizeMode.Interactive
    assert header.sectionSize(0) > header.sectionSize(1)


def test_tag_capsule_corners_are_clear(qtbot: QtBot, tmp_path: Path) -> None:
    app = App("psi6-tag-edge", theme="graphite", config_root=tmp_path)
    del app
    tag = Tag("成功", tone="success", checkable=False)
    qtbot.addWidget(tag)
    tag.show()
    image = tag.grab().toImage()
    corner = _pixel(image, tag, 0, 0)
    center = _pixel(image, tag, tag.width() // 2, tag.height() // 2)
    assert corner.alpha() < 40
    assert center.alpha() > 200


def test_selected_tab_has_no_box_when_focus_ring_is_off(qtbot: QtBot, tmp_path: Path) -> None:
    app = App("psi6-tab-ring", theme="light", config_root=tmp_path, focus_ring=False)
    del app
    tabs = UnderlineTabs()
    tabs.add_tab("快", QLabel("一"))
    tabs.add_tab("慢", QLabel("二"))
    qtbot.addWidget(tabs)
    tabs.resize(360, 140)
    tabs.show()
    tabs.setFocus()
    image = tabs._bar.grab().toImage()
    focus = QColor(Tokens.light().color_focus)
    hits = 0
    for y in range(image.height()):
        for x in range(image.width()):
            color = image.pixelColor(x, y)
            same = (color.red(), color.green(), color.blue())
            if same == (focus.red(), focus.green(), focus.blue()):
                hits += 1
    assert hits == 0


def test_drawer_slides_over_the_host(qtbot: QtBot, tmp_path: Path) -> None:
    app = App("psi6-drawer", theme="light", config_root=tmp_path, reduced_motion=True)
    del app
    host = QWidget()
    host.resize(480, 320)
    qtbot.addWidget(host)
    host.show()
    qtbot.waitExposed(host)
    drawer = Drawer("详情", host)
    drawer.body().addWidget(QLabel("正文"))
    drawer.open()
    assert drawer.isVisible()
    assert drawer.width() == host.width()
    assert drawer._panel.x() == host.width() - drawer._panel.width()
    qtbot.mouseClick(drawer, Qt.MouseButton.LeftButton, pos=QPoint(8, 40))
    assert drawer.isVisible() is False
