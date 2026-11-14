"""组件目录：按组看外观，用状态矩阵核对悬停、按下和焦点。"""

from __future__ import annotations

import contextlib
import logging
from typing import Any

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
from psi6.examples.file_index import FILE_INDEX_COLUMNS
from psi6.jobs.file_index import FileIndexParams, run_file_index
from psi6.runtime.logs import LogLevel, LogRecord
from psi6.theme.apply import apply_psi6_button_style
from psi6.theme.builtin import Compact, CompactDark, Graphite, ModernDark
from psi6.theme.theme import Theme
from psi6.ui.action_bar import ActionBar
from psi6.ui.app_shell import AppShell, NavDestination
from psi6.ui.banner import Banner
from psi6.ui.buttons import danger_button, ghost_button, primary_button, text_button
from psi6.ui.chrome import PageHeader
from psi6.ui.collapsible import Collapsible
from psi6.ui.column_picker import ColumnPicker, column_toggle_menu
from psi6.ui.context_menu import MenuAction, MenuTarget
from psi6.ui.data_table import DataTable, TableColumn
from psi6.ui.desktop_window import DesktopWindow
from psi6.ui.empty_state import EmptyState
from psi6.ui.file_input import FileInput, FolderInput
from psi6.ui.form import FormError, pydantic_form
from psi6.ui.icon import IconButton
from psi6.ui.log_console import LogConsole
from psi6.ui.log_panel import LogPanel
from psi6.ui.property_list import PropertyList
from psi6.ui.search_field import SearchField
from psi6.ui.segmented import SegmentedControl
from psi6.ui.status_badge import StatusBadge
from psi6.ui.status_progress import StatusProgress
from psi6.ui.switch import Switch
from psi6.ui.tab_view import TabView
from psi6.ui.tone import Tone
from psi6.ui.workspace import Workspace


def _property_view(
    row: dict[str, object] | None, labels: dict[str, str]
) -> dict[str, object] | None:
    """属性栏用可读名称，不把字段键直接摊开。"""

    if row is None:
        return None
    return {labels.get(str(key), str(key)): value for key, value in row.items()}


_DESTINATIONS = (
    NavDestination("buttons", "按钮", "check"),
    NavDestination("inputs", "输入", "file"),
    NavDestination("choice", "选择", "sliders"),
    NavDestination("nav", "导航", "sidebar"),
    NavDestination("data", "数据", "table"),
    NavDestination("shell", "壳", "sidebar"),
    NavDestination("formlab", "表单", "sliders"),
    NavDestination("inspect", "检查", "table"),
    NavDestination("dense", "密度", "list"),
    NavDestination("feedback", "反馈", "info"),
    NavDestination("window", "窗口", "monitor"),
    NavDestination("states", "状态", "circle-dot"),
    NavDestination("theme", "主题", "sun"),
    NavDestination("workbench", "多视图", "layout-dashboard"),
    NavDestination("compose", "组合", "grid"),
)

_STATE_ROWS = ("默认", "悬停", "按下", "焦点", "禁用", "错误", "选中")
_NA = "不适用"


