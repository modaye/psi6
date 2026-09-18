"""开始 / 取消 / 进度 / 状态，避免每个主窗自己管按钮启用态。"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget

from psi6.ui.buttons import ghost_button, primary_button
from psi6.ui.icon import apply_button_icon


class TaskPanel(QWidget):
    """任务控制条。"""

    start_requested = Signal()
    cancel_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        row = QHBoxLayout()
        self._start = primary_button("开始")
        apply_button_icon(self._start, "play")
        self._start.clicked.connect(self.start_requested.emit)
        self._cancel = ghost_button("取消")
        apply_button_icon(self._cancel, "x")
        self._cancel.setEnabled(False)
        self._cancel.clicked.connect(self.cancel_requested.emit)
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)
        row.addWidget(self._start)
        row.addWidget(self._cancel)
        row.addWidget(self._progress, stretch=1)
        root.addLayout(row)

        self._status = QLabel("就绪")
        self._status.setObjectName("psi6Hint")
        root.addWidget(self._status)

    def set_idle(self, message: str = "就绪") -> None:
        self._start.setEnabled(True)
        self._cancel.setEnabled(False)
        self._progress.setValue(0)
        self._status.setText(message)

    def set_running(self, current: int, total: int, message: str) -> None:
        self._start.setEnabled(False)
        self._cancel.setEnabled(True)
        percent = int(current / total * 100) if total else 0
        self._progress.setValue(percent)
        self._status.setText(message)

    def set_finished(self, message: str) -> None:
        self._start.setEnabled(True)
        self._cancel.setEnabled(False)
        self._progress.setValue(100)
        self._status.setText(message)

    def set_failed(self, message: str) -> None:
        self._start.setEnabled(True)
        self._cancel.setEnabled(False)
        self._status.setText(message)
