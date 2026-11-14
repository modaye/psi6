"""运行时：应用、任务、配置、通知。

导入本包不加载 ``psi6.ui``。``App`` 的导入写在 ``__getattr__`` 里，
第一次访问 ``psi6.runtime.App`` 才进入 ``psi6.runtime.app``。

这里同样使用字面量导入，方便打包器收集模块。需要任务而不需要窗口时，
直接 ``from psi6.runtime.tasks import TaskRunner``。
"""

from __future__ import annotations

from typing import Any

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
    if name == "App":
        from psi6.runtime.app import App

        globals()["App"] = App
        return App
    if name == "ConfigMigrations":
        from psi6.runtime.config import ConfigMigrations

        globals()["ConfigMigrations"] = ConfigMigrations
        return ConfigMigrations
    if name == "ConfigStore":
        from psi6.runtime.config import ConfigStore

        globals()["ConfigStore"] = ConfigStore
        return ConfigStore
    if name == "JobOutcome":
        from psi6.runtime.job import JobOutcome

        globals()["JobOutcome"] = JobOutcome
        return JobOutcome
    if name == "LogJournal":
        from psi6.runtime.logs import LogJournal

        globals()["LogJournal"] = LogJournal
        return LogJournal
    if name == "LogLevel":
        from psi6.runtime.logs import LogLevel

        globals()["LogLevel"] = LogLevel
        return LogLevel
    if name == "LogRecord":
        from psi6.runtime.logs import LogRecord

        globals()["LogRecord"] = LogRecord
        return LogRecord
    if name == "NoticeLevel":
        from psi6.runtime.notifications import NoticeLevel

        globals()["NoticeLevel"] = NoticeLevel
        return NoticeLevel
    if name == "Notifier":
        from psi6.runtime.notifications import Notifier

        globals()["Notifier"] = Notifier
        return Notifier
    if name == "SingleInstance":
        from psi6.runtime.single_instance import SingleInstance

        globals()["SingleInstance"] = SingleInstance
        return SingleInstance
    if name == "TaskHandle":
        from psi6.runtime.tasks import TaskHandle

        globals()["TaskHandle"] = TaskHandle
        return TaskHandle
    if name == "TaskRunner":
        from psi6.runtime.tasks import TaskRunner

        globals()["TaskRunner"] = TaskRunner
        return TaskRunner
    if name == "TaskStatus":
        from psi6.runtime.tasks import TaskStatus

        globals()["TaskStatus"] = TaskStatus
        return TaskStatus
    if name == "format_exception":
        from psi6.runtime.errors import format_exception

        globals()["format_exception"] = format_exception
        return format_exception
    if name == "install_exception_hooks":
        from psi6.runtime.errors import install_exception_hooks

        globals()["install_exception_hooks"] = install_exception_hooks
        return install_exception_hooks
    if name == "uninstall_exception_hooks":
        from psi6.runtime.errors import uninstall_exception_hooks

        globals()["uninstall_exception_hooks"] = uninstall_exception_hooks
        return uninstall_exception_hooks
    if name == "instance_key":
        from psi6.runtime.single_instance import instance_key

        globals()["instance_key"] = instance_key
        return instance_key
    if name == "restore_window":
        from psi6.runtime.window_state import restore_window

        globals()["restore_window"] = restore_window
        return restore_window
    if name == "save_window":
        from psi6.runtime.window_state import save_window

        globals()["save_window"] = save_window
        return save_window
    raise AttributeError(f"module 'psi6.runtime' has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted({*globals(), *__all__})
