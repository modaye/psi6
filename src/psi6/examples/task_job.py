"""后台任务：进度在状态栏，取消是单独的按钮。

``python -m psi6.examples.task_job --check`` 跑通成功路径后退出。
取消只是请求。工作函数返回或抛出 ``InterruptedError`` 后，状态才结束。
应用退出时 ``App`` 会 ``runner.shutdown()``，不会杀掉线程。
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QHBoxLayout, QWidget

from psi6 import App, DesktopWindow, TaskHandle
from psi6.ui.buttons import ghost_button, primary_button
from psi6.ui.status_progress import StatusProgress


def succeed(*, on_progress, is_cancelled) -> str:
    """报告一步进度。已请求取消时用 ``InterruptedError`` 结束。"""

    on_progress(1, 1, "完成")
    if is_cancelled():
        raise InterruptedError
    return "ok"


def fail_read() -> None:
    """失败信息回到 ``on_failed`` 和 ``TaskHandle.error_message``。"""

    raise RuntimeError("读失败")


def build(app: App) -> DesktopWindow:
    """开始和取消放在页面上。进度条只出现在状态栏右侧。"""

    window = DesktopWindow(title="后台任务")
    progress = StatusProgress(window.statusBar())
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
        current[:] = [
            app.runner.submit(
                succeed,
                on_progress=progress.set_progress,
                on_succeeded=lambda value: set_idle(str(value)),
                on_failed=set_idle,
                on_cancelled=lambda: set_idle("已取消"),
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
    return window


def main(argv: list[str] | None = None) -> int:
    """``--check`` 提交成功任务，回调里退出。"""

    args = sys.argv[1:] if argv is None else argv
    app = App("psi6-task")
    window = build(app)
    if "--check" in args:
        progress = StatusProgress(window.statusBar())
        app.runner.submit(
            succeed,
            on_progress=progress.set_progress,
            on_succeeded=lambda _value: app.qt_app.quit(),
            on_failed=lambda _message: app.qt_app.quit(),
        )
    return app.run(window)


if __name__ == "__main__":
    raise SystemExit(main())
