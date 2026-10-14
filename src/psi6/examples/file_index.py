"""可运行参考：表单、表格、日志、进度和后台任务放在同一个窗口里。

不是要复制的行业模板。调度只走 ``App.runner``。
空结果用表格自带空态，运行中用 ``set_busy``。关窗口、取消和退出仍是三件事。
"""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from psi6 import App, DesktopWindow, JobOutcome, TaskHandle
from psi6.jobs.file_index import FILE_INDEX_COLUMNS, FileIndexParams, run_file_index
from psi6.ui.buttons import ghost_button, primary_button
from psi6.ui.data_table import DataTable
from psi6.ui.form import FormError, pydantic_form
from psi6.ui.log_panel import LogPanel
from psi6.ui.status_progress import StatusProgress


def build(app: App) -> DesktopWindow:
    """系统标题栏。进度在状态栏右侧，取消按钮单独放在表单下方。"""

    window = DesktopWindow(title="文件索引")
    window.resize(880, 640)
    form = pydantic_form(app.load_config(FileIndexParams))
    start = primary_button("开始")
    cancel = ghost_button("取消")
    cancel.setEnabled(False)
    table = DataTable(FILE_INDEX_COLUMNS)
    log = LogPanel()
    progress = StatusProgress(window.statusBar())
    current: list[TaskHandle] = []

    def set_idle(message: str) -> None:
        table.set_busy(False)
        progress.finish(message)
        start.setEnabled(True)
        cancel.setEnabled(False)

    def start_job() -> None:
        try:
            params = form.get_model()
        except FormError as exc:
            app.notifier.error(str(exc))
            return
        app.save_config(params)
        start.setEnabled(False)
        cancel.setEnabled(True)
        table.set_busy(True, "正在索引")

        def ok(outcome: JobOutcome) -> None:
            table.set_rows(outcome.rows)
            set_idle(outcome.message)

        def bad(message: str) -> None:
            app.notifier.error(message)
            set_idle(message)

        current[:] = [
            app.runner.submit(
                run_file_index,
                params,
                on_progress=progress.set_progress,
                on_log=log.append,
                on_succeeded=ok,
                on_failed=bad,
                on_cancelled=lambda: set_idle("已取消"),
                exclusive="index",
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
    column.addWidget(form)
    column.addWidget(actions)
    column.addWidget(table, stretch=1)
    column.addWidget(log, stretch=1)
    window.set_body(body)
    window.statusBar().showMessage("就绪")
    return window


def main() -> None:
    """启动文件索引窗口。"""

    app = App("psi6-file-index")
    raise SystemExit(app.run(build(app), tray=True, single_instance=True, restore_geometry=True))
