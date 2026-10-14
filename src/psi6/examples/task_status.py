"""把任务状态留在状态栏。``python -m psi6.examples.task_status --check``。"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QHBoxLayout, QWidget

from psi6 import App, DesktopWindow, TaskHandle, TaskStatus
from psi6.ui.buttons import ghost_button, primary_button
from psi6.ui.status_progress import StatusProgress


def work(*, on_progress, is_cancelled) -> str:
    """两步进度。界面只在回调里读 ``TaskHandle.status``。"""

    on_progress(1, 2, "读取")
    if is_cancelled():
        raise InterruptedError
    on_progress(2, 2, "写完")
    return "完成"


def build(app: App) -> tuple[DesktopWindow, StatusProgress]:
    """进度条在状态栏。开始和取消不与进度条同一行。"""

    window = DesktopWindow(title="任务状态")
    progress = StatusProgress(window.statusBar())
    start = primary_button("开始")
    cancel = ghost_button("取消")
    cancel.setEnabled(False)
    current: list[TaskHandle] = []

    def show(message: str) -> None:
        handle = current[-1]
        progress.finish(f"{handle.status} {message}")
        start.setEnabled(True)
        cancel.setEnabled(False)

    def start_job() -> None:
        start.setEnabled(False)
        cancel.setEnabled(True)
        current[:] = [
            app.runner.submit(
                work,
                on_progress=progress.set_progress,
                on_succeeded=lambda value: show(str(value)),
                on_failed=show,
                on_cancelled=lambda: show("已取消"),
            )
        ]

    def request_cancel() -> None:
        if current:
            current[-1].cancel()

    start.clicked.connect(start_job)
    cancel.clicked.connect(request_cancel)
    body = QWidget()
    row = QHBoxLayout(body)
    row.addWidget(start)
    row.addWidget(cancel)
    row.addStretch()
    window.set_body(body)
    return window, progress


def main(argv: list[str] | None = None) -> int:
    """``--check`` 跑完任务并退出。成功时状态必须是 ``succeeded``。"""

    args = sys.argv[1:] if argv is None else argv
    app = App("psi6-status")
    window, progress = build(app)
    if "--check" in args:

        def finished(value: object) -> None:
            progress.finish(str(value))
            if handle.status is not TaskStatus.SUCCEEDED:
                app.qt_app.exit(2)
                return
            app.qt_app.quit()

        handle = app.runner.submit(work, on_progress=progress.set_progress, on_succeeded=finished)
    return app.run(window)


if __name__ == "__main__":
    raise SystemExit(main())
