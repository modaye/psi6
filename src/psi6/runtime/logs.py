"""任务过程日志的数据结构。与诊断日志（如 loguru）分离。"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class LogLevel(StrEnum):
    """操作日志级别。"""

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
