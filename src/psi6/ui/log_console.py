"""终端式操作日志。

``LogPanel`` 是可筛选的四列表格。本控件按时间往下滚，观感接近彩色终端。
日志从标准库 ``logging.Handler`` 进来，不绑定某一种日志库。
"""

from __future__ import annotations

import logging
import traceback
import weakref
from collections import deque
from datetime import datetime

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QTextBrowser, QWidget

from psi6.runtime.logs import LogLevel, LogRecord
from psi6.theme.runtime import token_color

_LEVEL_TOKENS = {
    LogLevel.DEBUG: "color_muted",
    LogLevel.INFO: "color_text",
    LogLevel.SUCCESS: "color_success",
    LogLevel.WARNING: "color_warning",
    LogLevel.ERROR: "color_danger",
}

_LEVEL_LABELS = {
    LogLevel.DEBUG: "DEBUG",
    LogLevel.INFO: "INFO",
    LogLevel.SUCCESS: "SUCCESS",
    LogLevel.WARNING: "WARNING",
    LogLevel.ERROR: "ERROR",
}

_THEME_EVENTS = {QEvent.Type.PaletteChange, QEvent.Type.StyleChange}


class LogConsole(QTextBrowser):
    """接收 ``LogRecord``，时间戳用辅助色，级别和正文用该级别的主题色。

    ``max_entries`` 限制行数。记录留在控件里，主题切换后整片按新配色重画。
    日志走标准库 ``logging.Handler``：``handler()`` 拿到 ``LogConsoleHandler``，
    再 ``logger.addHandler``。工作线程写入会排队回界面线程。
    """

    _incoming = Signal(object)

    def __init__(self, *, max_entries: int = 2000, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("psi6LogConsole")
        self.setReadOnly(True)
        self.setOpenLinks(False)
        self.setOpenExternalLinks(False)
        self._limit = max(100, int(max_entries))
        self.document().setMaximumBlockCount(self._limit)
        self._entries: deque[LogRecord | str] = deque(maxlen=self._limit)
        self._incoming.connect(self.append, Qt.ConnectionType.QueuedConnection)

    def append(self, record: LogRecord | str) -> None:
        """追加一条记录并滚到底部。纯文本没有级别，只吃当前正文色。"""

        self._entries.append(record)
        self._write(self._tail(), record)
        self._scroll_to_end()

    def _tail(self) -> QTextCursor:
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        if self.document().characterCount() > 1:
            cursor.insertText("\n")
        return cursor

    def _write(self, cursor: QTextCursor, record: LogRecord | str) -> None:
        if isinstance(record, str):
            cursor.insertText(record, self._format("color_text"))
            return
        ink = self._format(_LEVEL_TOKENS.get(record.level, "color_text"))
        muted = self._format("color_muted")
        cursor.insertText(datetime.now().strftime("%H:%M:%S"), muted)
        cursor.insertText("  ", muted)
        label = _LEVEL_LABELS.get(record.level, record.level.value.upper()).ljust(7)
        cursor.insertText(label, ink)
        cursor.insertText("  ", muted)
        logger_name = record.extra.get("logger", "")
        if logger_name:
            cursor.insertText(f"{logger_name}  ", muted)
        cursor.insertText(record.message, ink)
        if record.detail:
            cursor.insertText(f"\n    {record.detail}", muted)

    @staticmethod
    def _format(token: str) -> QTextCharFormat:
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(token_color(token)))
        return fmt

    def _scroll_to_end(self) -> None:
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear(self) -> None:
        self._entries.clear()
        self.document().clear()

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if event.type() in _THEME_EVENTS:
            self._rebuild()

    def _rebuild(self) -> None:
        """按当前主题重画全部记录。配色存在文档里，不重画就留着上一套主题的颜色。"""

        entries = list(self._entries)
        self.document().clear()
        cursor = self._tail()
        for index, entry in enumerate(entries):
            if index:
                cursor.insertText("\n")
            self._write(cursor, entry)
        self._scroll_to_end()

    def handler(self, *, level: int = logging.NOTSET) -> LogConsoleHandler:
        """返回可 ``addHandler`` 的处理器。挂到哪个 logger 由应用决定。"""

        return LogConsoleHandler(self, level=level)


class LogConsoleHandler(logging.Handler):
    """把标准库 ``LogRecord`` 写进 ``LogConsole``。

    用法::

        console = LogConsole()
        log = logging.getLogger("myapp")
        log.setLevel(logging.INFO)
        log.addHandler(console.handler())

    控件自己绘制时间戳和级别颜色，Formatter 只负责正文。
    标准库没有 SUCCESS；``levelname`` 为 ``SUCCESS`` 时仍用成功色。
    其它日志库先把记录送进 ``logging``，再由这个 Handler 显示。
    """

    def __init__(self, console: LogConsole, level: int = logging.NOTSET) -> None:
        super().__init__(level)
        self._console = weakref.ref(console)

    def emit(self, record: logging.LogRecord) -> None:
        console = self._console()
        if console is None:
            return
        try:
            message = record.getMessage() if _has_detail(record) else self.format(record)
            payload = _from_stdlib(record, message)
            console._incoming.emit(payload)
        except RuntimeError:
            return
        except Exception:
            self.handleError(record)


def _has_detail(record: logging.LogRecord) -> bool:
    """异常和堆栈由 ``LogRecord.detail`` 单独显示，正文里不要再拼一遍。"""

    return bool(record.exc_info or record.exc_text or record.stack_info)


def _from_stdlib(record: logging.LogRecord, message: str) -> LogRecord:
    detail = ""
    if record.exc_info:
        detail = "".join(traceback.format_exception(*record.exc_info)).rstrip()
    elif record.stack_info:
        detail = str(record.stack_info)
    extra: dict[str, str] = {}
    if record.name:
        extra["logger"] = record.name
    return LogRecord(_level_of(record), message, detail=detail, extra=extra)


def _level_of(record: logging.LogRecord) -> LogLevel:
    if record.levelname.upper() == "SUCCESS":
        return LogLevel.SUCCESS
    if record.levelno >= logging.ERROR:
        return LogLevel.ERROR
    if record.levelno >= logging.WARNING:
        return LogLevel.WARNING
    if record.levelno >= logging.INFO:
        return LogLevel.INFO
    return LogLevel.DEBUG
