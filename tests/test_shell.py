"""图标渲染与应用壳。"""

from __future__ import annotations

from PySide6.QtWidgets import QLabel
from pytestqt.qtbot import QtBot

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


def test_pinned_shortcuts_keep_their_own_page_id(qtbot: QtBot) -> None:
    """侧栏底部的最近任务发出自己的编号，未知编号不会把内容栈切走。"""

    shell = AppShell((NavDestination("home", "工作台", "grid"),), title="本地工作空间")
    home = QLabel("home")
    shell.add_page("home", home)
    seen: list[str] = []
    shell.sidebar.destination_changed.connect(seen.append)
    shell.set_pinned((NavDestination("task:1", "客户通知", "file"),))
    qtbot.addWidget(shell)
    shell.show_page("home")
    shell.sidebar._pinned_buttons["task:1"].click()
    assert seen[-1] == "task:1"
    assert shell.current_id() == "home"
    shell.set_pinned((NavDestination("task:2", "另一项", "file"),))
    assert "task:1" not in shell.sidebar._pinned_buttons
    shell.sidebar.select("task:2")
    assert shell.sidebar._pinned_buttons["task:2"].isChecked()


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


def test_log_console_handler_shows_stdlib_records(qtbot: QtBot) -> None:
    """标准库 Handler 把级别名和正文送进面板，工作线程也会排队回来。"""

    import logging
    import threading

    from psi6.theme.runtime import token_color
    from psi6.ui.log_console import LogConsole

    console = LogConsole()
    qtbot.addWidget(console)
    demo = logging.getLogger("psi6.test.console")
    demo.setLevel(logging.DEBUG)
    demo.propagate = False
    handler = console.handler(level=logging.DEBUG)
    demo.addHandler(handler)
    try:
        threading.Thread(target=lambda: demo.warning("汇率缺失-psi6"), daemon=True).start()
        qtbot.waitUntil(lambda: "汇率缺失-psi6" in console.toPlainText(), timeout=2000)
        text = console.toPlainText()
        assert "WARNING" in text
        assert "psi6.test.console" in text
        assert token_color("color_warning").startswith("#")
    finally:
        demo.removeHandler(handler)


def test_log_console_exception_is_shown_once(qtbot: QtBot) -> None:
    import logging

    from psi6.ui.log_console import LogConsole

    console = LogConsole()
    qtbot.addWidget(console)
    demo = logging.getLogger("psi6.test.console.exc")
    demo.setLevel(logging.DEBUG)
    demo.propagate = False
    handler = console.handler(level=logging.DEBUG)
    demo.addHandler(handler)
    try:
        try:
            raise ZeroDivisionError("boom-psi6")
        except ZeroDivisionError:
            demo.exception("读取失败")
        qtbot.waitUntil(lambda: "读取失败" in console.toPlainText(), timeout=2000)
        text = console.toPlainText()
        assert text.count("读取失败") == 1
        assert text.count("Traceback (most recent call last)") == 1
        assert text.count("ZeroDivisionError: boom-psi6") == 1
    finally:
        demo.removeHandler(handler)


def test_log_console_appends_and_caps(qtbot: QtBot, tmp_path) -> None:
    """纯文本操作日志：加时间戳、限行数，颜色按级别取 token。"""

    from psi6.runtime.logs import LogLevel, LogRecord
    from psi6.ui.log_console import LogConsole

    panel = LogConsole(max_entries=120)
    qtbot.addWidget(panel)
    panel.append(LogRecord(LogLevel.INFO, "开始读取"))
    panel.append(LogRecord(LogLevel.ERROR, "解析失败", detail="第 3 行"))
    text = panel.document().toPlainText()
    assert "开始读取" in text
    assert "解析失败" in text
    assert "第 3 行" in text
    for index in range(200):
        panel.append(LogRecord(LogLevel.INFO, f"row {index}"))
    assert panel.document().blockCount() <= 120


def test_log_console_accepts_plain_text(qtbot: QtBot) -> None:
    from psi6.ui.log_console import LogConsole

    panel = LogConsole()
    qtbot.addWidget(panel)
    panel.append("纯文本一行")
    assert "纯文本一行" in panel.document().toPlainText()


