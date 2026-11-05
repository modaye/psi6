"""未捕获异常：写日志、发通知并弹出用户可读对话框。

对话框只在界面线程创建。工作线程的钩子只把纯文本排队过来。
"""

from __future__ import annotations

import sys
import threading
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from types import TracebackType
from typing import Any

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from psi6.runtime.notifications import Notifier
from psi6.runtime.qt_alive import qt_alive

_bridge: _ExceptionBridge | None = None
_saved_hooks: tuple[Any, Any, Any] | None = None


@dataclass(frozen=True)
class _Binding:
    parent: QWidget | None
    notifier: Notifier | None
    reporter: Callable[[str], None] | None


_bindings: dict[Any, _Binding] = {}


def format_exception(exc: BaseException) -> str:
    """把异常转成短的用户可读句子。"""

    text = str(exc).strip()
    if text:
        return text
    return exc.__class__.__name__


class _ExceptionBridge(QObject):
    """把异常文本从任意线程送到创建本对象的界面线程。"""

    _queued = Signal(str, str, str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._parent: QWidget | None = None
        self._notifier: Notifier | None = None
        self._reporter: Callable[[str], None] | None = None
        self._queued.connect(self._show, Qt.ConnectionType.QueuedConnection)

    def bind(
        self,
        *,
        parent: QWidget | None,
        notifier: Notifier | None,
        reporter: Callable[[str], None] | None,
    ) -> None:
        """换窗口或再建一个 App 时改绑，不叠加钩子。"""

        self._parent = parent
        self._notifier = notifier
        self._reporter = reporter

    def deliver(self, title: str, message: str, detail: str) -> None:
        app = QApplication.instance()
        if app is None or not isinstance(app, QApplication):
            sys.stderr.write(detail)
            return
        if QThread.currentThread() is app.thread():
            self._show(title, message, detail)
            return
        self._queued.emit(title, message, detail)

    def _show(self, title: str, message: str, detail: str) -> None:
        try:
            if self._reporter is not None:
                self._reporter(f"{title}: {message}")
            if self._notifier is not None:
                self._notifier.error(message)
            parent = self._parent if self._parent is not None and qt_alive(self._parent) else None
            box = QMessageBox(parent)
            box.setIcon(QMessageBox.Icon.Critical)
            box.setWindowTitle(title)
            box.setText(message)
            box.setDetailedText(detail)
            box.exec()
        except RuntimeError:
            sys.stderr.write(detail)


def install_exception_hooks(
    app: QApplication,
    *,
    parent: QWidget | None = None,
    reporter: Callable[[str], None] | None = None,
    notifier: Notifier | None = None,
    owner: Any = None,
) -> None:
    """安装 sys / threading / unraisable 钩子。

    ``owner`` 默认是 ``app``；同一 ``owner`` 重复安装只改绑窗口。多个 ``owner``
    并存时，最后安装的那个接收异常，退出时各自摘掉自己的绑定。
    """

    global _bridge, _saved_hooks
    if _bridge is None:
        _bridge = _ExceptionBridge(app)
    owner = app if owner is None else owner
    _bindings.pop(owner, None)
    _bindings[owner] = _Binding(parent=parent, notifier=notifier, reporter=reporter)
    _bridge.bind(parent=parent, notifier=notifier, reporter=reporter)
    if _saved_hooks is None:
        _saved_hooks = (sys.excepthook, threading.excepthook, sys.unraisablehook)
    sys.excepthook = _hook
    threading.excepthook = _thread_hook
    sys.unraisablehook = _unraisable


def uninstall_exception_hooks(owner: Any = None) -> None:
    """撤掉一个 ``owner`` 的绑定；不传 ``owner`` 时强制还原全部钩子。

    先退出的 App 只摘掉自己，剩下的 App 继续接收异常。没有绑定剩下时才恢复
    进程原来的钩子，测试和退出收尾都能直接调用。
    """

    global _bridge, _saved_hooks
    if owner is None:
        _bindings.clear()
    else:
        _bindings.pop(owner, None)
    if _bindings:
        active = next(reversed(_bindings.values()))
        if _bridge is not None:
            _bridge.bind(
                parent=active.parent,
                notifier=active.notifier,
                reporter=active.reporter,
            )
        return
    if _saved_hooks is not None:
        sys.excepthook, threading.excepthook, sys.unraisablehook = _saved_hooks
        _saved_hooks = None
    if _bridge is not None:
        _bridge.bind(parent=None, notifier=None, reporter=None)
        _bridge.deleteLater()
        _bridge = None


def _hook(
    exc_type: type[BaseException],
    exc: BaseException,
    tb: TracebackType | None,
) -> None:
    detail = "".join(traceback.format_exception(exc_type, exc, tb))
    sys.stderr.write(detail)
    if _bridge is None:
        return
    _bridge.deliver("未捕获异常", format_exception(exc), detail)


def _thread_hook(args: Any) -> None:
    _hook(args.exc_type, args.exc_value, args.exc_traceback)


def _unraisable(unraisable: Any) -> None:
    exc = getattr(unraisable, "exc_value", None)
    if isinstance(exc, BaseException):
        _hook(type(exc), exc, exc.__traceback__)
