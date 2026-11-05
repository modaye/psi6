"""后台任务：UI 线程只提交，工作在线程池中执行。

``TaskRunner`` 是唯一的执行器：提交、进度、日志、取消、并发槽都在这里。
``TaskHandle.status`` 是一次任务的状态。``JobOutcome`` 只描述批处理成功后的表格结果，
不是第二套执行状态。界面自己组合，不另建调度器。
"""

from __future__ import annotations

import contextlib
import contextvars
import inspect
import itertools
import threading
import time
import traceback
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from PySide6.QtCore import (
    QCoreApplication,
    QEvent,
    QObject,
    QRunnable,
    Qt,
    QThreadPool,
    Signal,
    Slot,
)

from psi6.runtime.errors import format_exception
from psi6.runtime.logs import _ACTIVE_SINK, LogJournal, LogRecord


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
        self._progress: tuple[int, int, str] | None = None
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

    @property
    def progress(self) -> tuple[int, int, str] | None:
        """最近一次进度 ``(current, total, message)``。还没有进度时是 ``None``。

        界面回调仍按间隔节流，这里保留每一次上报里的最新值。
        """

        with self._lock:
            return self._progress

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

    def _set_progress(self, current: int, total: int, message: str) -> None:
        with self._lock:
            self._progress = (current, total, message)

    @property
    def cancel_requested(self) -> bool:
        """是否已请求取消。``status`` 要等工作函数结束才变成 ``cancelled``。"""

        return self._cancel_flag.is_set()

    def cancel(self) -> None:
        """请求取消。不会 ``terminate`` 线程。工作函数需检查 ``is_cancelled`` 后自行退出。"""

        self._cancel_flag.set()


class _JobSignals(QObject):
    """跨线程信号，必须挂在 QObject 上才能走 QueuedConnection。

    每个 ``TaskRunner`` 只有一个信号对象，任务靠 ``job_id`` 分流；结束后不删除，
    子对象数量不会随任务数增长。
    """

    progress = Signal(str, int, int, str)
    log = Signal(str, object)
    started = Signal(str)
    succeeded = Signal(str, object)
    failed = Signal(str, str, str, object)
    cancelled = Signal(str)


@dataclass(slots=True)
class _JobCallbacks:
    on_progress: Callable[..., None] | None = None
    on_log: Callable[..., None] | None = None
    on_succeeded: Callable[..., None] | None = None
    on_failed: Callable[..., None] | None = None
    on_cancelled: Callable[..., None] | None = None
    on_finished: Callable[..., None] | None = None


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
        context: contextvars.Context,
        handle: TaskHandle,
    ) -> None:
        super().__init__()
        self._job_id = job_id
        self._fn = fn
        self._args = args
        self._kwargs = kwargs
        self._signals = signals
        self._cancel_flag = cancel_flag
        self._inject = inject
        self._context = context
        self._handle = handle
        self.setAutoDelete(True)

    @Slot()
    def run(self) -> None:
        self._context.run(self._run_in_context)

    def _run_in_context(self) -> None:
        if self._cancel_flag.is_set():
            self._emit_cancelled()
            return
        self._handle._set_status(TaskStatus.RUNNING)
        _safe_emit(self._signals.started, self._job_id)
        try:
            kwargs = dict(self._kwargs)
            kwargs.update(self._inject)
            result = self._fn(*self._args, **kwargs)
            if self._cancel_flag.is_set():
                self._emit_cancelled()
                return
            _safe_emit(self._signals.succeeded, self._job_id, result)
        except InterruptedError:
            self._emit_cancelled()
        except BaseException as exc:
            if self._cancel_flag.is_set():
                self._emit_cancelled()
                return
            _safe_emit(
                self._signals.failed,
                self._job_id,
                format_exception(exc),
                traceback.format_exc(),
                exc,
            )

    def _emit_cancelled(self) -> None:
        _safe_emit(self._signals.cancelled, self._job_id)


def _safe_emit(signal: Any, *args: Any) -> None:
    """工作线程发信号。运行器已经销毁时 Qt 抛 RuntimeError，任务线程不能因此崩掉。"""

    with contextlib.suppress(RuntimeError):
        signal.emit(*args)


def _invoke(callback: Callable[..., Any], *args: Any) -> None:
    """调用回到 UI 的回调。控件已销毁时 PySide 会抛 RuntimeError，这里吞掉这一类。"""

    try:
        callback(*args)
    except RuntimeError as exc:
        text = str(exc).lower()
        if "deleted" in text or "destroyed" in text:
            return
        raise


