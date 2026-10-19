"""终端式操作日志。

``LogPanel`` 是可筛选的四列表格。本控件按时间往下滚，观感接近彩色终端。
日志从标准库 ``logging.Handler`` 进来，不绑定某一种日志库。
"""

from __future__ import annotations

import logging
import traceback
import weakref
from datetime import datetime

from PySide6.QtCore import Qt, Signal
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


class LogConsole(QTextBrowser):
    """接收 ``LogRecord``，时间戳用辅助色，级别和正文用该级别的主题色。

    ``max_entries`` 限制行数。标准库日志用 ``handler()`` 拿到 ``LogConsoleHandler``，
    再 ``logger.addHandler``。工作线程写入会排队回界面线程。
    """

    _incoming = Signal(object)

    def __init__(self, *, max_entries: int = 2000, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("psi6LogConsole")
        self.setReadOnly(True)
        self.setOpenLinks(False)
        self.setOpenExternalLinks(False)
        self.document().setMaximumBlockCount(max(100, int(max_entries)))
        self._incoming.connect(self.append, Qt.ConnectionType.QueuedConnection)

    def append(self, record: LogRecord) -> None:
        """追加一条记录并滚到底部。颜色取写入时的当前主题。"""

        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        muted = QTextCharFormat()
        muted.setForeground(QColor(token_color("color_muted")))
        ink = QTextCharFormat()
        ink.setForeground(QColor(token_color(_LEVEL_TOKENS.get(record.level, "color_text"))))
        if self.document().characterCount() > 1:
            cursor.insertText("\n")
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
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear(self) -> None:
        self.document().clear()

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
            payload = _from_stdlib(record, self.format(record))
            console._incoming.emit(payload)
        except RuntimeError:
            return
        except Exception:
            self.handleError(record)


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
