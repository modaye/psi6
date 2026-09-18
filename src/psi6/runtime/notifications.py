"""用户可读通知：状态栏 + 可选 Toast。不替代对话框。"""

from __future__ import annotations

from enum import StrEnum

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QStatusBar

from psi6.ui.toast import ToastHost


class NoticeLevel(StrEnum):
    """通知级别。"""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class Notifier(QObject):
    """应用级通知器。

    ``info`` 只写状态栏，避免进度刷屏。成功/警告/错误默认再弹 Toast。
    需要决策或必须看见的错误走 ``psi6.ui.dialogs``。
    """

    posted = Signal(str, str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._status: QStatusBar | None = None
        self._toasts: ToastHost | None = None
        self._last: tuple[str, str] | None = None

    def bind_status_bar(self, bar: QStatusBar | None) -> None:
        """把通知映射到主窗口状态栏。"""

        self._status = bar

    def bind_toast_host(self, host: ToastHost | None) -> None:
        """把成功/警告/错误映射到窗口右上角 Toast。"""

        self._toasts = host

    @property
    def last(self) -> tuple[str, str] | None:
        """最近一次通知 ``(level, message)``。"""

        return self._last

    def post(
        self,
        level: NoticeLevel | str,
        message: str,
        *,
        timeout_ms: int = 6000,
        toast: bool | None = None,
    ) -> None:
        """发布一条通知。

        ``toast`` 为 ``None`` 时：``info`` 不上 Toast，其余级别上。
        """

        kind = NoticeLevel(str(level))
        self._last = (kind.value, message)
        self.posted.emit(kind.value, message)
        if self._status is not None:
            self._status.showMessage(message, timeout_ms)
        show_toast = kind is not NoticeLevel.INFO if toast is None else toast
        if show_toast and self._toasts is not None:
            self._toasts.push(message, tone=kind.value, timeout_ms=timeout_ms)

    def info(self, message: str) -> None:
        self.post(NoticeLevel.INFO, message)

    def success(self, message: str) -> None:
        self.post(NoticeLevel.SUCCESS, message)

    def warning(self, message: str) -> None:
        self.post(NoticeLevel.WARNING, message)

    def error(self, message: str) -> None:
        self.post(NoticeLevel.ERROR, message, timeout_ms=10000)
