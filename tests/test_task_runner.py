"""TaskRunner 在线程池中执行，回调回到主线程。"""

from __future__ import annotations

import contextvars
import threading
import time

import pytest

from psi6.runtime.logs import LogLevel, LogRecord, capture_task_context
from psi6.runtime.tasks import TaskRunner, TaskStatus


def test_submit_copies_the_caller_context(qtbot) -> None:
    probe: contextvars.ContextVar[int] = contextvars.ContextVar("psi6_probe", default=0)
    probe.set(7)
    runner = TaskRunner()
    seen: dict[str, int] = {}
    nested: dict[str, int] = {}

    def job() -> None:
        seen["value"] = probe.get()
        box: dict[str, int] = {}

        bare = threading.Thread(target=lambda: box.__setitem__("bare", probe.get()))
        bare.start()
        bare.join(timeout=2)
        nested["bare"] = box["bare"]
        carried = capture_task_context()
        wrapped = threading.Thread(
            target=lambda: carried.run(lambda: box.__setitem__("carried", probe.get()))
        )
        wrapped.start()
        wrapped.join(timeout=2)
        nested["carried"] = box["carried"]

    handle = runner.submit(job)
    qtbot.waitUntil(lambda: handle.status is TaskStatus.SUCCEEDED, timeout=3000)
    assert seen["value"] == 7
    assert nested["bare"] == 0
    assert nested["carried"] == 7


def test_submit_success(qtbot) -> None:
    runner = TaskRunner()
    box: dict[str, int] = {}

    def job() -> int:
        return 7

    handle = runner.submit(job, on_succeeded=lambda value: box.__setitem__("value", value))
    qtbot.waitUntil(lambda: handle.status is TaskStatus.SUCCEEDED, timeout=3000)
    assert box["value"] == 7


def test_injects_progress_and_log(qtbot) -> None:
    runner = TaskRunner()
    progress: list[tuple[int, int, str]] = []
    logs: list[str] = []

    def job(on_progress=None, on_log=None, is_cancelled=None) -> str:
        assert is_cancelled is not None
        on_progress(1, 2, "half")
        on_log(LogRecord(LogLevel.INFO, "hello"))
        return "ok"

    handle = runner.submit(
        job,
        on_progress=lambda c, t, m: progress.append((c, t, m)),
        on_log=lambda record: logs.append(record.message),
    )
    qtbot.waitUntil(lambda: handle.status is TaskStatus.SUCCEEDED, timeout=3000)
    assert progress == [(1, 2, "half")]
    assert logs == ["hello"]


def test_cancel_is_cooperative(qtbot) -> None:
    runner = TaskRunner()

    def job(is_cancelled=None) -> None:
        for _ in range(80):
            if is_cancelled():
                raise InterruptedError
            time.sleep(0.02)

    handle = runner.submit(job)
    qtbot.waitUntil(lambda: handle.status is TaskStatus.RUNNING, timeout=3000)
    handle.cancel()
    qtbot.waitUntil(lambda: handle.status is TaskStatus.CANCELLED, timeout=3000)


def test_failure_is_user_facing(qtbot) -> None:
    runner = TaskRunner()
    errors: list[str] = []

    def job() -> None:
        raise RuntimeError("boom")

    handle = runner.submit(job, on_failed=errors.append)
    qtbot.waitUntil(lambda: handle.status is TaskStatus.FAILED, timeout=3000)
    assert errors[0] == "boom"
    assert handle.error_message == "boom"
    assert handle.error_traceback is not None
    assert "RuntimeError" in handle.error_traceback


def test_on_failed_can_receive_the_exception(qtbot) -> None:
    """声明第二个参数的 ``on_failed`` 收到原异常对象，界面不必从字符串里拆结构。"""

    runner = TaskRunner()
    seen: list[tuple[str, BaseException]] = []

    class DataError(Exception):
        def __init__(self, code: str) -> None:
            super().__init__("数据有问题")
            self.code = code

    def job() -> None:
        raise DataError("E_READ")

    handle = runner.submit(job, on_failed=lambda message, exc: seen.append((message, exc)))
    qtbot.waitUntil(lambda: handle.status is TaskStatus.FAILED, timeout=3000)
    message, exc = seen[0]
    assert message == "数据有问题"
    assert isinstance(exc, DataError)
    assert exc.code == "E_READ"
    assert "DataError" in (handle.error_traceback or "")


