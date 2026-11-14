"""psi6 框架入口。控件从 ``psi6.ui`` 导入，示例见 ``psi6.examples``。

稳定名字仍是 ``from psi6 import App``。每个名字在下面的 ``__getattr__`` 里用
字面量 ``from 模块 import 名字`` 引入，所以：

- ``import psi6`` 不会执行这些导入，没有界面的进程可以继续用 ``psi6.runtime.tasks``。
- 静态分析（包括 PyInstaller）能看见模块名。不要改回 ``importlib.import_module(变量)``，
  变量里的模块名不会被打进包。

定义处：

- ``App`` → ``psi6.runtime.app``
- ``TaskRunner`` / ``TaskHandle`` / ``TaskStatus`` → ``psi6.runtime.tasks``
- ``JobOutcome`` → ``psi6.runtime.job``
- ``Theme`` → ``psi6.theme.theme``
- ``Tokens`` → ``psi6.theme.tokens``
- ``contrast_notes`` → ``psi6.theme.diagnose``
- ``DesktopWindow`` → ``psi6.ui.desktop_window``
- ``TitleBar`` → ``psi6.ui.title_bar``
- ``TrayIcon`` → ``psi6.ui.tray``
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "App",
    "DesktopWindow",
    "JobOutcome",
    "TaskHandle",
    "TaskRunner",
    "TaskStatus",
    "Theme",
    "TitleBar",
    "Tokens",
    "TrayIcon",
    "contrast_notes",
]


def __getattr__(name: str) -> Any:
    if name == "App":
        from psi6.runtime.app import App

        globals()["App"] = App
        return App
    if name == "DesktopWindow":
        from psi6.ui.desktop_window import DesktopWindow

        globals()["DesktopWindow"] = DesktopWindow
        return DesktopWindow
    if name == "JobOutcome":
        from psi6.runtime.job import JobOutcome

        globals()["JobOutcome"] = JobOutcome
        return JobOutcome
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
    if name == "Theme":
        from psi6.theme.theme import Theme

        globals()["Theme"] = Theme
        return Theme
    if name == "TitleBar":
        from psi6.ui.title_bar import TitleBar

        globals()["TitleBar"] = TitleBar
        return TitleBar
    if name == "Tokens":
        from psi6.theme.tokens import Tokens

        globals()["Tokens"] = Tokens
        return Tokens
    if name == "TrayIcon":
        from psi6.ui.tray import TrayIcon

        globals()["TrayIcon"] = TrayIcon
        return TrayIcon
    if name == "contrast_notes":
        from psi6.theme.diagnose import contrast_notes

        globals()["contrast_notes"] = contrast_notes
        return contrast_notes
    raise AttributeError(f"module 'psi6' has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted({*globals(), *__all__})
