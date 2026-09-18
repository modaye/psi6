"""后台任务：UI 线程只提交，工作在线程池中执行。"""

from __future__ import annotations

import inspect
import itertools
import threading
import time
import traceback
import uuid
from collections.abc import Callable
from enum import StrEnum
from typing import Any

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal, Slot

from psi6.runtime.errors import format_exception
from psi6.runtime.logs import LogRecord


class TaskStatus(StrEnum):
    """任务生命周期。"""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskHandle:
    """一次 ``submit`` 的句柄。取消是协作式的，不会 ``terminate`` 线程。"""

    def __init__(
        self,
        job_id: str,
        cancel_flag: threading.Event,
        *,
        exclusive: str | None = None,
    ) -> None:
        self.id = job_id
        self.exclusive = exclusive
        self._cancel_flag = cancel_flag
        self._status = TaskStatus.QUEUED
        self._result: Any = None
        self._error_message: str | None = None
        self._error_traceback: str | None = None
        self._lock = threading.Lock()

    @property
    def status(self) -> TaskStatus:
        with self._lock:
            return self._status

    @property
    def result(self) -> Any:
        with self._lock:
            return self._result

    @property
    def error_message(self) -> str | None:
        """给用户看的失败原因，不含堆栈。"""

        with self._lock:
            return self._error_message

    @property
    def error_traceback(self) -> str | None:
        with self._lock:
            return self._error_traceback

    def _set_status(self, status: TaskStatus) -> None:
        with self._lock:
            self._status = status

    def _set_result(self, value: Any) -> None:
        with self._lock:
            self._result = value

    def _set_error(self, message: str, traceback_text: str) -> None:
        with self._lock:
            self._error_message = message
            self._error_traceback = traceback_text

    def cancel(self) -> None:
        """请求取消。工作函数需检查 ``is_cancelled`` 后自行退出。"""

        self._cancel_flag.set()


class _JobSignals(QObject):
    """跨线程信号，必须挂在 QObject 上才能走 QueuedConnection。"""

    progress = Signal(str, int, int, str)
    log = Signal(str, object)
    succeeded = Signal(str, object)
    failed = Signal(str, str, str)
    cancelled = Signal(str)


class _JobRunnable(QRunnable):
    """在线程池里执行任意可调用对象。"""

    def __init__(
        self,
        job_id: str,
        fn: Callable[..., Any],
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        signals: _JobSignals,
        cancel_flag: threading.Event,
        inject: dict[str, Any],
    ) -> None:
        super().__init__()
        self._job_id = job_id
        self._fn = fn
        self._args = args
        self._kwargs = kwargs
        self._signals = signals
        self._cancel_flag = cancel_flag
        self._inject = inject
        self.setAutoDelete(True)

    @Slot()
    def run(self) -> None:
        if self._cancel_flag.is_set():
            self._emit_cancelled()
            return
        try:
            kwargs = dict(self._kwargs)
            kwargs.update(self._inject)
            result = self._fn(*self._args, **kwargs)
            if self._cancel_flag.is_set():
                self._emit_cancelled()
                return
            self._signals.succeeded.emit(self._job_id, result)
        except InterruptedError:
            self._emit_cancelled()
        except Exception as exc:  # noqa: BLE001 — 边界捕获，经信号回主线程
            if self._cancel_flag.is_set():
                self._emit_cancelled()
                return
            self._signals.failed.emit(
                self._job_id,
                format_exception(exc),
                traceback.format_exc(),
            )

    def _emit_cancelled(self) -> None:
        try:
            self._signals.cancelled.emit(self._job_id)
        except RuntimeError:
            pass


def _accepts(fn: Callable[..., Any], name: str) -> bool:
    try:
        params = inspect.signature(fn).parameters
    except (TypeError, ValueError):
        return False
    return name in params


