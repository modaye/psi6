"""运行时：应用、任务、配置、通知。

导入本包不加载 ``psi6.ui``。需要 ``App`` 时再导入组合根
``psi6.runtime.app``，它负责把主题、托盘和 Toast 接到 Qt 上。
"""

from __future__ import annotations

import importlib
from typing import Any

_LAZY: dict[str, tuple[str, str]] = {
    "App": ("psi6.runtime.app", "App"),
    "ConfigMigrations": ("psi6.runtime.config", "ConfigMigrations"),
    "ConfigStore": ("psi6.runtime.config", "ConfigStore"),
    "JobOutcome": ("psi6.runtime.job", "JobOutcome"),
    "LogJournal": ("psi6.runtime.logs", "LogJournal"),
    "LogLevel": ("psi6.runtime.logs", "LogLevel"),
    "LogRecord": ("psi6.runtime.logs", "LogRecord"),
    "NoticeLevel": ("psi6.runtime.notifications", "NoticeLevel"),
    "Notifier": ("psi6.runtime.notifications", "Notifier"),
    "SingleInstance": ("psi6.runtime.single_instance", "SingleInstance"),
    "TaskHandle": ("psi6.runtime.tasks", "TaskHandle"),
    "TaskRunner": ("psi6.runtime.tasks", "TaskRunner"),
    "TaskStatus": ("psi6.runtime.tasks", "TaskStatus"),
    "format_exception": ("psi6.runtime.errors", "format_exception"),
    "install_exception_hooks": ("psi6.runtime.errors", "install_exception_hooks"),
    "uninstall_exception_hooks": ("psi6.runtime.errors", "uninstall_exception_hooks"),
    "instance_key": ("psi6.runtime.single_instance", "instance_key"),
    "restore_window": ("psi6.runtime.window_state", "restore_window"),
    "save_window": ("psi6.runtime.window_state", "save_window"),
}

__all__ = [
    "App",
    "ConfigMigrations",
    "ConfigStore",
    "JobOutcome",
    "LogJournal",
    "LogLevel",
    "LogRecord",
    "NoticeLevel",
    "Notifier",
    "SingleInstance",
    "TaskHandle",
    "TaskRunner",
    "TaskStatus",
    "format_exception",
    "install_exception_hooks",
    "instance_key",
    "restore_window",
    "save_window",
    "uninstall_exception_hooks",
]


def __getattr__(name: str) -> Any:
    target = _LAZY.get(name)
    if target is None:
        raise AttributeError(f"module 'psi6.runtime' has no attribute {name!r}")
    module_name, attr = target
    value = getattr(importlib.import_module(module_name), attr)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *__all__})
