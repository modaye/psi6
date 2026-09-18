"""场景控件的布局约束：空态宽度、标题栏按钮、日志表头、发送钮。"""

from __future__ import annotations

from pytestqt.qtbot import QtBot
from PySide6.QtWidgets import QPushButton, QWidget

from psi6.runtime.logs import LogLevel, LogRecord
from psi6.ui.chat import Composer, MessageList
from psi6.ui.desktop_window import DesktopWindow
from psi6.ui.diff_view import DiffView
from psi6.ui.empty_state import EmptyState
from psi6.ui.icon import IconButton
from psi6.ui.log_panel import LogPanel
from psi6.ui.playlist import Playlist
from psi6.ui.toast import ToastHost
from psi6.ui.transport import TransportBar


def test_empty_state_hint_keeps_readable_width(qtbot: QtBot) -> None:
    empty = EmptyState("没有打开影片", "从资料库选一部，或拖进此区域。")
    qtbot.addWidget(empty)
    empty.resize(640, 420)
    empty.show()
    qtbot.waitExposed(empty)
    assert empty._hint.minimumWidth() >= 280
    assert empty._hint.width() >= 280
    assert empty._title.width() >= 280


def test_icon_button_hot_zone_and_title_bar(qtbot: QtBot) -> None:
    button = IconButton("play", label="播放")
    qtbot.addWidget(button)
    assert button.width() == 32
    assert button.height() == 32
    compact = IconButton("win-close", label="关闭", size=16, extent=32)
    qtbot.addWidget(compact)
    assert compact.size().width() == 32
    window = DesktopWindow(title="布局")
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    bar = window.title_bar
    assert bar.height() == 36
    assert bar._min.height() == 32
    assert bar._close.objectName() == "psi6TitleClose"


def test_log_panel_hides_row_numbers_and_uses_chinese_levels(qtbot: QtBot) -> None:
    panel = LogPanel()
    qtbot.addWidget(panel)
    assert not panel._table.verticalHeader().isVisible()
    panel.append(LogRecord(LogLevel.SUCCESS, "health-check ok"))
    panel.append(LogRecord(LogLevel.WARNING, "retry queue"))
    assert panel._table.item(0, 1).text() == "成功"
    assert panel._table.item(1, 1).text() == "警告"


def test_playlist_has_no_marker_column(qtbot: QtBot) -> None:
    playlist = Playlist()
    qtbot.addWidget(playlist)
    keys = [column.key for column in playlist._table._columns]
    assert keys == ["title", "artist", "time"]
    playlist.set_tracks([{"title": "Night Shift", "artist": "Harbor", "time": "3:41"}])
    playlist.set_current(0)
    assert playlist._table.visible_rows()[0]["title"] == "Night Shift"


def test_diff_view_is_a_card(qtbot: QtBot) -> None:
    view = DiffView()
    qtbot.addWidget(view)
    assert view.objectName() == "psi6DiffView"
    assert view._host.objectName() == "psi6DiffHost"
    view.set_lines([("+", "added"), ("-", "removed"), (" ", "same")])
    names = [
        view._column.itemAt(index).widget().objectName()
        for index in range(view._column.count() - 1)
    ]
    assert names == ["psi6DiffAdd", "psi6DiffDel", "psi6DiffCtx"]


def test_composer_send_is_primary_and_transport_is_large(qtbot: QtBot) -> None:
    composer = Composer()
    qtbot.addWidget(composer)
    send = composer.findChild(QPushButton, "psi6Primary")
    assert send is not None
    assert send.text() == "发送"
    assert send.height() == 32
    bar = TransportBar()
    qtbot.addWidget(bar)
    assert bar._play.width() >= 32
    assert bar._play.height() >= 32


def test_toast_stack_does_not_compress_cards(qtbot: QtBot) -> None:
    window = QWidget()
    qtbot.addWidget(window)
    window.resize(900, 640)
    window.show()
    qtbot.waitExposed(window)
    host = ToastHost(window)
    host.push("已保存主题。", timeout_ms=0)
    host.push("扫描完成，结果已写入表格。", timeout_ms=0)
    host.push("第三份通知也要完整显示关闭按钮，不能被挤成一条线。", timeout_ms=0)
    qtbot.waitUntil(lambda: host.isVisible())
    assert len(host._cards) == 3
    assert host.height() >= sum(card.minimumHeight() for card in host._cards)
    for index, card in enumerate(host._cards):
        assert card.isVisible()
        assert card.height() >= 36, f"card {index} squeezed to {card.height()}"
        assert card._close.height() == 28
        assert card._close.width() == 28
        assert not card._close.isHidden()
    for upper, lower in zip(host._cards, host._cards[1:]):
        assert upper.geometry().bottom() <= lower.geometry().top()


def test_message_list_appends_below_without_empty_gap(qtbot: QtBot) -> None:
    messages = MessageList()
    qtbot.addWidget(messages)
    messages.resize(640, 480)
    messages.show()
    qtbot.waitExposed(messages)
    first = messages.add_message("第一条", role="user", timestamp="18:00")
    second = messages.add_message("第二条助手回复", role="assistant", timestamp="18:01")
    qtbot.waitUntil(lambda: second.isVisible())
    first_wrap = first.parentWidget()
    second_wrap = second.parentWidget()
    assert first_wrap is not None and second_wrap is not None
    assert first_wrap.y() == 0
    assert second_wrap.y() >= first_wrap.y() + first_wrap.height()
    assert messages._empty.isHidden() or messages._stack.currentWidget() is messages._scroll
