"""组件目录：按组看外观，用状态矩阵核对悬停、按下和焦点。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from psi6 import App, JobOutcome, TaskHandle
from psi6.jobs.file_index import FILE_INDEX_COLUMNS, FileIndexParams, run_file_index
from psi6.theme.builtin import (
    Brass,
    Compact,
    CompactDark,
    ModernDark,
    Mono,
    Obsidian,
    Pine,
)
from psi6.theme.theme import Theme
from psi6.ui.action_bar import ActionBar
from psi6.ui.app_shell import AppShell, NavDestination
from psi6.ui.banner import Banner
from psi6.ui.buttons import danger_button, ghost_button, primary_button, text_button
from psi6.ui.chrome import PageHeader
from psi6.ui.collapsible import Collapsible
from psi6.ui.data_table import DataTable, TableColumn
from psi6.ui.desktop_window import DesktopWindow
from psi6.ui.file_input import FileInput, FolderInput
from psi6.ui.form import FormError, pydantic_form
from psi6.ui.icon import IconButton
from psi6.ui.log_panel import LogPanel
from psi6.ui.search_field import SearchField
from psi6.ui.segmented import SegmentedControl
from psi6.ui.status_badge import StatusBadge
from psi6.ui.status_progress import StatusProgress
from psi6.ui.switch import Switch

_DESTINATIONS = (
    NavDestination("buttons", "按钮", "check"),
    NavDestination("inputs", "输入", "file"),
    NavDestination("choice", "选择", "sliders"),
    NavDestination("nav", "导航", "sidebar"),
    NavDestination("data", "数据", "table"),
    NavDestination("feedback", "反馈", "info"),
    NavDestination("window", "窗口", "monitor"),
    NavDestination("states", "状态", "circle-dot"),
    NavDestination("theme", "主题", "sun"),
    NavDestination("compose", "组合", "grid"),
)

_STATE_ROWS = ("默认", "悬停", "按下", "焦点", "禁用", "错误", "选中")
_NA = "不适用"


class KitWindow(DesktopWindow):
    """七组控件、状态矩阵、四种组合，以及一页文件索引组合。"""

    def __init__(self, app: App, parent: QWidget | None = None) -> None:
        super().__init__(title="psi6 组件目录", icon="grid", frameless=True, parent=parent)
        self._app = app
        self.resize(1180, 760)
        self.shell = AppShell(_DESTINATIONS, title="psi6")
        self._banner = Banner()
        holder = QWidget()
        holder_layout = QVBoxLayout(holder)
        holder_layout.setContentsMargins(0, 0, 0, 0)
        holder_layout.setSpacing(0)
        holder_layout.addWidget(self._banner)
        holder_layout.addWidget(self.shell, stretch=1)
        self.set_body(holder)
        pages = {
            "buttons": self._page_buttons,
            "inputs": self._page_inputs,
            "choice": self._page_choice,
            "nav": self._page_nav,
            "data": self._page_data,
            "feedback": self._page_feedback,
            "window": self._page_window,
            "states": self._page_states,
            "theme": self._page_theme,
            "compose": self._page_compose,
        }
        for page_id, factory in pages.items():
            self.shell.add_page(page_id, factory())
        self.shell.show_page("buttons")
        self.statusBar().showMessage("组件目录 · 四种组合在「主题」页切换")

    def show_page(self, page_id: str) -> None:
        self.shell.show_page(page_id)

    def _wrap(self, header: PageHeader, body: QWidget) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)
        layout.addWidget(header)
        layout.addWidget(body, stretch=1)
        return page

    def _page_buttons(self) -> QWidget:
        header = PageHeader("按钮", hint="主按钮实心，次按钮描边，危险按钮用危险色，文字按钮无边框。", icon="check")
        bar = ActionBar()
        bar.add_left(primary_button("开始"))
        bar.add_left(ghost_button("取消"))
        bar.add_left(danger_button("删除"))
        bar.add_left(text_button("详情"))
        bar.add_right(IconButton("search", label="搜索"))
        body = QWidget()
        column = QVBoxLayout(body)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(12)
        column.addWidget(bar)
        column.addWidget(SegmentedControl(("列表", "网格")))
        column.addStretch()
        return self._wrap(header, body)

    def _page_inputs(self) -> QWidget:
        header = PageHeader("输入", hint="输入落在下沉表面。焦点用焦点环，错误旁边要有文字。", icon="file")
        name = QLineEdit()
        name.setPlaceholderText("名称")
        body = QWidget()
        column = QVBoxLayout(body)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(12)
        column.addWidget(name)
        column.addWidget(SearchField())
        column.addWidget(FileInput())
        column.addWidget(FolderInput())
        column.addStretch()
        return self._wrap(header, body)

    def _page_choice(self) -> QWidget:
        header = PageHeader("选择", hint="勾选、单选、组合框和开关共用同一套选中色。", icon="sliders")
        combo = QComboBox()
        combo.addItems(("浅色", "深色"))
        body = QWidget()
        column = QVBoxLayout(body)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(12)
        column.addWidget(QCheckBox("包含子目录"))
        column.addWidget(QRadioButton("现代"))
        compact = QRadioButton("紧凑")
        compact.setChecked(True)
        column.addWidget(compact)
        column.addWidget(combo)
        column.addWidget(Switch(checked=True))
        column.addStretch()
        return self._wrap(header, body)

    def _page_nav(self) -> QWidget:
        header = PageHeader("导航", hint="侧栏就是本窗口。这里看标签页、折叠区和一条导航项。", icon="sidebar")
        tabs = QTabWidget()
        tabs.addTab(QLabel("概览"), "概览")
        tabs.addTab(QLabel("明细"), "明细")
        disabled = QLabel("停用")
        tabs.addTab(disabled, "停用")
        tabs.setTabEnabled(2, False)
        section = Collapsible("高级选项", expanded=True)
        section.add_widget(QLabel("折叠区只收不常用字段。"))
        sample = QPushButton("当前页")
        sample.setObjectName("psi6NavItem")
        sample.setCheckable(True)
        sample.setChecked(True)
        body = QWidget()
        column = QVBoxLayout(body)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(12)
        column.addWidget(tabs)
        column.addWidget(section)
        column.addWidget(sample)
        column.addStretch()
        return self._wrap(header, body)

    def _page_data(self) -> QWidget:
        header = PageHeader("数据", hint="表格选中用悬停底加正文色。空表用空态，不另画一块占位。", icon="table")
        filled = DataTable(
            (
                TableColumn("name", "名称"),
                TableColumn("state", "状态"),
            )
        )
        filled.set_rows(({"name": "索引", "state": "就绪"}, {"name": "导出", "state": "等待"}))
        filled.select_row(0)
        empty = DataTable((TableColumn("name", "名称"),))
        badges = QWidget()
        row = QHBoxLayout(badges)
        row.setContentsMargins(0, 0, 0, 0)
        for tone, text in (("success", "成功"), ("warning", "警告"), ("error", "失败"), ("info", "信息")):
            row.addWidget(StatusBadge(text, tone=tone))
        row.addStretch()
        body = QWidget()
        column = QVBoxLayout(body)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(12)
        column.addWidget(filled, stretch=1)
        column.addWidget(badges)
        column.addWidget(empty, stretch=1)
        return self._wrap(header, body)

    def _page_feedback(self) -> QWidget:
        header = PageHeader("反馈", hint="横幅留在页内。短句走通知。进度在状态栏。", icon="info")
        banner = Banner()
        banner.set_notice("目录为空时把原因写在横幅里。", tone="warning")
        toast = primary_button("弹出成功通知")
        toast.clicked.connect(lambda: self._app.notifier.success("已完成"))
        self._feedback_progress = StatusProgress(self.statusBar())
        show_progress = ghost_button("状态栏进度")
        show_progress.clicked.connect(lambda: self._feedback_progress.set_progress(1, 3, "读取"))
        self._busy_table = DataTable((TableColumn("name", "名称"),))
        busy = ghost_button("表格忙碌")
        busy.clicked.connect(lambda: self._busy_table.set_busy(True, "正在索引"))
        idle = ghost_button("结束忙碌")
        idle.clicked.connect(lambda: self._busy_table.set_busy(False))
        actions = ActionBar()
        actions.add_left(toast)
        actions.add_left(show_progress)
        actions.add_left(busy)
        actions.add_left(idle)
        body = QWidget()
        column = QVBoxLayout(body)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(12)
        column.addWidget(banner)
        column.addWidget(actions)
        column.addWidget(self._busy_table, stretch=1)
        return self._wrap(header, body)

    def _page_window(self) -> QWidget:
        header = PageHeader(
            "窗口",
            hint="本目录窗口使用自绘标题栏。业务窗口默认用系统标题栏，frameless=True 才自绘。",
            icon="monitor",
        )
        note = QLabel(
            "关闭窗口不取消任务。没有托盘时关闭仍退出。进度没有指定位置时放在状态栏右侧。"
        )
        note.setObjectName("psi6Hint")
        note.setWordWrap(True)
        body = QWidget()
        column = QVBoxLayout(body)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(12)
        column.addWidget(note)
        column.addStretch()
        return self._wrap(header, body)

    def _page_states(self) -> QWidget:
        """同屏矩阵。悬停、按下和焦点用 psi6State 画出来，不要求移动鼠标。"""

        header = PageHeader(
            "状态",
            hint="行是状态，列是控件。不适用的格子写明。禁用按钮不能点击，错误旁边有文字。",
            icon="circle-dot",
        )
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)
        columns = ("主按钮", "次按钮", "输入", "侧栏")
        for column, title in enumerate(columns, start=1):
            label = QLabel(title)
            label.setObjectName("psi6SectionTitle")
            grid.addWidget(label, 0, column)
        for row, state in enumerate(_STATE_ROWS, start=1):
            name = QLabel(state)
            name.setObjectName("psi6Hint")
            grid.addWidget(name, row, 0)
            grid.addWidget(self._state_cell("primary", state), row, 1)
            grid.addWidget(self._state_cell("ghost", state), row, 2)
            grid.addWidget(self._state_cell("field", state), row, 3)
            grid.addWidget(self._state_cell("nav", state), row, 4)
        body = QWidget()
        column = QVBoxLayout(body)
        column.setContentsMargins(0, 0, 0, 0)
        column.addLayout(grid)
        column.addStretch()
        return self._wrap(header, body)

    def _state_cell(self, kind: str, state: str) -> QWidget:
        if kind == "primary":
            return self._button_state(primary_button, state, pressed=True, error=False, selected=False)
        if kind == "ghost":
            return self._button_state(ghost_button, state, pressed=True, error=False, selected=False)
        if kind == "field":
            return self._field_state(state)
        return self._nav_state(state)

    def _button_state(
        self,
        factory,
        state: str,
        *,
        pressed: bool,
        error: bool,
        selected: bool,
    ) -> QWidget:
        if state == "按下" and not pressed:
            return self._na()
        if state == "错误" and not error:
            return self._na()
        if state == "选中" and not selected:
            return self._na()
        button = factory(state)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        if state == "禁用":
            button.setEnabled(False)
            return button
        token = {"悬停": "hover", "按下": "pressed", "焦点": "focus"}.get(state)
        if token:
            self._force_visual(button, token)
        return button

    def _field_state(self, state: str) -> QWidget:
        if state in {"按下", "选中"}:
            return self._na()
        if state == "错误":
            box = QWidget()
            row = QHBoxLayout(box)
            row.setContentsMargins(0, 0, 0, 0)
            edit = QLineEdit("缺少目录")
            edit.setProperty("invalid", True)
            edit.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self._force_visual(edit, "")
            error = QLabel("请选择一个存在的目录")
            error.setObjectName("psi6Error")
            row.addWidget(edit, stretch=1)
            row.addWidget(error)
            return box
        edit = QLineEdit()
        edit.setPlaceholderText(state)
        edit.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        if state == "禁用":
            edit.setEnabled(False)
            return edit
        token = {"悬停": "hover", "焦点": "focus"}.get(state, "")
        if token:
            self._force_visual(edit, token)
        return edit

    def _nav_state(self, state: str) -> QWidget:
        if state == "错误":
            return self._na()
        button = QPushButton(state)
        button.setObjectName("psi6NavItem")
        button.setCheckable(True)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        if state == "禁用":
            button.setEnabled(False)
            return button
        if state == "选中":
            button.setChecked(True)
            return button
        token = {"悬停": "hover", "按下": "pressed", "焦点": "focus"}.get(state)
        if token:
            self._force_visual(button, token)
        return button

    def _force_visual(self, widget: QWidget, state: str) -> None:
        if state:
            widget.setProperty("psi6State", state)
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def _na(self) -> QLabel:
        label = QLabel(_NA)
        label.setObjectName("psi6Hint")
        return label

    def _page_theme(self) -> QWidget:
        header = PageHeader("主题", hint="切换后上面各页一起变。尺寸只由 style 决定。", icon="sun")
        presets = (
            ("现代浅色", "light"),
            ("现代深色", ModernDark),
            ("紧凑浅色", Compact),
            ("紧凑深色", CompactDark),
        )
        extra = (
            ("黑白 Mono", Mono),
            ("深黑 Obsidian", Obsidian),
            ("墨绿 Pine", Pine),
            ("黄铜 Brass", Brass),
        )
        body = QWidget()
        column = QVBoxLayout(body)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(12)
        for row_themes in (presets, extra):
            actions = ActionBar()
            for label, theme in row_themes:
                button = primary_button(label) if row_themes is presets else ghost_button(label)
                button.clicked.connect(lambda _checked=False, chosen=theme: self._apply_theme(chosen))
                actions.add_left(button)
            column.addWidget(actions)
        note = QLabel("macOS、Linux 和 150% 缩放尚未在本机验证。")
        note.setObjectName("psi6Hint")
        note.setWordWrap(True)
        column.addWidget(note)
        column.addStretch()
        return self._wrap(header, body)

    def _page_compose(self) -> QWidget:
        """文件索引那一套放进本窗口，用来看组合后是否仍然一致。"""

        header = PageHeader(
            "组合",
            hint="表单、开始、取消、空表、忙碌、日志和状态栏进度在同一个窗口里。",
            icon="grid",
        )
        form = pydantic_form(self._app.load_config(FileIndexParams))
        start = primary_button("开始")
        cancel = ghost_button("取消")
        cancel.setEnabled(False)
        table = DataTable(FILE_INDEX_COLUMNS)
        log = LogPanel()
        progress = StatusProgress(self.statusBar())
        current: list[TaskHandle] = []

        def set_idle(message: str) -> None:
            table.set_busy(False)
            progress.finish(message)
            start.setEnabled(True)
            cancel.setEnabled(False)
            self.statusBar().showMessage(message)

        def start_job() -> None:
            try:
                params = form.get_model()
            except FormError as exc:
                self._app.notifier.error(str(exc))
                return
            self._app.save_config(params)
            start.setEnabled(False)
            cancel.setEnabled(True)
            table.set_busy(True, "正在索引")

            def ok(outcome: JobOutcome) -> None:
                table.set_rows(outcome.rows)
                set_idle(outcome.message)

            current[:] = [
                self._app.runner.submit(
                    run_file_index,
                    params,
                    on_progress=progress.set_progress,
                    on_log=log.append,
                    on_succeeded=ok,
                    on_failed=lambda message: (self._app.notifier.error(message), set_idle(message)),
                    on_cancelled=lambda: set_idle("已取消"),
                    exclusive="index",
                )
            ]

        start.clicked.connect(start_job)
        cancel.clicked.connect(lambda: current and current[-1].cancel())
        actions = ActionBar()
        actions.add_left(start)
        actions.add_left(cancel)
        body = QWidget()
        column = QVBoxLayout(body)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(10)
        column.addWidget(form)
        column.addWidget(actions)
        column.addWidget(table, stretch=1)
        column.addWidget(log, stretch=1)
        return self._wrap(header, body)

    def _apply_theme(self, theme: str | Theme | type[Theme]) -> None:
        self._app.set_theme(theme)
        self.shell.sidebar.apply_metrics()
        self.shell.sidebar.refresh_icons()
        self.update()
        name = theme if isinstance(theme, str) else theme.name
        self._banner.set_notice(f"已应用主题：{name}", tone="success")
        self.statusBar().showMessage(f"主题 {name}")


def main() -> None:
    """打开组件目录。"""

    app = App("psi6-kit", theme="light")
    raise SystemExit(app.run(KitWindow(app), tray=True, restore_geometry=True))
