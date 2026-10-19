"""TaskRunner 在线程池中执行，回调回到主线程。"""

from __future__ import annotations

import contextvars
import threading
import time

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
