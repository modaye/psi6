"""未捕获异常：写日志、发通知并弹出用户可读对话框。"""

from __future__ import annotations

import sys
import threading
import traceback
from collections.abc import Callable
from types import TracebackType
from typing import Any

from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from psi6.runtime.notifications import Notifier

_installed = False


def format_exception(exc: BaseException) -> str:
    """把异常转成短的用户可读句子。"""

    text = str(exc).strip()
    if text:
        return text
    return exc.__class__.__name__


def install_exception_hooks(
    app: QApplication,
    *,
    parent: QWidget | None = None,
    reporter: Callable[[str], None] | None = None,
    notifier: Notifier | None = None,
) -> None:
    """安装 sys / threading 异常钩子。重复调用不会叠加。"""

    global _installed
    if _installed:
        return
    _installed = True

    def _report(title: str, message: str, detail: str) -> None:
        if reporter is not None:
            reporter(f"{title}: {message}")
        if notifier is not None:
            notifier.error(message)
        box = QMessageBox(parent)
        box.setIcon(QMessageBox.Icon.Critical)
        box.setWindowTitle(title)
        box.setText(message)
        box.setDetailedText(detail)
        box.exec()

    def _hook(
        exc_type: type[BaseException],
        exc: BaseException,
        tb: TracebackType | None,
    ) -> None:
        detail = "".join(traceback.format_exception(exc_type, exc, tb))
        sys.stderr.write(detail)
        _report("未捕获异常", format_exception(exc), detail)

    def _thread_hook(args: Any) -> None:
        _hook(args.exc_type, args.exc_value, args.exc_traceback)

    def _unraisable(unraisable: Any) -> None:
        exc = getattr(unraisable, "exc_value", None)
        if isinstance(exc, BaseException):
            _hook(type(exc), exc, exc.__traceback__)

    sys.excepthook = _hook
    threading.excepthook = _thread_hook
    sys.unraisablehook = _unraisable