def test_on_failed_can_receive_detail_text(qtbot) -> None:
    """第三个位置参数拿到堆栈文本，窗口可直接交给 ``fail(..., detail=...)``。"""

    runner = TaskRunner()
    seen: list[tuple[str, BaseException, str]] = []

    def job() -> None:
        raise ValueError("月份解析失败")

    handle = runner.submit(
        job,
        on_failed=lambda message, exc, detail: seen.append((message, exc, detail)),
    )
    qtbot.waitUntil(lambda: handle.status is TaskStatus.FAILED, timeout=3000)
    message, exc, detail = seen[0]
    assert message == "月份解析失败"
    assert isinstance(exc, ValueError)
    assert "ValueError" in detail


def test_on_finished_runs_for_every_terminal_state(qtbot) -> None:
    """成功、失败、取消都会触发一次 ``on_finished``，界面用它恢复按钮。"""

    runner = TaskRunner()
    finished: list[str] = []

    runner.submit(lambda: 1, on_finished=lambda: finished.append("ok"))
    runner.submit(
        _raise,
        on_failed=lambda message: None,
        on_finished=lambda: finished.append("bad"),
    )
    slow = runner.submit(_slow, on_finished=lambda: finished.append("cancelled"))
    qtbot.waitUntil(lambda: slow.status is TaskStatus.RUNNING, timeout=3000)
    slow.cancel()
    qtbot.waitUntil(lambda: len(finished) == 3, timeout=3000)
    assert sorted(finished) == ["bad", "cancelled", "ok"]


def test_on_finished_error_still_releases_the_slot(qtbot) -> None:
    """收尾回调自己抛错时，任务登记和互斥槽仍然清掉。"""

    runner = TaskRunner()

    def broken() -> None:
        raise RuntimeError("收尾出错")

    handle = runner.submit(lambda: 1, exclusive="batch", on_finished=broken)
    qtbot.waitUntil(lambda: handle.status is TaskStatus.SUCCEEDED, timeout=3000)
    assert runner.active_handles() == []
    assert runner.is_busy("batch") is False


def test_log_callback_error_does_not_stick_the_job(qtbot) -> None:
    runner = TaskRunner()

    def job(on_log=None) -> int:
        on_log(LogRecord(LogLevel.INFO, "一行"))
        return 1

    def broken(_record: object) -> None:
        raise RuntimeError("日志控件已失效")

    handle = runner.submit(job, on_log=broken)
    qtbot.waitUntil(lambda: handle.status is TaskStatus.SUCCEEDED, timeout=3000)
    assert runner.is_busy() is False


def test_callbacks_after_widget_deleted_do_not_stick_the_job(qtbot) -> None:
    """页面先销毁，进度、日志和完成回调再碰到失效控件，任务仍要收尾。"""

    from PySide6.QtWidgets import QLabel

    from psi6.runtime.qt_alive import qt_alive

    label = QLabel("alive")
    label.deleteLater()
    qtbot.waitUntil(lambda: not qt_alive(label), timeout=3000)
    runner = TaskRunner()

    def job(on_progress=None, on_log=None) -> int:
        on_progress(1, 1, "完成")
        on_log(LogRecord(LogLevel.INFO, "一行"))
        return 1

    def touch(*_args: object) -> None:
        label.setText("still-there")

    handle = runner.submit(job, on_progress=touch, on_log=touch, on_finished=touch)
    qtbot.waitUntil(lambda: handle.status is TaskStatus.SUCCEEDED, timeout=3000)
    assert runner.active_handles() == []


def test_progress_callback_error_does_not_stick_the_job(qtbot) -> None:
    runner = TaskRunner()

    def job(on_progress=None) -> int:
        on_progress(1, 1, "完成")
        return 1

    def broken(*_args: object) -> None:
        raise RuntimeError("进度控件已失效")

    handle = runner.submit(job, on_progress=broken)
    qtbot.waitUntil(lambda: handle.status is TaskStatus.SUCCEEDED, timeout=3000)
    assert runner.is_busy() is False


def test_cancel_while_queued_finishes_without_running(qtbot) -> None:
    runner = TaskRunner(max_threads=1)
    started = threading.Event()
    release = threading.Event()
    ran: list[str] = []

    def blocker(is_cancelled=None) -> None:
        del is_cancelled
        started.set()
        release.wait(2)

    def later() -> None:
        ran.append("later")

    first = runner.submit(blocker)
    qtbot.waitUntil(started.is_set, timeout=3000)
    second = runner.submit(later)
    assert second.status is TaskStatus.QUEUED
    second.cancel()
    release.set()
    qtbot.waitUntil(lambda: second.status is TaskStatus.CANCELLED, timeout=3000)
    qtbot.waitUntil(lambda: first.status is TaskStatus.SUCCEEDED, timeout=3000)
    assert ran == []


