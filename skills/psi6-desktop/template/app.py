"""应用入口。复制本目录后，在此目录执行 ``python app.py --check``。"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QPushButton

from psi6 import App, TaskStatus

from job import run_job
from theme import Desk
from window import build


def main(argv: list[str] | None = None) -> int:
    """显示主窗口。``--check`` 核对主题和任务页后，跑通一次任务再退出。

    退出码 0 表示主题已加载、页面上有开始和取消、任务以 ``succeeded`` 结束。
    主题字段写错会在创建 ``App`` 时抛错。任务失败或被取消时返回 2。
    """

    args = sys.argv[1:] if argv is None else argv
    app = App("desk", theme=Desk)
    window = build(app)
    if "--check" not in args:
        return app.run(window)
    if app.tokens.color_primary != "#4d7c5a":
        return 2
    labels = {button.text() for button in window.findChildren(QPushButton)}
    if not {"开始", "取消"} <= labels:
        return 2

    def finished(_value: object) -> None:
        if handle.status is not TaskStatus.SUCCEEDED:
            app.qt_app.exit(2)
            return
        app.qt_app.quit()

    handle = app.runner.submit(
        run_job,
        on_succeeded=finished,
        on_failed=lambda _message: app.qt_app.exit(2),
        on_cancelled=lambda: app.qt_app.exit(2),
    )
    return app.run(window)


if __name__ == "__main__":
    raise SystemExit(main())
