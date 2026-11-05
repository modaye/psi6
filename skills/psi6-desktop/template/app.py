"""应用入口。复制本目录后，在此目录执行 ``python app.py --check``。"""

from __future__ import annotations

import sys
from pathlib import Path

from job import run_job
from PySide6.QtWidgets import QPushButton
from theme import Desk
from window import build

from psi6 import App, TaskStatus
from psi6.spec import check_paths, format_findings


def main(argv: list[str] | None = None) -> int:
    """显示主窗口。``--check`` 先核对规范，再核对主题和任务页。

    退出码 0 表示规范检查通过、主题已加载、页面上有开始和取消、任务以
    ``succeeded`` 结束。主题字段写错会在创建 ``App`` 时抛错。
    规范问题、任务失败或被取消时返回 2。
    """

    args = sys.argv[1:] if argv is None else argv
    if "--check" in args:
        findings = check_paths([Path(__file__).resolve().parent])
        if findings:
            sys.stderr.write(format_findings(findings) + "\n")
            return 2
    # density="auto" 会在窗口变小 / 高 DPI 时自动收紧间距与控件高度；
    # 也可传 "modern" / "compact" 固定，或运行时用 app.set_density_mode(...) 切换。
    # 键盘焦点环默认不画；需要键盘可见性时传 focus_ring=True 或 app.set_focus_ring(True)。
    app = App("desk", theme=Desk, density="auto")
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