class KitWindow(DesktopWindow):
    """组件目录。壳、数据和表单页同时放正常、空、错误和长文本。"""

    def __init__(self, app: App, parent: QWidget | None = None) -> None:
        super().__init__(title="psi6 组件目录", icon="grid", frameless=True, parent=parent)
        self._app = app
        self._density_note: QLabel | None = None
        self._focus_note: QLabel | None = None
        self._motion_note: QLabel | None = None
        self._motion_switch: Switch | None = None
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
            "shell": self._page_shell,
            "formlab": self._page_formlab,
            "inspect": self._page_inspect,
            "dense": self._page_dense,
            "feedback": self._page_feedback,
            "window": self._page_window,
            "states": self._page_states,
            "theme": self._page_theme,
            "workbench": self._page_workbench,
            "compose": self._page_compose,
        }
        for page_id, factory in pages.items():
            self.shell.add_page(page_id, factory())
        self.shell.show_page("buttons")
        app.density_changed.connect(self._on_density_changed)
        self.statusBar().showMessage("组件目录 · 浅色、深色和密度在「主题」页切换")

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
        header = PageHeader(
            "按钮", hint="主按钮实心，次按钮描边，危险按钮用危险色，文字按钮无边框。", icon="check"
        )
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
        header = PageHeader(
            "输入", hint="输入落在下沉表面。焦点用焦点环，错误旁边要有文字。", icon="file"
        )
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
        header = PageHeader(
            "选择", hint="勾选、单选、组合框和开关共用同一套选中色。", icon="sliders"
        )
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
        header = PageHeader(
            "导航", hint="侧栏就是本窗口。这里看标签页、折叠区和一条导航项。", icon="sidebar"
        )
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
        apply_psi6_button_style(sample)
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
        header = PageHeader(
            "数据",
            hint="from psi6.ui.data_table import DataTable。正常行、空表、错误状态和长文本放在同一页。",
            icon="table",
        )
        filled = DataTable(
            (
                TableColumn("name", "名称", stretch=True),
                TableColumn("state", "状态"),
            )
        )
        filled.set_rows(
            (
                {"name": "索引", "state": "就绪"},
                {"name": "导出", "state": "等待"},
                {
                    "name": "这条名称故意写得很长，用来看单元格在窄列里是否仍然可读，而不是被切成没有上下文的碎片。",
                    "state": "失败",
                },
            )
        )
        filled.select_row(0)
        empty = DataTable((TableColumn("name", "名称"),))
        badges = QWidget()
        row = QHBoxLayout(badges)
        row.setContentsMargins(0, 0, 0, 0)
        badge_rows: tuple[tuple[Tone, str], ...] = (
            ("success", "成功"),
            ("warning", "警告"),
            ("error", "失败"),
            ("info", "信息"),
        )
        for tone, text in badge_rows:
            row.addWidget(StatusBadge(text, tone=tone))
        row.addStretch()

        # 列管理：右边勾选显示哪几列，左边的表格立刻跟着变。
        managed = DataTable(
            (
                TableColumn("id", "编号"),
                TableColumn("name", "名称", stretch=True),
                TableColumn("owner", "负责人"),
                TableColumn("state", "状态"),
                TableColumn("updated", "更新时间"),
            )
        )
        managed.set_rows(
            (
                {"id": 1, "name": "生成索引", "owner": "我", "state": "就绪", "updated": "今天"},
                {"id": 2, "name": "导出结果", "owner": "同事", "state": "等待", "updated": "昨天"},
                {"id": 3, "name": "同步缓存", "owner": "我", "state": "失败", "updated": "上周"},
            )
        )
        picker = ColumnPicker()
        picker.setObjectName("psi6KitColumnPicker")
        picker.set_columns(managed.columns())
        picker.columns_changed.connect(managed.set_visible_columns)

        def _toggle_column(key: str, visible: bool) -> None:
            picker.set_visible(key, visible)

        # 列头右键也能勾选列，和右边的面板是同一份状态。
        managed.column_menu(
            lambda target: column_toggle_menu(
                managed.columns(),
                managed.visible_columns(),
                on_toggle=_toggle_column,
            )
        )

        managed_row = QWidget()
        managed_layout = QHBoxLayout(managed_row)
        managed_layout.setContentsMargins(0, 0, 0, 0)
        managed_layout.setSpacing(12)
        managed_layout.addWidget(managed, stretch=3)
        managed_layout.addWidget(picker, stretch=1)

        body = QWidget()
        column = QVBoxLayout(body)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(12)
        column.addWidget(filled, stretch=1)
        column.addWidget(badges)
        column.addWidget(empty, stretch=1)
        column.addWidget(managed_row, stretch=2)
        return self._wrap(header, body)

    def _page_feedback(self) -> QWidget:
        header = PageHeader(
            "反馈",
            hint="横幅留在页内。短句走通知。进度在状态栏。下方是终端式彩色日志。",
            icon="info",
        )
        banner = Banner()
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
        console = LogConsole(max_entries=200)
        for level, message in (
            (LogLevel.DEBUG, "扫描目录"),
            (LogLevel.INFO, "开始读取"),
            (LogLevel.SUCCESS, "写入完成"),
            (LogLevel.WARNING, "汇率缺失"),
            (LogLevel.ERROR, "月份解析失败"),
        ):
            console.append(LogRecord(level, message, extra={"logger": "psi6.kit"}))
        demo_log = logging.getLogger("psi6.kit.demo")
        demo_log.setLevel(logging.DEBUG)
        demo_log.propagate = False
        demo_handler = console.handler()
        demo_log.addHandler(demo_handler)

        def drop_demo_handler(*_args: object) -> None:
            demo_log.removeHandler(demo_handler)

        console.destroyed.connect(drop_demo_handler)
        more = ghost_button("再写一行")
        more.clicked.connect(lambda: demo_log.info("来自 logging 的一行"))
        actions = ActionBar()
        actions.add_left(toast)
        actions.add_left(show_progress)
        actions.add_left(busy)
        actions.add_left(idle)
        actions.add_left(more)
        body = QWidget()
        column = QVBoxLayout(body)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(12)
        column.addWidget(banner)
        banner.set_notice("目录为空时把原因写在横幅里。", tone="warning")
        column.addWidget(actions)
        column.addWidget(console, stretch=1)
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
        column_layout = QVBoxLayout(body)
        column_layout.setContentsMargins(0, 0, 0, 0)
        column_layout.addLayout(grid)
        column_layout.addStretch()
        return self._wrap(header, body)

    def _state_cell(self, kind: str, state: str) -> QWidget:
        if kind == "primary":
            return self._button_state(
                primary_button, state, pressed=True, error=False, selected=False
            )
        if kind == "ghost":
            return self._button_state(
                ghost_button, state, pressed=True, error=False, selected=False
            )
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
        apply_psi6_button_style(button)
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

    def _page_shell(self) -> QWidget:
        """应用壳：工具栏、面包屑和可省略的分栏。"""

        header = PageHeader(
            "壳",
            hint="from psi6.ui.workspace import Workspace。多页导航仍用 AppShell，不要用它代替侧栏。",
            icon="sidebar",
        )
        work = Workspace()
        work.setObjectName("psi6PrototypeShell")
        work.set_crumbs(["工作区", "壳", "预览"])
        work.toolbar.add_primary(primary_button("开始"))
        work.toolbar.add_secondary(ghost_button("取消"))
        empty = EmptyState("空栏", "不需要这一栏时不要创建它。")
        long_copy = QLabel(
            "主区与左右栏共用画布，不另套一层卡片。这段文字故意写长，用来看分栏里的说明是否顶对齐，而不是浮在栏的正中。"
        )
        long_copy.setWordWrap(True)
        long_copy.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        error = QLabel("路径无效")
        error.setObjectName("psi6Error")
        error.setWordWrap(True)
        work.set_pane("left", empty)
        work.set_pane("center", long_copy)
        work.set_pane("right", error)
        work.set_stretch("left", 2)
        work.set_stretch("center", 3)
        work.set_stretch("right", 2)
        return self._wrap(header, work)

    def _page_formlab(self) -> QWidget:
        """分组、可搜索选项，以及提交后留在字段下的模型错误。"""

        from enum import StrEnum

        from pydantic import BaseModel, Field

        class Pace(StrEnum):
            ALPHA = "alpha"
            BETA = "beta"
            GAMMA = "gamma"

        class Sample(BaseModel):
            pace: Pace = Field(
                default=Pace.ALPHA,
                description="节奏",
                json_schema_extra={"group": "扫描", "search": True},
            )
            count: int = Field(
                default=1, gt=0, le=10, description="数量", json_schema_extra={"group": "扫描"}
            )
            label: str = Field(default="", description="标签", json_schema_extra={"group": "说明"})
            note: str = Field(
                default="这条备注故意写长，用来看分组下面的文字是否仍留在字段里，而不是被卡片裁掉。",
                description="备注",
                json_schema_extra={"group": "说明"},
            )

        header = PageHeader(
            "表单",
            hint="pydantic_form。分组用 group，可搜索选项用 search。控件接受的值仍以模型校验为准。",
            icon="sliders",
        )
        form = pydantic_form(Sample)
        form.setObjectName("psi6PrototypeForm")
        count = next(
            (
                edit
                for edit in form.findChildren(QLineEdit)
                if edit.property("psi6Field") == "count"
            ),
            None,
        )
        if count is not None:
            count.setText("0")
            with contextlib.suppress(FormError):
                form.get_model()
        error = QLabel("数量 0 的错误已经留在字段下。改回 1 到 10 再点校验会通过。")
        error.setObjectName("psi6Hint")
        error.setWordWrap(True)
        check = ghost_button("校验")

        def validate() -> None:
            try:
                form.get_model()
            except FormError as exc:
                self.statusBar().showMessage(str(exc))
                return
            self.statusBar().showMessage("表单有效")

        check.clicked.connect(validate)
        body = QWidget()
        column = QVBoxLayout(body)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(12)
        column.addWidget(error)
        column.addWidget(form)
        column.addWidget(check)
        column.addStretch()
        return self._wrap(header, body)

    def _page_inspect(self) -> QWidget:
        """数据检查：排序、筛选、空结果和选中行属性。"""

        header = PageHeader(
            "检查",
            hint="DataTable.sort_by 与表头点击。搜索只筛选，属性栏显示选中行。数据是普通记录。",
            icon="table",
        )
        rows = [
            {
                "name": f"记录 {index:03d}",
                "value": index,
                "note": "这条说明故意写得很长，用来看单元格是否仍可读。" if index == 3 else "正常",
            }
            for index in range(200)
        ]
        table = DataTable(
            (
                TableColumn("name", "名称", stretch=True),
                TableColumn("value", "数值"),
                TableColumn("note", "说明", stretch=True),
            )
        )
        table.setObjectName("psi6PrototypeInspect")
        table.set_rows(rows)
        props = PropertyList()
        props.setObjectName("psi6PrototypeProps")
        search = SearchField(placeholder="筛选名称或说明")
        search.setObjectName("psi6PrototypeSearch")
        search.query_changed.connect(table.set_filter)
        clear = ghost_button("清除筛选")
        clear.clicked.connect(search.clear)
        labels = {"name": "名称", "value": "数值", "note": "说明"}
        table.selection_changed.connect(
            lambda: props.set_values(
                _property_view(table.selected_rows()[0] if table.selected_rows() else None, labels)
            )
        )
        table.select_row(3)
        work = Workspace()
        work.set_crumbs(["数据", "检查"])
        work.toolbar.add_primary(search)
        work.toolbar.add_secondary(clear)
        work.set_pane("center", table)
        work.set_pane("right", props)
        work.set_stretch("center", 3)
        work.set_stretch("right", 1)
        return self._wrap(header, work)

    def _page_dense(self) -> QWidget:
        """高密度三栏。记录仍是通用字典，用来看空间，不是行业界面。"""

        header = PageHeader(
            "密度",
            hint="这一页用紧凑密度审定。主题页切到紧凑后，留白和行高一起收紧。记录仍是普通字典。",
            icon="list",
        )
        records = [
            {
                "name": f"项 {index}",
                "value": index * 3,
                "state": "正常" if index % 5 else "留意",
            }
            for index in range(40)
        ]
        names = DataTable((TableColumn("name", "名称", stretch=True),))
        names.set_rows(records)
        values = DataTable(
            (
                TableColumn("name", "名称", stretch=True),
                TableColumn("value", "数值"),
                TableColumn("state", "状态"),
            )
        )
        values.setObjectName("psi6PrototypeDense")
        values.set_rows(records)
        detail = PropertyList(empty_title="未选择", empty_hint="选择中间一行查看数值。")
        labels = {"name": "名称", "value": "数值", "state": "状态"}
        names.selection_changed.connect(
            lambda: detail.set_values(
                _property_view(names.selected_rows()[0] if names.selected_rows() else None, labels)
            )
        )
        names.select_row(5)
        work = Workspace()
        work.set_crumbs(["工作台", "密度"])
        for label in ("刷新", "标记", "导出"):
            work.toolbar.add_primary(ghost_button(label))
        work.toolbar.add_secondary(ghost_button("清除"))
        work.set_pane("left", names)
        work.set_pane("center", values)
        work.set_pane("right", detail)
        work.set_stretch("left", 2)
        work.set_stretch("center", 5)
        work.set_stretch("right", 2)
        return self._wrap(header, work)

    def _page_theme(self) -> QWidget:
        header = PageHeader(
            "主题",
            hint="同一套语言的浅色、深色和两种密度。配色与尺寸分开，密度可跟随窗口自动收紧。",
            icon="sun",
        )
        presets = (
            ("现代浅色", "light"),
            ("现代深色", ModernDark),
            ("紧凑浅色", Compact),
            ("紧凑深色", CompactDark),
            ("石墨铜", Graphite),
        )
        body = QWidget()
        column = QVBoxLayout(body)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(12)
        actions = ActionBar()
        actions.setObjectName("psi6ThemePresets")
        for label, theme in presets:
            button = primary_button(label)
            button.clicked.connect(lambda _checked=False, chosen=theme: self._apply_theme(chosen))
            actions.add_left(button)
        column.addWidget(actions)

        density_label = QLabel("响应式密度：窗口变小或高 DPI 时自动收紧，也可以手动固定。")
        density_label.setObjectName("psi6Hint")
        density_label.setWordWrap(True)
        column.addWidget(density_label)
        density_bar = ActionBar()
        density_bar.setObjectName("psi6DensityModes")
        for label, mode in (("自动", "auto"), ("宽松", "modern"), ("紧凑", "compact")):
            button = ghost_button(label)
            button.setProperty("densityMode", mode)
            button.clicked.connect(lambda _checked=False, chosen=mode: self._apply_density(chosen))
            density_bar.add_left(button)
        column.addWidget(density_bar)
        self._density_note = QLabel(self._density_text())
        self._density_note.setObjectName("psi6Hint")
        self._density_note.setWordWrap(True)
        column.addWidget(self._density_note)

        focus_label = QLabel(
            "应用默认不画焦点环。组件目录为了展示状态矩阵，这里显式打开。"
            "聚焦时在控件外侧留出父级表面，再画焦点色。可以在这里关掉对照。"
        )
        focus_label.setObjectName("psi6Hint")
        focus_label.setWordWrap(True)
        column.addWidget(focus_label)
        focus_bar = ActionBar()
        focus_bar.setObjectName("psi6FocusRingModes")
        for label, enabled in (("关闭焦点环", False), ("开启焦点环", True)):
            button = ghost_button(label)
            button.setProperty("focusRing", enabled)
            button.clicked.connect(
                lambda _checked=False, chosen=enabled: self._apply_focus_ring(chosen)
            )
            focus_bar.add_left(button)
        column.addWidget(focus_bar)
        self._focus_note = QLabel(self._focus_text())
        self._focus_note.setObjectName("psi6Hint")
        column.addWidget(self._focus_note)

        motion_label = QLabel(
            "动效：悬停、按下和开关滑块共用同一套时长 token。关闭后所有动画直达终值，"
            "功能不变——用于无障碍、低性能设备和远程桌面。"
        )
        motion_label.setObjectName("psi6Hint")
        motion_label.setWordWrap(True)
        column.addWidget(motion_label)
        motion_bar = ActionBar()
        motion_bar.setObjectName("psi6MotionModes")
        for label, enabled in (("开启动效", True), ("减少动效", False)):
            button = ghost_button(label)
            button.setProperty("reducedMotion", not enabled)
            button.clicked.connect(
                lambda _checked=False, chosen=enabled: self._apply_motion(chosen)
            )
            motion_bar.add_left(button)
        column.addWidget(motion_bar)
        self._motion_note = QLabel(self._motion_text())
        self._motion_note.setObjectName("psi6Hint")
        self._motion_note.setWordWrap(True)
        column.addWidget(self._motion_note)

        switch_row = ActionBar()
        switch_row.setObjectName("psi6MotionProbe")
        switch_row.add_left(QLabel("试着拨动这个开关："))
        self._motion_switch = Switch(checked=True)
        switch_row.add_left(self._motion_switch)
        column.addWidget(switch_row)

        note = QLabel("macOS、Linux 和 150% 缩放尚未在本机验证。")
        note.setObjectName("psi6Hint")
        note.setWordWrap(True)
        column.addWidget(note)
        column.addStretch()
        return self._wrap(header, body)

    def _page_workbench(self) -> QWidget:
        header = PageHeader(
            "多视图与面板布局",
            hint=(
                "TabView 按 key 复用文档：可关闭、可拖动重排、全关掉显示空态；"
                "Workspace 的栏可显隐。标签顺序和分栏布局可以记录并恢复。"
            ),
            icon="layout-dashboard",
        )
        body = QWidget()
        column = QVBoxLayout(body)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(12)

        work = Workspace()
        work.setObjectName("psi6KitWorkbench")
        work.set_crumbs(["组件目录", "多视图"])
        tabs = TabView(empty_title="没有打开的文档", empty_hint="点「打开文档」新建一份。")
        tabs.setObjectName("psi6KitTabs")
        work.set_pane("left", QLabel("文档列表\n\n打开后可拖动标签重排"))
        work.set_pane("center", tabs)
        work.set_pane("right", QLabel("属性\n\n右栏可以显隐"))
        work.set_stretch("left", 1)
        work.set_stretch("center", 3)
        work.set_stretch("right", 1)

        note = QLabel("记录布局后，试着关掉文档、隐藏右栏，再点恢复。")
        note.setObjectName("psi6Hint")
        note.setWordWrap(True)

        actions = ActionBar()
        actions.setObjectName("psi6WorkbenchActions")
        docs: dict[str, tuple[QLabel, str]] = {}
        sequence = [0]
        saved_tabs: dict[str, Any] | None = None
        saved_work: dict[str, Any] | None = None

        def open_doc() -> None:
            sequence[0] += 1
            key = f"doc-{sequence[0]}"
            title = f"文档 {sequence[0]}"
            page = QLabel(f"{title} 的内容")
            page.setAlignment(Qt.AlignmentFlag.AlignCenter)
            docs[key] = (page, title)
            tabs.add_tab(key, title, page)
            note.setText(f"已打开 {tabs.count()} 份文档，当前：{tabs.current_key()}")

        def close_current() -> None:
            key = tabs.current_key()
            if key:
                tabs.close_tab(key)
            note.setText(f"剩余 {tabs.count()} 份文档")

        def toggle_right() -> None:
            visible = not work.is_pane_visible("right")
            work.set_pane_visible("right", visible)
            names = "、".join(work.visible_panes())
            note.setText(f"右栏：{'显示' if visible else '隐藏'}；可见栏 {names}")

        def remember() -> None:
            nonlocal saved_tabs, saved_work
            saved_tabs = tabs.state()
            saved_work = work.state()
            note.setText("已记录标签顺序、当前文档与分栏显隐/宽度")

        def restore() -> None:
            if saved_tabs is None or saved_work is None:
                note.setText("请先点「记录布局」")
                return
            # 状态只记 key，不记控件：恢复前先把被关掉的文档按 key 放回来，再对齐顺序。
            for key in saved_tabs["keys"]:
                if tabs.widget(key) is None and key in docs:
                    page, title = docs[key]
                    tabs.add_tab(key, title, page)
            tabs.set_state(saved_tabs)
            work.set_state(saved_work)
            note.setText("已恢复到记录的布局")

        for label, slot in (
            ("打开文档", open_doc),
            ("关闭当前", close_current),
            ("显隐右栏", toggle_right),
            ("记录布局", remember),
            ("恢复布局", restore),
        ):
            button = ghost_button(label)
            button.setProperty("workbenchAction", label)
            button.clicked.connect(lambda _checked=False, chosen=slot: chosen())
            actions.add_left(button)
        column.addWidget(actions)
        column.addWidget(note)
        column.addWidget(work, stretch=1)

        # 页签右键：关闭 / 关闭其他 / 关闭全部。命中哪个页签就作用于哪个，不用先切过去。
        def tab_menu(target: MenuTarget) -> list[MenuAction]:
            if not target.hit:
                return []
            key = str(target.key)
            others = list(tabs.keys())
            others.remove(key)
            return [
                MenuAction(f"关闭「{target.data}」", lambda: tabs.close_tab(key), icon="x"),
                MenuAction(
                    "关闭其他",
                    lambda: [tabs.close_tab(item) for item in others],
                    enabled=bool(others),
                ),
                MenuAction.line(),
                MenuAction(
                    "关闭全部",
                    tabs.close_all,
                    enabled=tabs.count() > 0,
                    dangerous=True,
                ),
            ]

        tabs.context_menu(tab_menu)
        open_doc()
        open_doc()
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

            def failed(message: str) -> None:
                self._app.notifier.error(message)
                set_idle(message)

            current[:] = [
                self._app.runner.submit(
                    run_file_index,
                    params,
                    on_progress=progress.set_progress,
                    on_log=log.append,
                    on_succeeded=ok,
                    on_failed=failed,
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

    def _density_text(self, effective: str | None = None) -> str:
        label = {
            "compact": "紧凑尺寸",
            "modern": "宽松尺寸",
            "theme": "主题自带尺寸",
        }.get(effective or "", "")
        detail = f" · 生效 {label}" if label else ""
        return (
            f"当前密度：{self._app.density_mode}{detail} · "
            f"控件高 {self._app.tokens.control_height}px"
        )

    def _focus_text(self) -> str:
        if self._app.focus_ring:
            return "焦点环：开启 · Tab 聚焦时显示品牌色环（键盘可见性）"
        return "焦点环：关闭 · 聚焦不改外观与尺寸，只抑制原生焦点框"

    def _motion_text(self) -> str:
        if self._app.reduced_motion:
            return "动效：已减少 · 所有动画直接到终值，功能不变"
        fast = self._app.tokens.motion_fast_ms
        slow = self._app.tokens.motion_ms
        return f"动效：开启 · 悬停与按下 {fast}ms，位移与显隐 {slow}ms"

    def _apply_motion(self, enabled: bool) -> None:
        self._app.set_reduced_motion(not enabled)
        if self._motion_note is not None:
            self._motion_note.setText(self._motion_text())
        self.shell.sidebar.refresh_icons()
        self.update()
        self._banner.set_notice(self._motion_text(), tone="success")
        self.statusBar().showMessage(self._motion_text())

    def _apply_focus_ring(self, enabled: bool) -> None:
        self._app.set_focus_ring(enabled)
        if self._focus_note is not None:
            self._focus_note.setText(self._focus_text())
        self.shell.sidebar.refresh_icons()
        self.update()
        self._banner.set_notice(self._focus_text(), tone="success")
        self.statusBar().showMessage(self._focus_text())

    def _apply_density(self, mode: str) -> None:
        self._app.set_density_mode(mode)
        self.shell.sidebar.refresh_icons()
        self.update()
        self._banner.set_notice(f"密度模式：{mode}", tone="success")
        if self._density_note is not None:
            self.statusBar().showMessage(self._density_note.text())

    def _on_density_changed(self, effective: str) -> None:
        """窗口尺寸触发的自动翻转也更新说明；窗口已销毁时静默跳过。"""

        with contextlib.suppress(Exception):
            if self._density_note is not None:
                self._density_note.setText(self._density_text(effective))


def main() -> None:
    """打开样例工作台。``--workbench`` 仍打开带状态矩阵的组件目录。"""

    import sys

    if "--workbench" in sys.argv:
        # 业务应用默认不画焦点环；组件目录要展示「状态矩阵」的焦点态，显式开启。
        app = App("psi6-kit", theme="light", density="auto", focus_ring=True)
        raise SystemExit(app.run(KitWindow(app), tray=True, restore_geometry=True))
    from psi6.examples.showroom import main as showroom_main

    showroom_main()
