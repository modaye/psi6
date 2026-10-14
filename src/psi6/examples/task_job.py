"""后台任务：进度、失败和退出时的取消请求。

``python -m psi6.examples.task_job --check`` 跑通成功路径后退出。
取消只是请求。工作函数返回或抛出 ``InterruptedError`` 后，状态才结束。
应用退出时 ``App`` 会 ``runner.shutdown()``，不会杀掉线程。
"""

from __future__ import annotations

import sys

from psi6 import App, DesktopWindow, TaskHandle
from psi6.ui.task_panel import TaskPanel


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
    """开始按钮提交 ``succeed``。失败写到任务条，不在界面线程里抛出。"""

    window = DesktopWindow(title="后台任务")
    panel = TaskPanel()
    current: list[TaskHandle] = []

    def start() -> None:
        panel.set_running(0, 1, "运行中")

        def ok(value: object) -> None:
            panel.set_finished(str(value))

        def bad(message: str) -> None:
            panel.set_failed(message)

        current[:] = [app.runner.submit(succeed, on_succeeded=ok, on_failed=bad)]

    def request_cancel() -> None:
        if current:
            current[-1].cancel()

    panel.start_requested.connect(start)
    panel.cancel_requested.connect(request_cancel)
    window.set_body(panel)
    return window


def main(argv: list[str] | None = None) -> int:
    """``--check`` 提交成功任务，回调里退出。"""

    args = sys.argv[1:] if argv is None else argv
    app = App("psi6-task")
    window = build(app)
    if "--check" in args:
        app.runner.submit(
            succeed,
            on_succeeded=lambda _value: app.qt_app.quit(),
            on_failed=lambda _message: app.qt_app.quit(),
        )
    return app.run(window)


if __name__ == "__main__":
    raise SystemExit(main())
