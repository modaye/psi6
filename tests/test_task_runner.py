"""TaskRunner 在线程池中执行，回调回到主线程。"""

from __future__ import annotations

import time

from psi6.runtime.logs import LogLevel, LogRecord
from psi6.runtime.tasks import TaskRunner, TaskStatus


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