def test_log_console_recolors_when_theme_switches(qtbot: QtBot, tmp_path) -> None:
    """配色写进了文档，所以主题切换要按存下来的记录整片重画。"""

    from psi6.runtime.app import App
    from psi6.runtime.logs import LogLevel, LogRecord
    from psi6.ui.log_console import LogConsole

    app = App("psi6-log-theme", theme="light", config_root=tmp_path)
    panel = LogConsole()
    qtbot.addWidget(panel)
    panel.append(LogRecord(LogLevel.ERROR, "解析失败"))
    panel.append("纯文本一行")
    assert app.tokens.color_danger.lower() in panel.toHtml().lower()
    app.set_theme(app.tokens.overlay({"color_danger": "#00fe00"}))
    html = panel.toHtml().lower()
    assert "#00fe00" in html
    assert "解析失败" in panel.toPlainText()
    assert "纯文本一行" in panel.toPlainText()
    app.set_theme("light")


def test_sparkline_repaints_when_theme_switches(qtbot: QtBot, tmp_path) -> None:
    from psi6.runtime.app import App
    from psi6.ui.sparkline import Sparkline

    app = App("psi6-spark-theme", theme="light", config_root=tmp_path)
    line = Sparkline([1.0, 3.0, 2.0])
    qtbot.addWidget(line)
    line.show()
    qtbot.waitExposed(line)
    repaints: list[int] = []
    original = line.update

    def spy(*args: object) -> None:
        repaints.append(1)
        original(*args)

    line.update = spy  # type: ignore[method-assign]
    app.set_theme("dark")
    assert repaints
    app.set_theme("light")


def test_icon_paints_at_device_ratio(qtbot: QtBot, monkeypatch) -> None:
    from PySide6.QtGui import QPixmap

    from psi6.ui import icon as icon_module

    seen: dict[str, object] = {}

    def fake_pixmap(name: str, *, color: str, size: int = 16, ratio: float = 1.0) -> QPixmap:
        del name, color
        seen["ratio"] = ratio
        return QPixmap(size, size)

    def fake_ratio(widget: object = None) -> float:
        seen["widget"] = widget
        return 2.0

    monkeypatch.setattr(icon_module, "pixmap_for", fake_pixmap)
    monkeypatch.setattr(icon_module, "device_ratio", fake_ratio)
    widget = icon_module.Icon("search")
    qtbot.addWidget(widget)
    widget.render(QPixmap(widget.size()))
    assert seen["ratio"] == 2.0
    assert seen["widget"] is widget


def test_apply_button_icon_refreshes_on_theme_change(qtbot: QtBot, monkeypatch) -> None:
    from PySide6.QtCore import QEvent
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication, QPushButton

    from psi6.ui import icon as icon_module

    button = QPushButton("搜索")
    qtbot.addWidget(button)
    icon_module.apply_button_icon(button, "search")
    calls: list[str] = []

    def fake_icon(name: str, *, color: str, size: int = 16, ratio: float | None = None) -> QIcon:
        del color, size, ratio
        calls.append(name)
        return QIcon()

    monkeypatch.setattr(icon_module, "icon_for", fake_icon)
    QApplication.sendEvent(button, QEvent(QEvent.Type.StyleChange))
    assert calls == ["search"]
    icon_module.apply_button_icon(button, "play")
    calls.clear()
    QApplication.sendEvent(button, QEvent(QEvent.Type.DevicePixelRatioChange))
    assert calls == ["play"]


def test_icon_button_asks_for_the_widget_ratio(qtbot: QtBot, monkeypatch) -> None:
    from PySide6.QtGui import QIcon

    from psi6.ui import icon as icon_module

    seen: dict[str, float | None] = {}

    def fake_icon(
        name: str,
        *,
        color: str,
        size: int = 16,
        ratio: float | None = None,
    ) -> QIcon:
        del name, color, size
        seen["ratio"] = ratio
        return QIcon()

    monkeypatch.setattr(icon_module, "icon_for", fake_icon)
    monkeypatch.setattr(icon_module, "device_ratio", lambda widget=None: 1.5)
    button = icon_module.IconButton("play", label="播放")
    qtbot.addWidget(button)
    button.refresh()
    assert seen["ratio"] == 1.5


def test_kit_window_builds(qtbot: QtBot, tmp_path) -> None:
    app = App("psi6-kit-test", config_root=tmp_path)
    window = KitWindow(app)
    qtbot.addWidget(window)
    window.show_page("buttons")
    assert window.shell.current_id() == "buttons"
    window.show_page("states")
    assert window.shell.current_id() == "states"
    window.show_page("compose")
    assert window.shell.current_id() == "compose"


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