def test_on_finished_runs_even_when_a_callback_raises(qtbot) -> None:
    """成功回调自己抛错时，``on_finished`` 仍执行，按钮不会一直灰着。"""

    runner = TaskRunner()
    finished: list[bool] = []

    def broken_callback(value: object) -> None:
        raise RuntimeError("界面代码出错")

    handle = runner.submit(
        lambda: 1,
        on_succeeded=broken_callback,
        on_finished=lambda: finished.append(True),
    )
    qtbot.waitUntil(lambda: handle.status is TaskStatus.SUCCEEDED, timeout=3000)
    qtbot.waitUntil(lambda: finished == [True], timeout=3000)


def test_logs_from_worker_threads_are_all_kept(qtbot) -> None:
    """joblib 风格的并发写日志：缓冲有锁，一条不丢。"""

    runner = TaskRunner()
    logs: list[str] = []

    def job(on_log=None) -> str:
        def write(name: str) -> None:
            for index in range(50):
                on_log(LogRecord(LogLevel.INFO, f"{name}-{index}"))

        threads = [threading.Thread(target=write, args=(f"t{n}",)) for n in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        return "ok"

    handle = runner.submit(
        job,
        on_log=lambda record: logs.append(record.message),
        log_interval_ms=0,
    )
    qtbot.waitUntil(lambda: handle.status is TaskStatus.SUCCEEDED, timeout=3000)
    qtbot.waitUntil(lambda: len(logs) == 200, timeout=3000)


def _raise() -> None:
    raise RuntimeError("boom")


def _slow(is_cancelled=None) -> None:
    for _ in range(80):
        if is_cancelled():
            raise InterruptedError
        time.sleep(0.02)


def test_task_log_reaches_on_log_from_nested_calls(qtbot) -> None:
    """深层函数用 ``task_log`` 写日志，不必把 ``on_log`` 逐层传下去。"""

    from psi6.runtime.logs import task_log

    runner = TaskRunner()
    logs: list[tuple[LogLevel, str]] = []

    def read_rows() -> int:
        task_log("正在读取 loans.csv，120 行")
        return 120

    def job() -> str:
        rows = read_rows()
        task_log(f"共 {rows} 行", level=LogLevel.SUCCESS)
        return "ok"

    handle = runner.submit(job, on_log=lambda record: logs.append((record.level, record.message)))
    qtbot.waitUntil(lambda: handle.status is TaskStatus.SUCCEEDED, timeout=3000)
    assert (LogLevel.INFO, "正在读取 loans.csv，120 行") in logs
    assert (LogLevel.SUCCESS, "共 120 行") in logs


def test_task_log_outside_a_task_falls_back_to_logging() -> None:
    from psi6.runtime.logs import task_log

    task_log("没有任务上下文")  # 回退到标准库 logging，不抛错


def test_loguru_sink_bridges_records_without_loguru() -> None:
    """loguru 桥只做结构转换；psi6 自身不依赖 loguru。"""

    from collections import namedtuple

    from psi6.runtime.logs import loguru_sink

    received: list[LogRecord] = []
    sink = loguru_sink(received.append)
    level = namedtuple("Level", "name")(name="WARNING")
    message = namedtuple("Message", "record")(record={"level": level, "message": "汇率缺失"})
    sink(message)
    sink("plain")
    assert received[0].level is LogLevel.WARNING
    assert received[0].message == "汇率缺失"
    assert received[1].level is LogLevel.INFO
    assert received[1].message == "plain"


def test_on_busy_fires_when_slot_is_occupied(qtbot) -> None:
    """同槽任务还在跑时再次提交：返回原句柄并触发一次 ``on_busy``。"""

    runner = TaskRunner()
    started = threading.Event()
    busy_calls: list[str] = []

    def job(is_cancelled=None) -> str:
        started.set()
        for _ in range(80):
            if is_cancelled():
                raise InterruptedError
            time.sleep(0.02)
        return "done"

    first = runner.submit(job, exclusive="loan")
    qtbot.waitUntil(started.is_set, timeout=3000)
    second = runner.submit(job, exclusive="loan", on_busy=lambda: busy_calls.append("busy"))
    assert second is first
    assert busy_calls == ["busy"]
    silent = runner.submit(job, exclusive="loan")
    assert silent is first
    assert busy_calls == ["busy"]
    first.cancel()
    qtbot.waitUntil(lambda: first.status is TaskStatus.CANCELLED, timeout=3000)


def test_cancel_all_and_shutdown(qtbot) -> None:
    runner = TaskRunner()

    def job(is_cancelled=None) -> None:
        for _ in range(80):
            if is_cancelled():
                raise InterruptedError
            time.sleep(0.02)

    handle = runner.submit(job)
    qtbot.waitUntil(lambda: handle.status is TaskStatus.RUNNING, timeout=3000)
    assert runner.active_handles()
    runner.cancel_all()
    qtbot.waitUntil(lambda: handle.status is TaskStatus.CANCELLED, timeout=3000)
    assert runner.shutdown(timeout_ms=2000) is True


def test_shutdown_timeout_does_not_kill_the_thread(qtbot) -> None:
    runner = TaskRunner()
    started = threading.Event()
    release = threading.Event()

    def job(is_cancelled=None) -> str:
        del is_cancelled
        started.set()
        release.wait(2)
        return "done"

    handle = runner.submit(job)
    qtbot.waitUntil(started.is_set, timeout=3000)
    assert runner.shutdown(timeout_ms=30) is False
    assert handle.cancel_requested is True
    assert handle.status is TaskStatus.RUNNING
    release.set()
    qtbot.waitUntil(lambda: handle.status is TaskStatus.CANCELLED, timeout=3000)


def test_exclusive_slot_rejects_second_job(qtbot) -> None:
    runner = TaskRunner()
    started = 0

    def job(is_cancelled=None) -> str:
        nonlocal started
        started += 1
        for _ in range(80):
            if is_cancelled():
                raise InterruptedError
            time.sleep(0.02)
        return "done"

    first = runner.submit(job, exclusive="batch")
    qtbot.waitUntil(lambda: started >= 1, timeout=3000)
    second = runner.submit(job, exclusive="batch")
    assert second is first
    first.cancel()
    qtbot.waitUntil(lambda: first.status is TaskStatus.CANCELLED, timeout=3000)
    assert started == 1


def test_is_busy_tracks_exclusive_slot(qtbot) -> None:
    runner = TaskRunner()

    def job(is_cancelled=None) -> str:
        for _ in range(80):
            if is_cancelled():
                raise InterruptedError
            time.sleep(0.02)
        return "done"

    assert runner.is_busy() is False
    handle = runner.submit(job, exclusive="scan")
    qtbot.waitUntil(lambda: handle.status is TaskStatus.RUNNING, timeout=3000)
    assert runner.is_busy() is True
    assert runner.is_busy("scan") is True
    assert runner.is_busy("other") is False
    handle.cancel()
    qtbot.waitUntil(lambda: handle.status is TaskStatus.CANCELLED, timeout=3000)
    assert runner.is_busy("scan") is False


def test_progress_coalesces_intermediate_updates(qtbot) -> None:
    runner = TaskRunner()
    progress: list[tuple[int, int, str]] = []

    def job(on_progress=None) -> str:
        on_progress(1, 4, "a")
        on_progress(2, 4, "b")
        on_progress(3, 4, "c")
        on_progress(4, 4, "d")
        return "ok"

    handle = runner.submit(
        job,
        on_progress=lambda current, total, message: progress.append((current, total, message)),
        progress_interval_ms=10_000,
    )
    qtbot.waitUntil(lambda: handle.status is TaskStatus.SUCCEEDED, timeout=3000)
    assert progress[0] == (1, 4, "a")
    assert progress[-1] == (4, 4, "d")
    assert (2, 4, "b") not in progress
    assert (3, 4, "c") not in progress


def test_on_finished_can_restart_the_same_slot(qtbot) -> None:
    """收尾回调里重新提交同一 ``exclusive`` 槽时，旧槽已经释放。"""

    runner = TaskRunner()
    restarted: list = []

    def start_again() -> None:
        restarted.append(runner.submit(lambda: 2, exclusive="batch"))

    first = runner.submit(lambda: 1, exclusive="batch", on_finished=start_again)
    qtbot.waitUntil(lambda: len(restarted) == 1, timeout=3000)
    assert restarted[0] is not first
    qtbot.waitUntil(lambda: restarted[0].status is TaskStatus.SUCCEEDED, timeout=3000)
    assert runner.is_busy("batch") is False


def test_logs_written_after_cancel_are_delivered(qtbot) -> None:
    """取消请求不会吞掉收尾日志；工作函数退出前的记录仍要送到界面。"""

    runner = TaskRunner()
    logs: list[str] = []

    def job(on_log=None, is_cancelled=None) -> str:
        on_log(LogRecord(LogLevel.INFO, "before"))
        while not is_cancelled():
            time.sleep(0.01)
        on_log(LogRecord(LogLevel.INFO, "tail after cancel"))
        return "done"

    handle = runner.submit(
        job,
        on_log=lambda record: logs.append(record.message),
        log_interval_ms=0,
    )
    qtbot.waitUntil(lambda: handle.status is TaskStatus.RUNNING, timeout=3000)
    handle.cancel()
    qtbot.waitUntil(lambda: handle.status is TaskStatus.CANCELLED, timeout=3000)
    qtbot.waitUntil(lambda: "tail after cancel" in logs, timeout=3000)
    assert logs[0] == "before"


def test_base_exception_still_finishes_the_job(qtbot) -> None:
    runner = TaskRunner()
    errors: list[str] = []
    finished: list[bool] = []

    def job() -> None:
        raise SystemExit("退出码 2")

    handle = runner.submit(
        job,
        on_failed=errors.append,
        on_finished=lambda: finished.append(True),
    )
    qtbot.waitUntil(lambda: handle.status is TaskStatus.FAILED, timeout=3000)
    assert errors == ["退出码 2"]
    assert finished == [True]


def test_completed_jobs_do_not_accumulate_signal_objects(qtbot) -> None:
    from psi6.runtime.tasks import _JobSignals

    runner = TaskRunner()
    before = len(runner.findChildren(_JobSignals))
    handles = [runner.submit(lambda: 1) for _ in range(5)]
    for handle in handles:
        qtbot.waitUntil(lambda handle=handle: handle.status is TaskStatus.SUCCEEDED, timeout=3000)
    assert len(runner.findChildren(_JobSignals)) == before
    assert before == 1


def test_progress_snapshot_keeps_the_latest_value(qtbot) -> None:
    runner = TaskRunner()
    reached = threading.Event()
    release = threading.Event()

    def job(on_progress=None) -> str:
        on_progress(1, 4, "a")
        on_progress(2, 4, "b")
        reached.set()
        release.wait(2)
        on_progress(4, 4, "d")
        return "ok"

    handle = runner.submit(job, progress_interval_ms=10_000)
    qtbot.waitUntil(reached.is_set, timeout=3000)
    assert handle.progress == (2, 4, "b")
    release.set()
    qtbot.waitUntil(lambda: handle.status is TaskStatus.SUCCEEDED, timeout=3000)
    assert handle.progress == (4, 4, "d")


def test_started_and_finished_report_the_same_handle(qtbot) -> None:
    runner = TaskRunner()
    started: list = []
    finished: list = []
    runner.started.connect(started.append)
    runner.finished.connect(finished.append)
    handle = runner.submit(lambda: 5)
    qtbot.waitUntil(lambda: len(finished) == 1, timeout=3000)
    assert started == [handle]
    assert finished == [handle]
    assert handle.result == 5
    assert handle.status is TaskStatus.SUCCEEDED


def test_on_finished_can_receive_the_handle(qtbot) -> None:
    runner = TaskRunner()
    seen: list = []
    handle = runner.submit(lambda: 3, on_finished=lambda finished: seen.append(finished))
    qtbot.waitUntil(lambda: len(seen) == 1, timeout=3000)
    assert seen == [handle]
    assert handle.result == 3


def test_submit_after_shutdown_is_rejected(qtbot) -> None:
    runner = TaskRunner()
    handle = runner.submit(lambda: 1)
    qtbot.waitUntil(lambda: handle.status is TaskStatus.SUCCEEDED, timeout=3000)
    assert runner.shutdown(timeout_ms=1000) is True
    with pytest.raises(RuntimeError, match="已关闭"):
        runner.submit(lambda: 2)


def test_exclusive_slot_is_taken_once_across_threads(qtbot) -> None:
    runner = TaskRunner()
    hold = threading.Event()
    barrier = threading.Barrier(2)
    handles: list = []

    def job() -> None:
        hold.wait(2)

    def submit() -> None:
        barrier.wait(2)
        handles.append(runner.submit(job, exclusive="batch"))

    threads = [threading.Thread(target=submit) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(2)
    assert len(handles) == 2
    assert handles[0] is handles[1]
    hold.set()
    qtbot.waitUntil(lambda: handles[0].status is TaskStatus.SUCCEEDED, timeout=3000)
    assert runner.is_busy("batch") is False


def test_shutdown_drains_queued_finish_callbacks(qtbot) -> None:
    runner = TaskRunner()
    finished: list[bool] = []
    handle = runner.submit(lambda: 1, on_finished=lambda: finished.append(True))
    assert runner._pool.waitForDone(3000) is True
    assert runner.active_handles()
    assert runner.shutdown(timeout_ms=1000) is True
    assert handle.status is TaskStatus.SUCCEEDED
    assert finished == [True]
