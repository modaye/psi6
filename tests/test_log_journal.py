"""操作日志落盘：写入在后台线程，任务提交时可以带上 journal。"""

from __future__ import annotations

import json
from pathlib import Path

from psi6.runtime.logs import LogJournal, LogLevel, LogRecord
from psi6.runtime.tasks import TaskRunner, TaskStatus


def test_journal_appends_json_lines(tmp_path: Path) -> None:
    path = tmp_path / "run.jsonl"
    journal = LogJournal(path)
    journal.write(LogRecord(LogLevel.INFO, "开始", detail="第一行"))
    journal.write(LogRecord(LogLevel.ERROR, "失败", extra={"path": "a.txt"}))
    journal.close()
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert rows[0]["message"] == "开始"
    assert rows[0]["detail"] == "第一行"
    assert rows[1]["level"] == "error"
    assert rows[1]["extra"] == {"path": "a.txt"}
    journal.write(LogRecord(LogLevel.INFO, "关闭后"))
    assert len(path.read_text(encoding="utf-8").splitlines()) == 2


def test_submit_writes_the_journal_from_the_worker(qtbot, tmp_path: Path) -> None:
    path = tmp_path / "task.jsonl"
    journal = LogJournal(path)
    runner = TaskRunner()

    def job(on_log=None) -> None:
        on_log(LogRecord(LogLevel.INFO, "扫描完成"))

    handle = runner.submit(job, journal=journal)
    qtbot.waitUntil(lambda: handle.status is TaskStatus.SUCCEEDED, timeout=3000)
    journal.close()
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert rows == [
        {"level": "info", "message": "扫描完成", "detail": "", "extra": {}},
    ]
