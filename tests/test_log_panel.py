"""LogPanel 追加、过滤与导出。"""

from __future__ import annotations

import threading
from pathlib import Path

from pytestqt.qtbot import QtBot

from psi6.runtime.logs import LogLevel, LogRecord
from psi6.ui.log_panel import LogPanel


def test_log_panel_drops_oldest_entries(qtbot: QtBot) -> None:
    panel = LogPanel(max_entries=2)
    qtbot.addWidget(panel)
    panel.append(LogRecord(LogLevel.INFO, "一"))
    panel.append(LogRecord(LogLevel.INFO, "二"))
    panel.append(LogRecord(LogLevel.INFO, "三"))
    assert [entry.message for entry in panel._entries] == ["二", "三"]
    assert panel._table.rowCount() == 2


def test_log_panel_counts_and_export(qtbot: QtBot, tmp_path: Path) -> None:
    panel = LogPanel()
    qtbot.addWidget(panel)
    panel.append(LogRecord(LogLevel.SUCCESS, "ok", extra={"id": "1"}))
    panel.append(LogRecord(LogLevel.ERROR, "bad", detail="x"))
    counts = panel.count_by_level()
    assert counts[LogLevel.SUCCESS] == 1
    assert counts[LogLevel.ERROR] == 1
    target = tmp_path / "log.csv"
    panel.export_csv(target)
    text = target.read_text(encoding="utf-8-sig")
    assert "ok" in text
    assert "bad" in text


def test_worker_thread_append_is_queued(qtbot: QtBot) -> None:
    panel = LogPanel()
    qtbot.addWidget(panel)
    thread = threading.Thread(
        target=lambda: panel.append(LogRecord(LogLevel.INFO, "后台一行")),
        daemon=True,
    )
    thread.start()
    qtbot.waitUntil(lambda: panel._table.rowCount() == 1, timeout=3000)
    assert panel._table.item(0, 2).text() == "后台一行"
