"""桌面壳层：标题栏、防多开、命令面板、步进条。"""

from __future__ import annotations

import uuid

from PySide6.QtCore import QPoint, QRect, QSize
from pytestqt.qtbot import QtBot

from psi6.runtime.qt_env import detect_font_dir, prepare_qt_environment
from psi6.runtime.single_instance import SingleInstance, instance_key
from psi6.ui.chat import MessageList
from psi6.ui.command_palette import Command, CommandPalette
from psi6.ui.desktop_window import DesktopWindow
from psi6.ui.diff_view import DiffView
from psi6.ui.stepper import Stepper
from psi6.ui.title_bar import drag_origin_after_restore
from psi6.ui.transport import TransportBar
from psi6.ui.tray import TrayIcon
from psi6.ui.window_shape import grip_rects, hit_resize_edge, round_mask, supports_window_mask
from psi6.ui.workbench import ChangeList


def test_prepare_qt_environment_points_at_real_fonts() -> None:
    found = prepare_qt_environment()
    system = detect_font_dir()
    if system is not None:
        assert found is not None
        assert found.is_dir()


def test_desktop_window_has_title_bar(qtbot: QtBot) -> None:
    window = DesktopWindow(title="索引工具", icon="folder")
    qtbot.addWidget(window)
    assert window.title_bar.parent() is window._chrome
    assert window.title_bar._title.parent() is window.title_bar
    assert window.title_bar._title.text() == "索引工具"
    assert window.title_bar._min.toolTip() == "最小化"
    assert window.title_bar._close.toolTip() == "关闭"
    window.setWindowTitle("新标题")
    assert window.title_bar._title.text() == "新标题"
    window.set_icon("search")
    assert window.title_bar.icon_name == "search"


def test_title_bar_restore_keeps_cursor_ratio() -> None:
    origin = drag_origin_after_restore(QPoint(500, 40), QSize(400, 300), 0.25, 10)
    assert origin == QPoint(400, 30)


def test_resize_edge_hit_is_not_content() -> None:
    size = QSize(400, 300)
    assert hit_resize_edge(QPoint(2, 150), size) == "left"
    assert hit_resize_edge(QPoint(398, 150), size) == "right"
    assert hit_resize_edge(QPoint(200, 2), size) == "top"
    assert hit_resize_edge(QPoint(200, 298), size) == "bottom"
    assert hit_resize_edge(QPoint(2, 2), size) == "top-left"
    assert hit_resize_edge(QPoint(200, 150), size) is None
    blocked = QRect(320, 0, 80, 36)
    assert hit_resize_edge(QPoint(350, 4), size, blocked=blocked) is None
    assert hit_resize_edge(QPoint(200, 4), size, blocked=blocked) == "top"


def test_grip_rects_top_is_vertical_strip() -> None:
    rects = grip_rects(QSize(400, 300), thickness=8)
    assert rects["top"].height() == 8
    assert rects["bottom"].height() == 8
    assert rects["left"].width() == 8
    assert rects["right"].width() == 8
    assert not rects["top"].contains(QPoint(200, 80))
    blocked = QRect(310, 0, 90, 36)
    clipped = grip_rects(QSize(400, 300), thickness=8, blocked=blocked)
    assert clipped["top"].right() <= blocked.left()


def test_close_to_tray_hides_request_quit_closes(qtbot: QtBot) -> None:
    window = DesktopWindow(title="托盘")
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    window.close_to_tray = True
    window.close()
    assert not window.isVisible()
    assert window.close_to_tray
    window.request_quit()
    assert window._force_quit


def test_tray_refresh_is_safe_without_system_tray(qtbot: QtBot) -> None:
    window = DesktopWindow(title="托盘", icon="folder")
    qtbot.addWidget(window)
    tray = TrayIcon(window, tooltip="psi6-test", icon="folder")
    tray.set_icon("search")
    tray.set_tooltip("updated")
    tray.refresh()
    assert tray.icon_name == "search"


def test_desktop_window_applies_round_mask(qtbot: QtBot) -> None:
    region = round_mask(QRect(0, 0, 100, 80), 12)
    assert region.contains(QPoint(50, 40))
    assert not region.contains(QPoint(0, 0))
    window = DesktopWindow(title="圆角")
    qtbot.addWidget(window)
    window.resize(480, 320)
    window.show()
    qtbot.waitExposed(window)
    window._sync_shape()
    assert window._chrome.property("rounded") in {True, "true"}
    if supports_window_mask():
        assert not window.mask().isEmpty()


def test_single_instance_second_fails(qtbot: QtBot) -> None:
    del qtbot
    key = instance_key("psi6-test", f"lock-{uuid.uuid4().hex}")
    first = SingleInstance(key)
    assert first.try_acquire()
    second = SingleInstance(key)
    assert not second.try_acquire()
    first.close()
    third = SingleInstance(key)
    assert third.try_acquire()
    third.close()


def test_transport_mute_and_chat_empty(qtbot: QtBot) -> None:
    bar = TransportBar()
    qtbot.addWidget(bar)
    assert not bar.is_muted()
    bar.set_muted(True)
    assert bar.is_muted()
    messages = MessageList()
    qtbot.addWidget(messages)
    assert messages.is_empty()
    messages.add_message("hi", role="user", timestamp="18:00")
    assert not messages.is_empty()


def test_stepper_diff_and_changes(qtbot: QtBot) -> None:
    stepper = Stepper(("甲", "乙", "丙"))
    qtbot.addWidget(stepper)
    assert stepper.current_index() == 0
    stepper.next()
    assert stepper.current_index() == 1
    diff = DiffView()
    qtbot.addWidget(diff)
    diff.set_lines([("+", "added"), ("-", "removed"), (" ", "same")])
    changes = ChangeList()
    qtbot.addWidget(changes)
    seen: list[str] = []
    changes.current_changed.connect(seen.append)
    changes.set_changes([("a.py", "modified"), ("b.py", "added")])
    changes.set_current("b.py")
    assert seen[-1] == "b.py"
    assert changes._rows[1].is_selected()


def test_command_palette_filters(qtbot: QtBot) -> None:
    palette = CommandPalette()
    qtbot.addWidget(palette)
    palette.set_commands(
        [
            Command("open", "打开文件", "批处理", "folder"),
            Command("theme", "切换主题", "深色", "sun"),
        ]
    )
    fired: list[str] = []
    palette.activated.connect(fired.append)
    palette._rebuild("主题")
    assert palette._list.count() == 1
    item = palette._list.item(0)
    palette._on_item(item)
    assert fired == ["theme"]
