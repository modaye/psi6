"""任务过程日志面板：过滤、统计、导出。"""

from __future__ import annotations

import csv
from pathlib import Path

from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from psi6.runtime.logs import LogLevel, LogRecord

_LEVEL_LABELS = {
    "全部": None,
    "成功": LogLevel.SUCCESS,
    "警告": LogLevel.WARNING,
    "错误": LogLevel.ERROR,
    "信息": LogLevel.INFO,
}

_LEVEL_TEXT = {
    LogLevel.SUCCESS: "成功",
    LogLevel.WARNING: "警告",
    LogLevel.ERROR: "错误",
    LogLevel.INFO: "信息",
}


class LogPanel(QWidget):
    """可过滤、可导出的操作日志表。"""

    COLUMNS = ("序号", "级别", "消息", "详情")

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._entries: list[LogRecord] = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        toolbar = QHBoxLayout()
        self._filter = QComboBox()
        self._filter.setAccessibleName("日志级别")
        self._filter.addItems(list(_LEVEL_LABELS))
        self._filter.currentTextChanged.connect(self._rebuild)
        toolbar.addWidget(self._filter)
        toolbar.addStretch()
        export_btn = QPushButton("导出日志…")
        export_btn.setAccessibleName("导出日志")
        export_btn.clicked.connect(self._choose_export)
        clear_btn = QPushButton("清空")
        clear_btn.setAccessibleName("清空日志")
        clear_btn.clicked.connect(self.clear)
        toolbar.addWidget(export_btn)
        toolbar.addWidget(clear_btn)
        layout.addLayout(toolbar)

        self._table = QTableWidget(0, len(self.COLUMNS))
        self._table.setHorizontalHeaderLabels(list(self.COLUMNS))
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().hide()
        layout.addWidget(self._table)

    def append(self, record: LogRecord) -> None:
        self._entries.append(record)
        if self._match(record):
            self._append_row(len(self._entries), record)

    def clear(self) -> None:
        self._entries.clear()
        self._table.setRowCount(0)

    def count_by_level(self) -> dict[LogLevel, int]:
        counts = {level: 0 for level in LogLevel}
        for entry in self._entries:
            counts[entry.level] += 1
        return counts

    def export_csv(self, path: Path) -> None:
        wanted = self._current_filter()
        rows = [e for e in self._entries if wanted is None or e.level == wanted]
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            writer.writerow(["级别", "消息", "详情", "附加"])
            for entry in rows:
                extra = "; ".join(f"{k}={v}" for k, v in entry.extra.items())
                writer.writerow([entry.level.value, entry.message, entry.detail, extra])

    def _current_filter(self) -> LogLevel | None:
        return _LEVEL_LABELS[self._filter.currentText()]

    def _match(self, record: LogRecord) -> bool:
        wanted = self._current_filter()
        return wanted is None or record.level == wanted

    def _rebuild(self, _text: str = "") -> None:
        self._table.setRowCount(0)
        for index, entry in enumerate(self._entries, start=1):
            if self._match(entry):
                self._append_row(index, entry)

    def _append_row(self, seq: int, record: LogRecord) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        extra = "; ".join(f"{k}={v}" for k, v in record.extra.items())
        detail = record.detail or extra
        values = (str(seq), _LEVEL_TEXT[record.level], record.message, detail)
        for column, text in enumerate(values):
            item = QTableWidgetItem(text)
            if extra:
                item.setToolTip(extra)
            self._table.setItem(row, column, item)

    def _choose_export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "导出操作日志",
            "操作日志.csv",
            "CSV (*.csv)",
        )
        if path:
            self.export_csv(Path(path))
