"""任务过程日志的数据结构。与诊断日志（如 loguru）分离。"""

from __future__ import annotations

import contextvars
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum


class LogLevel(StrEnum):
    """操作日志级别。"""

    DEBUG = "debug"
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class LogRecord:
    """一条给用户看的操作记录。"""

    level: LogLevel
    message: str
    detail: str = ""
    extra: dict[str, str] = field(default_factory=dict)


_ACTIVE_SINK: contextvars.ContextVar[Callable[[LogRecord], None] | None] = contextvars.ContextVar(
    "psi6_task_log_sink",
    default=None,
)

_STDLIB_LEVELS = {
    LogLevel.DEBUG: logging.DEBUG,
    LogLevel.INFO: logging.INFO,
    LogLevel.SUCCESS: logging.INFO,
    LogLevel.WARNING: logging.WARNING,
    LogLevel.ERROR: logging.ERROR,
}


_LOGURU_LEVELS = {
    "TRACE": LogLevel.DEBUG,
    "DEBUG": LogLevel.DEBUG,
    "SUCCESS": LogLevel.SUCCESS,
    "WARNING": LogLevel.WARNING,
    "ERROR": LogLevel.ERROR,
    "CRITICAL": LogLevel.ERROR,
}


def loguru_sink(on_log: Callable[[LogRecord], None]) -> Callable[[object], None]:
    """返回可传给 ``logger.add`` 的 sink，把 loguru 记录转成 ``LogRecord``。

    ``loguru`` 不是 psi6 的安装依赖；只有应用自己装了它才会用到这个桥。
    """

    def sink(message: object) -> None:
        record = getattr(message, "record", None)
        if not isinstance(record, dict):
            on_log(LogRecord(LogLevel.INFO, str(message)))
            return
        name = str(getattr(record.get("level"), "name", "") or "").upper()
        level = _LOGURU_LEVELS.get(name, LogLevel.INFO)
        extra: dict[str, str] = {}
        logger_name = record.get("name")
        if logger_name:
            extra["logger"] = str(logger_name)
        on_log(LogRecord(level, str(record.get("message", "")), extra=extra))

    return sink


def capture_task_context() -> contextvars.Context:
    """复制当前上下文，交给任务内部再开的线程。

    ``TaskRunner`` 会把提交时所在线程的上下文带进工作线程。joblib 的
    ``threading`` 后端、以及任务自己 ``Thread()`` 出来的线程不会再继承。
    在那些线程里执行前调用 ``capture_task_context().run(fn)``。
    """

    return contextvars.copy_context()


def task_log(message: str, *, level: LogLevel = LogLevel.INFO, detail: str = "") -> None:
    """任务执行期间写一行日志，任意调用深度可用，不必把 ``on_log`` 逐层传下去。

    ``TaskRunner`` 在工作函数运行期间放置收集器，日志照旧批量节流送回界面。
    任务之外调用时回退到标准库 ``logging``，直接单测工作函数不会报错。
    """

    record = LogRecord(level=level, message=str(message), detail=str(detail))
    sink = _ACTIVE_SINK.get()
    if sink is None:
        logging.getLogger("psi6.task").log(_STDLIB_LEVELS[level], record.message)
        return
    sink(record)
