"""自绘辅助、流式布局、按下缩小过滤器。"""

from __future__ import annotations

from pytestqt.qtbot import QtBot
from PySide6.QtCore import QRectF, Qt
from PySide6.QtWidgets import QLabel, QWidget

from psi6.theme.paint import mix_color, rounded_rect_path
from psi6.ui.filters import DebugEventFilter, PressScaleFilter, install_press_scale
from psi6.ui.flow_layout import FlowLayout
from psi6.ui.icon import IconButton
from psi6.ui.switch import Switch
from psi6.ui.tag import TagRow


def test_mix_color_and_rounded_path() -> None:
    mid = mix_color("#000000", "#ffffff", 0.5)
    assert mid.red() == 127
    path = rounded_rect_path(QRectF(0, 0, 40, 20), (8, 0, 4, 0))
    assert not path.isEmpty()
    box = path.boundingRect()
    assert box.width() >= 39


def test_flow_layout_wraps(qtbot: QtBot) -> None:
    host = QWidget()
    flow = FlowLayout(host, spacing=4)
    labels = []
    for index in range(6):
        label = QLabel(f"item-{index}")
        label.setFixedWidth(80)
        flow.addWidget(label)
        labels.append(label)
    qtbot.addWidget(host)
    host.resize(120, 400)
    host.show()
    qtbot.waitExposed(host)
    qtbot.waitUntil(lambda: len({label.y() for label in labels}) > 1)


def test_tag_row_wraps_when_narrow(qtbot: QtBot) -> None:
    row = TagRow()
    qtbot.addWidget(row)
    row.set_labels(["alpha", "beta", "gamma", "delta"])
    row.resize(48, 240)
    row.show()
    qtbot.waitExposed(row)
    qtbot.waitUntil(lambda: len({tag.y() for tag in row._tags}) > 1)


def test_press_scale_on_icon_button(qtbot: QtBot) -> None:
    button = IconButton("play", label="播放")
    qtbot.addWidget(button)
    button.show()
    qtbot.waitExposed(button)
    filt = button.findChildren(PressScaleFilter)[0]
    qtbot.mousePress(button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: filt.scale < 0.99)
    qtbot.mouseRelease(button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: abs(filt.scale - 1.0) < 0.05)


def test_install_press_scale_is_idempotent(qtbot: QtBot) -> None:
    switch = Switch()
    qtbot.addWidget(switch)
    first = install_press_scale(switch)
    second = install_press_scale(switch)
    assert first is second


def test_debug_event_filter_records(qtbot: QtBot) -> None:
    host = QWidget()
    qtbot.addWidget(host)
    watcher = DebugEventFilter(host)
    host.installEventFilter(watcher)
    host.show()
    qtbot.waitExposed(host)
    qtbot.waitUntil(lambda: bool(watcher.events))
    assert all(" " in line for line in watcher.events)
