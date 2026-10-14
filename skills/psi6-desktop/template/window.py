"""任务页。开始和取消是分开的按钮，进度在状态栏。"""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from psi6 import App, DesktopWindow, TaskHandle
from psi6.ui.buttons import ghost_button, primary_button
from psi6.ui.log_panel import LogPanel
from psi6.ui.status_progress import StatusProgress

from job import run_job


def build(app: App) -> DesktopWindow:
    """系统标题栏。取消只作用于当前任务，不关闭窗口。"""

    window = DesktopWindow(title="Desk")
    window.resize(720, 480)
    progress = StatusProgress(window.statusBar())
    log = LogPanel()
    start = primary_button("开始")
    cancel = ghost_button("取消")
    cancel.setEnabled(False)
    current: list[TaskHandle] = []

    def set_idle(message: str) -> None:
        progress.finish(message)
        start.setEnabled(True)
        cancel.setEnabled(False)

    def start_job() -> None:
        start.setEnabled(False)
        cancel.setEnabled(True)

        def failed(message: str) -> None:
            app.notifier.error(message)
            set_idle(message)

        current[:] = [
            app.runner.submit(
                run_job,
                on_progress=progress.set_progress,
                on_log=log.append,
                on_succeeded=lambda value: set_idle(str(value)),
                on_failed=failed,
                on_cancelled=lambda: set_idle("已取消"),
                exclusive="desk",
            )
        ]

    def request_cancel() -> None:
        if current:
            current[-1].cancel()

    start.clicked.connect(start_job)
    cancel.clicked.connect(request_cancel)

    actions = QWidget()
    row = QHBoxLayout(actions)
    row.setContentsMargins(0, 0, 0, 0)
    row.addWidget(start)
    row.addWidget(cancel)
    row.addStretch()

    body = QWidget()
    column = QVBoxLayout(body)
    column.setContentsMargins(16, 16, 16, 8)
    column.setSpacing(10)
    column.addWidget(actions)
    column.addWidget(log, stretch=1)
    window.set_body(body)
    window.statusBar().showMessage("就绪")
    return window