def _dispatch(callback: Callable[..., Any], *args: Any) -> None:
    """进度、日志和收尾回调的统一出口。回调出错只记到 stderr，不碰任务状态。"""

    try:
        _invoke(callback, *args)
    except Exception:
        traceback.print_exc()


def _accepts(fn: Callable[..., Any], name: str) -> bool:
    try:
        params = inspect.signature(fn).parameters
    except (TypeError, ValueError):
        return False
    return name in params


def _positional_capacity(callback: Callable[..., Any]) -> int:
    """回调能收几个位置参数，最多算到 3。签名取不到按 1，老回调不受影响。"""

    try:
        params = list(inspect.signature(callback).parameters.values())
    except (TypeError, ValueError):
        return 1
    if any(p.kind is inspect.Parameter.VAR_POSITIONAL for p in params):
        return 3
    positional = {
        inspect.Parameter.POSITIONAL_ONLY,
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
    }
    return min(3, sum(1 for p in params if p.kind in positional))


class TaskRunner(QObject):
    """UI 线程提交任务；工作在 ``QThreadPool``。禁止 ``QThread.terminate``。

    ``started`` / ``finished`` 在界面线程发出，参数是这一次的 ``TaskHandle``。
    """

    started = Signal(object)
    finished = Signal(object)

    def __init__(self, max_threads: int = 3, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(max(1, max_threads))
        self._seq = itertools.count(1)
        self._jobs: dict[str, TaskHandle] = {}
        self._callbacks: dict[str, _JobCallbacks] = {}
        self._slots: dict[str, TaskHandle] = {}
        self._accepting = True
        self._lock = threading.Lock()
        self._bus = _JobSignals(self)
        self._bus.progress.connect(self._on_progress, Qt.ConnectionType.QueuedConnection)
        self._bus.log.connect(self._on_log, Qt.ConnectionType.QueuedConnection)
        self._bus.started.connect(self._on_started, Qt.ConnectionType.QueuedConnection)
        self._bus.succeeded.connect(self._on_succeeded, Qt.ConnectionType.QueuedConnection)
        self._bus.failed.connect(self._on_failed, Qt.ConnectionType.QueuedConnection)
        self._bus.cancelled.connect(self._on_cancelled, Qt.ConnectionType.QueuedConnection)

    def active_handles(self) -> list[TaskHandle]:
        """尚未结束的任务。"""

        with self._lock:
            return list(self._jobs.values())

    def is_busy(self, exclusive: str | None = None) -> bool:
        """是否有任务在跑。给出 ``exclusive`` 则只看该槽。"""

        with self._lock:
            if exclusive is None:
                return bool(self._jobs)
            return self._slots.get(exclusive) is not None

    def cancel_all(self) -> None:
        """协作式取消全部进行中的任务。"""

        for handle in self.active_handles():
            handle.cancel()

    def shutdown(self, timeout_ms: int = 8000) -> bool:
        """对未完成任务请求取消并等待线程池。返回是否在超时前排空。

        超时返回 ``False`` 时线程仍在运行，不会被强制结束。一旦调用，就不再接受
        ``submit``。线程结束后先把已排队的进度、日志和收尾回调送回界面，再返回。
        """

        with self._lock:
            self._accepting = False
        self.cancel_all()
        if not self._pool.waitForDone(timeout_ms):
            return False
        self._drain_posted_events()
        return True

    def _drain_posted_events(self) -> None:
        """``waitForDone`` 只表示线程结束，QueuedConnection 还在事件队列里。"""

        for _ in range(16):
            if not self.active_handles():
                return
            QCoreApplication.sendPostedEvents(None, QEvent.Type.MetaCall)

    def submit(
        self,
        fn: Callable[..., Any],
        *args: Any,
        on_progress: Callable[[int, int, str], None] | None = None,
        on_log: Callable[[LogRecord], None] | None = None,
        on_succeeded: Callable[[Any], None] | None = None,
        on_failed: Callable[..., None] | None = None,
        on_cancelled: Callable[[], None] | None = None,
        on_busy: Callable[[], None] | None = None,
        on_finished: Callable[[], None] | None = None,
        exclusive: str | None = None,
        progress_interval_ms: int = 50,
        log_interval_ms: int = 50,
        journal: LogJournal | None = None,
        **kwargs: Any,
    ) -> TaskHandle:
        """从 UI 线程提交后台任务。

        若 ``fn`` 声明了 ``on_progress`` / ``on_log`` / ``is_cancelled``，
        由运行器注入，不必由调用方手动传递。任务内部任意深度可用
        ``psi6.runtime.logs.task_log`` 写日志；其它线程调用注入的 ``on_log``
        是安全的，缓冲有锁。提交线程上的 ``ContextVar`` 会带进这次任务。
        任务内部再开的线程不会自动继承，用 ``capture_task_context().run(...)``。
        ``on_failed`` 收到用户可读短句；声明第二个位置参数时同时收到原异常对象，
        第三个位置参数再带堆栈文本。
        ``exclusive`` 占用同名槽位：已有任务在跑则返回那个句柄，不启动第二份。
        被槽位挡下时若给了 ``on_busy`` 会同步触发一次；按钮禁用仍由界面自己负责。
        ``on_finished`` 在成功、失败、取消任一收尾后都执行一次，
        即使前面的回调自己抛错；被槽位挡下的提交不触发。
        回调抛错只会打印到 stderr。任务登记和互斥槽仍会清掉。
        句柄先是 ``queued``，工作函数真正开始才变成 ``running``。
        排队期间 ``cancel()`` 不会要求它先进入 ``running``。
        进度只保留间隔内最新一条；日志按间隔批量送回 UI，结束时冲刷剩余。
        ``TaskHandle.progress`` 仍是每一次上报里的最新值。
        ``journal`` 在工作线程把每条日志交给 ``LogJournal`` 排队落盘，不占用界面线程。
        同一条仍会经 ``on_log`` 回到界面；不要把 journal 再当作 ``on_log``，否则会写两遍。
        ``on_finished`` 不声明参数时仍无参调用。声明一个位置参数时收到这次的 ``TaskHandle``。
        ``shutdown`` 之后再提交会抛 ``RuntimeError``。
        """

        job_id = f"job-{next(self._seq)}-{uuid.uuid4().hex[:8]}"
        cancel_flag = threading.Event()
        handle = TaskHandle(job_id, cancel_flag, exclusive=exclusive)
        signals = self._bus

        progress_gap = max(0, progress_interval_ms) / 1000
        log_gap = max(0, log_interval_ms) / 1000
        last_progress = 0.0
        pending_progress: tuple[int, int, str] | None = None
        log_buffer: list[LogRecord] = []
        last_log = 0.0
        progress_lock = threading.Lock()
        log_lock = threading.Lock()

        def emit_progress(current: int, total: int, message: str) -> None:
            nonlocal last_progress, pending_progress
            handle._set_progress(current, total, message)
            now = time.monotonic()
            final = total > 0 and current >= total
            with progress_lock:
                if progress_gap > 0 and not final and now - last_progress < progress_gap:
                    pending_progress = (current, total, message)
                    return
                pending_progress = None
                last_progress = now
            _safe_emit(signals.progress, job_id, current, total, message)

        def flush_progress() -> None:
            nonlocal pending_progress, last_progress
            with progress_lock:
                if pending_progress is None:
                    return
                current, total, message = pending_progress
                pending_progress = None
                last_progress = time.monotonic()
            _safe_emit(signals.progress, job_id, current, total, message)

        def flush_logs() -> None:
            nonlocal last_log
            with log_lock:
                if not log_buffer:
                    return
                records = list(log_buffer)
                log_buffer.clear()
                last_log = time.monotonic()
            for record in records:
                _safe_emit(signals.log, job_id, record)

        def emit_log(record: LogRecord) -> None:
            if journal is not None:
                journal.write(record)
            with log_lock:
                log_buffer.append(record)
                due = log_gap <= 0 or time.monotonic() - last_log >= log_gap
            if due:
                flush_logs()

        def wrapped(*call_args: Any, **call_kwargs: Any) -> Any:
            token = _ACTIVE_SINK.set(emit_log)
            try:
                return fn(*call_args, **call_kwargs)
            finally:
                _ACTIVE_SINK.reset(token)
                flush_progress()
                flush_logs()

        inject: dict[str, Any] = {}
        if _accepts(fn, "on_progress"):
            inject["on_progress"] = emit_progress
        if _accepts(fn, "on_log"):
            inject["on_log"] = emit_log
        if _accepts(fn, "is_cancelled"):
            inject["is_cancelled"] = cancel_flag.is_set

        callbacks = _JobCallbacks(
            on_progress=on_progress,
            on_log=on_log,
            on_succeeded=on_succeeded,
            on_failed=on_failed,
            on_cancelled=on_cancelled,
            on_finished=on_finished,
        )
        with self._lock:
            if not self._accepting:
                raise RuntimeError("TaskRunner 已关闭，不能再提交任务")
            if exclusive:
                current = self._slots.get(exclusive)
                if current is not None:
                    rejected: TaskHandle | None = current
                else:
                    rejected = None
                    self._slots[exclusive] = handle
            else:
                rejected = None
            if rejected is None:
                self._jobs[job_id] = handle
                self._callbacks[job_id] = callbacks
        if rejected is not None:
            if on_busy is not None:
                _invoke(on_busy)
            return rejected

        runnable = _JobRunnable(
            job_id,
            wrapped,
            args,
            kwargs,
            signals,
            cancel_flag,
            inject,
            contextvars.copy_context(),
            handle,
        )
        self._pool.start(runnable)
        return handle

    @Slot(str)
    def _on_started(self, job_id: str) -> None:
        with self._lock:
            handle = self._jobs.get(job_id)
        if handle is not None:
            self.started.emit(handle)

    @Slot(str, int, int, str)
    def _on_progress(self, job_id: str, current: int, total: int, message: str) -> None:
        with self._lock:
            callbacks = self._callbacks.get(job_id)
        if callbacks is not None and callbacks.on_progress is not None:
            _dispatch(callbacks.on_progress, current, total, message)

    @Slot(str, object)
    def _on_log(self, job_id: str, record: LogRecord) -> None:
        with self._lock:
            callbacks = self._callbacks.get(job_id)
        if callbacks is not None and callbacks.on_log is not None:
            _dispatch(callbacks.on_log, record)

    @Slot(str, object)
    def _on_succeeded(self, job_id: str, result: Any) -> None:
        self._finish(job_id, TaskStatus.SUCCEEDED, result)

    @Slot(str, str, str, object)
    def _on_failed(
        self,
        job_id: str,
        message: str,
        traceback_text: str,
        exception: BaseException,
    ) -> None:
        self._finish(
            job_id,
            TaskStatus.FAILED,
            message,
            traceback_text=traceback_text,
            exception=exception,
        )

    @Slot(str)
    def _on_cancelled(self, job_id: str) -> None:
        self._finish(job_id, TaskStatus.CANCELLED, None)

    def _finish(
        self,
        job_id: str,
        status: TaskStatus,
        payload: Any,
        traceback_text: str | None = None,
        exception: BaseException | None = None,
    ) -> None:
        with self._lock:
            handle = self._jobs.get(job_id)
            callbacks = self._callbacks.get(job_id)
        if handle is not None:
            handle._set_status(status)
            if status is TaskStatus.SUCCEEDED:
                handle._set_result(payload)
            elif status is TaskStatus.FAILED and isinstance(payload, str):
                handle._set_error(payload, traceback_text or "")
        # 先释放登记和互斥槽，回调里才能立刻重新提交同一槽位。
        self._release(job_id, handle)
        if callbacks is not None:
            self._deliver(status, callbacks, payload, traceback_text, exception, handle)
        if handle is not None:
            self.finished.emit(handle)

    def _deliver(
        self,
        status: TaskStatus,
        callbacks: _JobCallbacks,
        payload: Any,
        traceback_text: str | None,
        exception: BaseException | None,
        handle: TaskHandle | None,
    ) -> None:
        if status is TaskStatus.CANCELLED:
            if callbacks.on_cancelled is not None:
                _dispatch(callbacks.on_cancelled)
        elif status is TaskStatus.FAILED:
            callback = callbacks.on_failed
            if callback is not None:
                if exception is not None:
                    capacity = _positional_capacity(callback)
                    if capacity >= 3:
                        _dispatch(callback, payload, exception, traceback_text or "")
                    elif capacity == 2:
                        _dispatch(callback, payload, exception)
                    else:
                        _dispatch(callback, payload)
                else:
                    _dispatch(callback, payload)
        elif callbacks.on_succeeded is not None:
            _dispatch(callbacks.on_succeeded, payload)
        if callbacks.on_finished is not None and handle is not None:
            self._call_finished(callbacks.on_finished, handle)

    def _call_finished(self, callback: Callable[..., Any], handle: TaskHandle) -> None:
        """无参回调保持原样；声明了位置参数时把句柄交出去。"""

        if _positional_capacity(callback) >= 1:
            _dispatch(callback, handle)
        else:
            _dispatch(callback)

    def _release(self, job_id: str, handle: TaskHandle | None) -> None:
        with self._lock:
            self._jobs.pop(job_id, None)
            self._callbacks.pop(job_id, None)
            if handle is not None and handle.exclusive:
                current = self._slots.get(handle.exclusive)
                if current is handle:
                    self._slots.pop(handle.exclusive, None)
