"""图标渲染与应用壳。"""

from __future__ import annotations

from pytestqt.qtbot import QtBot
from PySide6.QtWidgets import QLabel

from psi6.examples.kit import KitWindow
from psi6.icons.glyphs import icon_names, svg_markup
from psi6.icons.render import pixmap_for
from psi6.runtime.app import App
from psi6.ui.app_shell import AppShell, NavDestination
from psi6.ui.chat import MessageList
from psi6.ui.icon import Icon
from psi6.ui.transport import TransportBar
from psi6.ui.workbench import ChangeRow, ToolTile


def test_every_icon_has_svg_and_renders(qtbot: QtBot) -> None:
    names = icon_names()
    assert "search" in names
    assert "play" in names
    assert "chevron-up" in names
    assert "win-close" in names
    assert "command" in names
    widget = Icon("search")
    qtbot.addWidget(widget)
    pix = pixmap_for("search", color="#35597a", size=16)
    assert pix.width() == 16
    assert pix.height() == 16
    assert "<svg" in svg_markup("search")


def test_app_shell_switches_pages(qtbot: QtBot) -> None:
    shell = AppShell(
        [
            NavDestination("a", "甲", "wrench"),
            NavDestination("b", "乙", "film"),
        ]
    )
    one = QLabel("one")
    two = QLabel("two")
    shell.add_page("a", one)
    shell.add_page("b", two)
    qtbot.addWidget(shell)
    shell.show_page("b")
    assert shell.current_id() == "b"
    wide = shell.sidebar.width()
    shell.set_sidebar_compact(True)
    assert shell.sidebar.is_compact()
    qtbot.waitUntil(lambda: shell.sidebar.width() < 80)
    assert shell.sidebar.width() < wide
    assert shell.sidebar._heading.isHidden()


def test_transport_and_chat_and_tiles(qtbot: QtBot) -> None:
    bar = TransportBar()
    qtbot.addWidget(bar)
    bar.set_playing(True)
    messages = MessageList()
    qtbot.addWidget(messages)
    messages.add_message("hi", role="user")
    tile = ToolTile("索引", "扫目录", icon="folder")
    qtbot.addWidget(tile)
    row = ChangeRow("a.py", kind="added")
    qtbot.addWidget(row)


def test_kit_window_builds(qtbot: QtBot, tmp_path) -> None:
    app = App("psi6-kit-test", config_root=tmp_path)
    window = KitWindow(app)
    qtbot.addWidget(window)
    window.show_page("chat")
    assert window.shell.current_id() == "chat"
    window.show_page("flow")
    assert window.shell.current_id() == "flow"
    window.show_page("icons")
    assert window.shell.current_id() == "icons"


def test_kit_widgets_are_parented_before_show(qtbot: QtBot, tmp_path) -> None:
    """搭完窗口树后，本次新建的 psi6 控件应已挂进布局，而不是无父顶层窗口。"""

    app = App("psi6-parent-test", config_root=tmp_path)
    before = set(app.qt_app.allWidgets())
    window = KitWindow(app)
    qtbot.addWidget(window)
    assert window.title_bar.parent() is window._chrome
    assert window.shell.parent() is not None
    created = set(app.qt_app.allWidgets()) - before
    orphans = [
        f"{type(widget).__name__}:{widget.objectName() or '-'}"
        for widget in created
        if widget is not window and widget.parent() is None
    ]
    assert orphans == []
