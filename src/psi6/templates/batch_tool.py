"""把表单、后台任务、日志、结果表接到一个窗里。可继承改布局或结果处理，不是行业模板。"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from pydantic import BaseModel
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from psi6.runtime.app import App
from psi6.runtime.job import JobOutcome
from psi6.runtime.logs import LogLevel, LogRecord
from psi6.runtime.tasks import TaskHandle
from psi6.ui.action_bar import ActionBar
from psi6.ui.banner import Banner
from psi6.ui.data_table import DataTable, TableColumn
from psi6.ui.desktop_window import DesktopWindow
from psi6.ui.dialogs import fail, warn
from psi6.ui.form import FormError, FormView, pydantic_form
from psi6.ui.log_panel import LogPanel
from psi6.ui.property_list import PropertyList
from psi6.ui.search_field import SearchField
from psi6.ui.status_badge import StatusBadge
from psi6.ui.tag import TagRow
from psi6.ui.task_panel import TaskPanel

JobFn = Callable[..., Any]


class BatchToolWindow(DesktopWindow):
    """表单 + 任务条 + 结果表 + 日志的组合窗。

    业务传入 ``params`` 与 ``job``。同一槽同时只跑一份（默认 ``exclusive="batch"``）。
    要改结构时子类覆盖钩子或使用公开属性，不要改 ``_`` 私有成员。
    """

    def __init__(
        self,
        *,
        title: str,
        params: type[BaseModel] | BaseModel,
        job: JobFn,
        app: App,
        result_columns: Sequence[TableColumn | str] | None = None,
        persist_config: bool = True,
        icon: str = "folder",
        exclusive: str = "batch",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(title=title, icon=icon, parent=parent)
        self.setMinimumSize(960, 640)
        self._app = app
        self._job = job
        self._persist_config = persist_config
        self._exclusive = exclusive
        self._model_type = type(params) if isinstance(params, BaseModel) else params
        self._handle: TaskHandle | None = None

        central = QWidget()
        self.set_body(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 8)
        root.setSpacing(10)

        self._form = pydantic_form(self._initial_params(params))
        root.addWidget(self._form)

        self._task_panel = TaskPanel()
        self._task_panel.start_requested.connect(self._start)
        self._task_panel.cancel_requested.connect(self._cancel)
        root.addWidget(self._task_panel)

        self._banner = Banner()
        root.addWidget(self._banner)

        bar = ActionBar()
        self._stat_success = StatusBadge("成功 0", tone="success")
        self._stat_warning = StatusBadge("警告 0", tone="warning")
        self._stat_error = StatusBadge("错误 0", tone="error")
        bar.add_left(self._stat_success)
        bar.add_left(self._stat_warning)
        bar.add_left(self._stat_error)
        self._search = SearchField(placeholder="筛选结果…")
        self._search.query_changed.connect(self._on_filter)
        bar.add_right(self._search)
        root.addWidget(bar)

        self._tags = TagRow()
        self._tags.tag_selected.connect(self._on_tag)
        root.addWidget(self._tags)

        self._table = DataTable(result_columns)
        self._table.selection_changed.connect(self._sync_properties)
        self._props = PropertyList()
        results = QSplitter(Qt.Orientation.Horizontal)
        results.addWidget(self._table)
        results.addWidget(self._props)
        results.setStretchFactor(0, 3)
        results.setStretchFactor(1, 2)

        self._log = LogPanel()
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(results)
        splitter.addWidget(self._log)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        root.addWidget(splitter, stretch=1)

        status = self.statusBar()
        self._app.notifier.bind_status_bar(status)
        self._app.notifier.info("就绪")

    @property
    def form(self) -> FormView:
        """参数表单。"""

        return self._form

    @property
    def table(self) -> DataTable:
        """结果表。"""

        return self._table

    @property
    def log(self) -> LogPanel:
        """过程日志。"""

        return self._log

    @property
    def banner(self) -> Banner:
        return self._banner

    @property
    def task_panel(self) -> TaskPanel:
        return self._task_panel

    @property
    def handle(self) -> TaskHandle | None:
        """当前任务句柄。空闲时为 ``None``。"""

        return self._handle

    @property
    def exclusive(self) -> str:
        """``TaskRunner`` 单飞槽名。"""

        return self._exclusive

    def tag_values(self, row: dict[str, Any]) -> list[str]:
        """从一行结果抽出筛选标签。子类可覆盖。"""

        labels: list[str] = []
        for key in ("suffix", "kind", "type"):
            raw = row.get(key)
            if raw:
                labels.append(str(raw))
        return labels

    def present_outcome(self, outcome: JobOutcome) -> None:
        """把成功结果填进表和标签。子类可覆盖。"""

        self._table.set_rows(outcome.rows)
        self._refresh_tags(outcome.rows)

    def _initial_params(self, params: type[BaseModel] | BaseModel) -> BaseModel | type[BaseModel]:
        if not self._persist_config:
            return params
        stored = self._app.store.path_for(self._app.name)
        if stored.is_file():
            return self._app.load_config(self._model_type)
        return params

    def _refresh_stats(self) -> None:
        counts = self._log.count_by_level()
        self._stat_success.set_status(f"成功 {counts[LogLevel.SUCCESS]}", tone="success")
        self._stat_warning.set_status(f"警告 {counts[LogLevel.WARNING]}", tone="warning")
        self._stat_error.set_status(f"错误 {counts[LogLevel.ERROR]}", tone="error")

    def _on_filter(self, query: str) -> None:
        self._table.set_filter(query)
        self._tags.set_checked(query)
        self._sync_properties()

    def _on_tag(self, label: str) -> None:
        self._search.blockSignals(True)
        self._search.setText(label)
        self._search.blockSignals(False)
        self._table.set_filter(label)
        self._sync_properties()

    def _sync_properties(self) -> None:
        rows = self._table.selected_rows()
        self._props.set_values(rows[0] if rows else None)

    def _start(self) -> None:
        if self._app.runner.is_busy(self._exclusive):
            return
        try:
            model = self._form.get_model()
        except FormError as exc:
            warn(self, "参数无效", str(exc))
            self._app.notifier.warning(str(exc))
            self._banner.set_notice(str(exc), tone="warning")
            return

        if self._persist_config:
            self._app.save_config(model)

        self._log.clear()
        self._table.clear()
        self._table.set_busy(True, "正在准备…")
        self._search.clear()
        self._props.clear()
        self._tags.clear()
        self._banner.clear()
        self._refresh_stats()
        self._task_panel.set_running(0, 1, "正在准备…")
        self._app.notifier.info("正在准备…")

        def run_job(
            *,
            on_progress: Callable[[int, int, str], None] | None = None,
            on_log: Callable[[LogRecord], None] | None = None,
            is_cancelled: Callable[[], bool] | None = None,
        ) -> Any:
            return self._job(
                model,
                on_progress=on_progress,
                on_log=on_log,
                is_cancelled=is_cancelled or (lambda: False),
            )

        self._handle = self._app.runner.submit(
            run_job,
            on_progress=self._on_progress,
            on_log=self._on_log,
            on_succeeded=self._on_succeeded,
            on_failed=self._on_failed,
            on_cancelled=self._on_cancelled,
            exclusive=self._exclusive,
        )

    def _cancel(self) -> None:
        if self._handle is not None:
            self._handle.cancel()
            self._app.notifier.warning("正在取消…")

    def _on_progress(self, current: int, total: int, message: str) -> None:
        self._task_panel.set_running(current, total, message)
        self._table.set_busy(True, message)
        self._app.notifier.info(message)

    def _on_log(self, record: object) -> None:
        if isinstance(record, LogRecord):
            self._log.append(record)
            self._refresh_stats()

    def _on_succeeded(self, result: object) -> None:
        outcome = JobOutcome.from_raw(result)
        self._table.set_busy(False)
        self.present_outcome(outcome)
        self._task_panel.set_finished(outcome.message)
        tone = "success" if outcome.rows else "warning"
        self._banner.set_notice(outcome.message, tone=tone)
        if outcome.rows:
            self._app.notifier.success(outcome.message)
        else:
            self._app.notifier.warning(outcome.message)
        self._handle = None

    def _on_failed(self, message: str) -> None:
        text = message.strip() or "任务失败"
        self._table.set_busy(False)
        self._task_panel.set_failed(text)
        self._app.notifier.error(text)
        self._banner.set_notice(text, tone="error")
        detail = self._handle.error_traceback if self._handle is not None else None
        fail(self, "任务失败", text, detail=detail)
        self._handle = None

    def _on_cancelled(self) -> None:
        self._table.set_busy(False)
        self._task_panel.set_idle("已取消")
        self._app.notifier.warning("已取消")
        self._banner.set_notice("已取消", tone="warning")
        self._handle = None

    def _refresh_tags(self, rows: Sequence[dict[str, Any]]) -> None:
        labels: list[str] = []
        for row in rows:
            labels.extend(self.tag_values(row))
        self._tags.set_labels(labels)