class TaskRunner(QObject):
    """UI 线程提交任务；工作在 ``QThreadPool``。禁止 ``QThread.terminate``。"""

    def __init__(self, max_threads: int = 3, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(max(1, max_threads))
        self._seq = itertools.count(1)
        self._jobs: dict[str, TaskHandle] = {}
        self._signals: dict[str, _JobSignals] = {}
        self._slots: dict[str, TaskHandle] = {}
        self._lock = threading.Lock()

    def active_handles(self) -> list[TaskHandle]:
        """尚未结束的任务。"""

        with self._lock:
            return list(self._jobs.values())

    def is_busy(self, exclusive: str | None = None) -> bool:
        """是否有任务在跑。给出 ``exclusive`` 则只看该槽。"""

        with self._lock:
            if exclusive is None:
                return bool(self._jobs)
            handle = self._slots.get(exclusive)
            return handle is not None and handle.status in {TaskStatus.QUEUED, TaskStatus.RUNNING}

    def cancel_all(self) -> None:
        """协作式取消全部进行中的任务。"""

        for handle in self.active_handles():
            handle.cancel()

    def shutdown(self, timeout_ms: int = 8000) -> bool:
        """取消未完成任务并等待线程池结束。返回是否在超时前排空。"""

        self.cancel_all()
        return bool(self._pool.waitForDone(timeout_ms))

    def submit(
        self,
        fn: Callable[..., Any],
        *args: Any,
        on_progress: Callable[[int, int, str], None] | None = None,
        on_log: Callable[[LogRecord], None] | None = None,
        on_succeeded: Callable[[Any], None] | None = None,
        on_failed: Callable[[str], None] | None = None,
        on_cancelled: Callable[[], None] | None = None,
        exclusive: str | None = None,
        progress_interval_ms: int = 50,
        log_interval_ms: int = 50,
        **kwargs: Any,
    ) -> TaskHandle:
        """从 UI 线程提交后台任务。

        若 ``fn`` 声明了 ``on_progress`` / ``on_log`` / ``is_cancelled``，
        由运行器注入，不必由调用方手动传递。
        ``on_failed`` 收到用户可读短句；完整堆栈在 ``TaskHandle.error_traceback``。
        ``exclusive`` 占用同名槽位：已有任务在跑则返回那个句柄，不启动第二份。
        进度只保留间隔内最新一条；日志按间隔批量送回 UI，结束时冲刷剩余。
        """

        if exclusive:
            with self._lock:
                current = self._slots.get(exclusive)
            if current is not None and current.status in {TaskStatus.QUEUED, TaskStatus.RUNNING}:
                return current

        job_id = f"job-{next(self._seq)}-{uuid.uuid4().hex[:8]}"
        cancel_flag = threading.Event()
        handle = TaskHandle(job_id, cancel_flag, exclusive=exclusive)
        signals = _JobSignals(self)

        signals.progress.connect(
            lambda jid, current, total, message, expected=job_id: (
                on_progress(current, total, message)
                if on_progress is not None and jid == expected
                else None
            ),
            Qt.ConnectionType.QueuedConnection,
        )
        signals.log.connect(
            lambda jid, record, expected=job_id: (
                on_log(record) if on_log is not None and jid == expected else None
            ),
            Qt.ConnectionType.QueuedConnection,
        )
        signals.succeeded.connect(
            lambda jid, result, expected=job_id, cb=on_succeeded: (
                self._finish(expected, TaskStatus.SUCCEEDED, cb, result)
                if jid == expected
                else None
            ),
            Qt.ConnectionType.QueuedConnection,
        )
        signals.failed.connect(
            lambda jid, message, tb, expected=job_id, cb=on_failed: (
                self._finish(
                    expected,
                    TaskStatus.FAILED,
                    cb,
                    message,
                    traceback_text=tb,
                )
                if jid == expected
                else None
            ),
            Qt.ConnectionType.QueuedConnection,
        )
        signals.cancelled.connect(
            lambda jid, expected=job_id, cb=on_cancelled: (
                self._finish(expected, TaskStatus.CANCELLED, cb, None)
                if jid == expected
                else None
            ),
            Qt.ConnectionType.QueuedConnection,
        )

        progress_gap = max(0, progress_interval_ms) / 1000
        log_gap = max(0, log_interval_ms) / 1000
        last_progress = 0.0
        pending_progress: tuple[int, int, str] | None = None
        log_buffer: list[LogRecord] = []
        last_log = 0.0

        def emit_progress(current: int, total: int, message: str) -> None:
            nonlocal last_progress, pending_progress
            if cancel_flag.is_set():
                return
            now = time.monotonic()
            final = total > 0 and current >= total
            if progress_gap > 0 and not final and now - last_progress < progress_gap:
                pending_progress = (current, total, message)
                return
            pending_progress = None
            last_progress = now
            signals.progress.emit(job_id, current, total, message)

        def flush_progress() -> None:
            nonlocal pending_progress, last_progress
            if pending_progress is None or cancel_flag.is_set():
                return
            current, total, message = pending_progress
            pending_progress = None
            last_progress = time.monotonic()
            signals.progress.emit(job_id, current, total, message)

        def flush_logs() -> None:
            nonlocal last_log
            if not log_buffer:
                return
            records = list(log_buffer)
            log_buffer.clear()
            last_log = time.monotonic()
            for record in records:
                if not cancel_flag.is_set():
                    signals.log.emit(job_id, record)

        def emit_log(record: LogRecord) -> None:
            if cancel_flag.is_set():
                return
            log_buffer.append(record)
            now = time.monotonic()
            if log_gap <= 0 or now - last_log >= log_gap:
                flush_logs()

        def wrapped(*call_args: Any, **call_kwargs: Any) -> Any:
            try:
                return fn(*call_args, **call_kwargs)
            finally:
                flush_progress()
                flush_logs()

        inject: dict[str, Any] = {}
        if _accepts(fn, "on_progress"):
            inject["on_progress"] = emit_progress
        if _accepts(fn, "on_log"):
            inject["on_log"] = emit_log
        if _accepts(fn, "is_cancelled"):
            inject["is_cancelled"] = cancel_flag.is_set

        with self._lock:
            self._jobs[job_id] = handle
            self._signals[job_id] = signals
            if exclusive:
                self._slots[exclusive] = handle

        handle._set_status(TaskStatus.RUNNING)
        runnable = _JobRunnable(job_id, wrapped, args, kwargs, signals, cancel_flag, inject)
        self._pool.start(runnable)
        return handle

    def _finish(
        self,
        job_id: str,
        status: TaskStatus,
        callback: Callable[..., Any] | None,
        payload: Any,
        traceback_text: str | None = None,
    ) -> None:
        handle = self._jobs.get(job_id)
        if handle is not None:
            handle._set_status(status)
            if status is TaskStatus.SUCCEEDED:
                handle._set_result(payload)
            elif status is TaskStatus.FAILED and isinstance(payload, str):
                handle._set_error(payload, traceback_text or "")
        if callback is not None:
            if status is TaskStatus.CANCELLED:
                callback()
            else:
                callback(payload)
        with self._lock:
            self._jobs.pop(job_id, None)
            self._signals.pop(job_id, None)
            if handle is not None and handle.exclusive:
                current = self._slots.get(handle.exclusive)
                if current is handle:
                    self._slots.pop(handle.exclusive, None)
