"""把任务状态画在界面上。``python -m psi6.examples.task_status --check``。"""

from __future__ import annotations

import sys

from psi6 import App, DesktopWindow, TaskHandle, TaskStatus
from psi6.ui.task_panel import TaskPanel


def work(*, on_progress, is_cancelled) -> str:
    """两步进度。界面只在回调里读 ``TaskHandle.status``。"""

    on_progress(1, 2, "读取")
    if is_cancelled():
        raise InterruptedError
    on_progress(2, 2, "写完")
    return "完成"


def build(app: App) -> tuple[DesktopWindow, TaskPanel]:
    """任务条展示运行、成功和失败。调度仍是 ``app.runner``。"""

    window = DesktopWindow(title="任务状态")
    panel = TaskPanel()
    current: list[TaskHandle] = []

    def show(message: str) -> None:
        handle = current[-1]
        if handle.status is TaskStatus.FAILED:
            panel.set_failed(message)
            return
        panel.set_finished(f"{handle.status} {message}")

    def start() -> None:
        panel.set_running(0, 2, "排队")
        current[:] = [
            app.runner.submit(
                work,
                on_progress=panel.set_running,
                on_succeeded=lambda value: show(str(value)),
                on_failed=lambda message: show(message),
            )
        ]

    def request_cancel() -> None:
        if current:
            current[-1].cancel()

    panel.start_requested.connect(start)
    panel.cancel_requested.connect(request_cancel)
    window.set_body(panel)
    return window, panel


def main(argv: list[str] | None = None) -> int:
    """``--check`` 跑完任务并退出。成功时状态必须是 ``succeeded``。"""

    args = sys.argv[1:] if argv is None else argv
    app = App("psi6-status")
    window, panel = build(app)
    if "--check" in args:
        def finished(value: object) -> None:
            panel.set_finished(str(value))
            if handle.status is not TaskStatus.SUCCEEDED:
                app.qt_app.exit(2)
                return
            app.qt_app.quit()

        handle = app.runner.submit(work, on_progress=panel.set_running, on_succeeded=finished)
    return app.run(window)


if __name__ == "__main__":
    raise SystemExit(main())
