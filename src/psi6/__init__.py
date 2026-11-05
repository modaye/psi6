"""psi6 框架入口。控件从 ``psi6.ui`` 导入，示例见 ``psi6.examples``。

根包用惰性导入：``import psi6`` 不会拉起 Qt 界面，``psi6.runtime.tasks``
也可以在没有 UI 的环境里单独使用。
"""

from __future__ import annotations

import importlib
from typing import Any

_LAZY: dict[str, tuple[str, str]] = {
    "App": ("psi6.runtime.app", "App"),
    "DesktopWindow": ("psi6.ui.desktop_window", "DesktopWindow"),
    "JobOutcome": ("psi6.runtime.job", "JobOutcome"),
    "TaskHandle": ("psi6.runtime.tasks", "TaskHandle"),
    "TaskRunner": ("psi6.runtime.tasks", "TaskRunner"),
    "TaskStatus": ("psi6.runtime.tasks", "TaskStatus"),
    "Theme": ("psi6.theme.theme", "Theme"),
    "TitleBar": ("psi6.ui.title_bar", "TitleBar"),
    "Tokens": ("psi6.theme.tokens", "Tokens"),
    "TrayIcon": ("psi6.ui.tray", "TrayIcon"),
    "contrast_notes": ("psi6.theme.diagnose", "contrast_notes"),
}

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
    target = _LAZY.get(name)
    if target is None:
        raise AttributeError(f"module 'psi6' has no attribute {name!r}")
    module_name, attr = target
    value = getattr(importlib.import_module(module_name), attr)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *__all__})
