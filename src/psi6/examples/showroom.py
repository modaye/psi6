"""样例工作台。

侧栏换页，页内按令牌、按钮、输入、数据、导航、反馈、容器、动效展开。
默认浅色就是石墨铜，焦点环默认关着。状态矩阵仍在 ``python -m psi6 kit --workbench``。
"""

from __future__ import annotations

from PySide6.QtCore import Property, QRectF, Qt
from PySide6.QtGui import QFont, QPen
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMenu,
    QPlainTextEdit,
    QProgressBar,
    QRadioButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from psi6 import App
from psi6.icons.render import icon_for
from psi6.theme.builtin import ModernDark
from psi6.theme.paint import as_color, create_painter
from psi6.theme.runtime import token_color
from psi6.ui import motion
from psi6.ui.app_shell import AppShell, NavDestination, Sidebar
from psi6.ui.banner import Banner
from psi6.ui.busy import BusyOverlay
from psi6.ui.buttons import danger_button, ghost_button, primary_button, set_loading, text_button
from psi6.ui.chrome import Card, Panel
from psi6.ui.collapsible import Collapsible
from psi6.ui.content_dialog import ContentDialog
from psi6.ui.data_table import DataTable, TableColumn
from psi6.ui.desktop_window import DesktopWindow
from psi6.ui.dialogs import confirm
from psi6.ui.drawer import Drawer
from psi6.ui.empty_state import EmptyState
from psi6.ui.flow_layout import FlowLayout
from psi6.ui.icon import IconButton
from psi6.ui.loading import BusyBar, Spinner
from psi6.ui.pagination import Pagination
from psi6.ui.search_field import SearchField
from psi6.ui.section import Section
from psi6.ui.segmented import SegmentedControl
from psi6.ui.skeleton import Skeleton
from psi6.ui.status_badge import StatusBadge
from psi6.ui.stepper import Stepper
from psi6.ui.style import set_style
from psi6.ui.switch import Switch
from psi6.ui.tag import Tag
from psi6.ui.toast import ToastHost
from psi6.ui.tree_view import TreeColumn, TreeNode, TreeView
from psi6.ui.underline_tabs import UnderlineTabs
from psi6.ui.workspace import Breadcrumb

_PAGES = (
    ("overview", "概览", "home", "色彩、字体、圆角、阴影和动效令牌。"),
    ("buttons", "按钮", "grid", "变体、尺寸、状态、图标按钮、标签和徽标。"),
    ("inputs", "输入", "sliders", "文本、选择、勾选、单选、开关和滑块。"),
    ("data", "数据", "layers", "表格、树、列表和分页。"),
    ("nav", "导航", "menu", "页签、面包屑、侧栏、菜单、分段和步骤。"),
    ("feedback", "反馈", "bell", "Toast、加载、骨架、空状态和横幅。"),
    ("containers", "容器", "copy", "卡片、折叠、抽屉和对话框。"),
    ("motion", "动效", "spark", "原则、缓动实验室，以及每个控件的时长。"),
)


def _row(*widgets: QWidget, spacing: int = 8) -> QWidget:
    """横排，末尾吃掉剩余宽度。"""

    host = QWidget()
    layout = QHBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(spacing)
    for widget in widgets:
        layout.addWidget(widget)
    layout.addStretch(1)
    return host


def _column(*widgets: QWidget, spacing: int = 8) -> QWidget:
    """竖排，宽度跟最宽的一块走。"""

    host = QWidget()
    layout = QVBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(spacing)
    for widget in widgets:
        layout.addWidget(widget)
    return host


def _section(title: str, description: str, *widgets: QWidget) -> Section:
    section = Section(title, description=description)
    for widget in widgets:
        section.add_widget(widget)
    return section


def _scroll(*widgets: QWidget) -> QScrollArea:
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(28, 8, 28, 28)
    layout.setSpacing(16)
    for widget in widgets:
        layout.addWidget(widget)
    layout.addStretch(1)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setWidget(page)
    return scroll


def _disabled(widget: QWidget) -> QWidget:
    widget.setEnabled(False)
    return widget


def _pair(title: str, text: str) -> QWidget:
    """左边短标题，右边说明。说明占满剩余宽度并换行。"""

    host = QWidget()
    layout = QHBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(12)
    name = QLabel(title)
    name.setFixedWidth(64)
    name.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
    layout.addWidget(name)
    detail = _hint(text)
    layout.addWidget(detail, stretch=1)
    return host


def _height_sample(title: str, height: int) -> QLabel:
    """用色块标出一档高度，避免透明图标按钮看不出尺寸。"""

    bar = QLabel(title)
    bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
    bar.setFixedSize(88, height)
    set_style(bar, fill="color_primary", color="color_on_primary", radius=6)
    return bar


def _hint(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("psi6Hint")
    label.setWordWrap(True)
    return label


def _labeled(widget: QWidget, text: str) -> QWidget:
    """控件下面加一行说明。"""

    host = QWidget()
    column = QVBoxLayout(host)
    column.setContentsMargins(0, 0, 0, 0)
    column.setSpacing(4)
    widget.setMinimumWidth(200)
    column.addWidget(widget)
    column.addWidget(_hint(text))
    return host


class _EaseProbe(QWidget):
    """缓动实验室里的圆点。只在样例里用，不是公开控件。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._progress = 0.0
        self.setFixedHeight(56)
        self.setMinimumWidth(360)

    def _get_progress(self) -> float:
        return self._progress

    def _set_progress(self, value: float) -> None:
        self._progress = float(value)
        self.update()

    progress = Property(float, _get_progress, _set_progress)

    def play(self, curve: str, duration: int) -> None:
        """从左走到右。``duration`` 为 0 时直接到终点。"""

        motion.animate(self, "progress", 0.0, 1.0, duration=duration, curve=curve)

    def paintEvent(self, _event) -> None:
        with create_painter(self) as painter:
            rect = QRectF(self.rect()).adjusted(8, 0, -8, 0)
            center_y = rect.center().y()
            painter.setPen(QPen(as_color(token_color("color_border_subtle")), 2))
            painter.drawLine(int(rect.left()), int(center_y), int(rect.right()), int(center_y))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(as_color(token_color("color_primary")))
            x = rect.left() + (rect.width() - 22) * self._progress
            painter.drawEllipse(QRectF(x, center_y - 11, 22, 22))


def _pager() -> QWidget:
    """12 页。超过 7 页时收成首页、末页和当前页两侧。"""

    note = _hint("第 1 / 12 页")
    pager = Pagination(12)
    pager.page_changed.connect(lambda page: note.setText(f"第 {page} / 12 页"))
    return _row(pager, note)


class Showroom(DesktopWindow):
    """样例画廊。侧栏图标与页内分组对齐 atelier 的目录。"""

    def __init__(self, app: App, parent: QWidget | None = None) -> None:
        super().__init__(title="psi6 样例", icon="spark", parent=parent)
        self._app = app
        self._loading = False
        self._toasts = ToastHost(self)
        destinations = tuple(
            NavDestination(page_id, title, icon) for page_id, title, icon, _hint in _PAGES
        )
        self.shell = AppShell(destinations, title="psi6")
        self.shell.set_brand("psi6", "Graphite & Copper", "spark")
        self._title = QLabel("概览")
        self._title.setObjectName("psi6PageTitle")
        self._hint = QLabel(_PAGES[0][3])
        self._hint.setObjectName("psi6Hint")
        self._hint.setWordWrap(True)
        header = QWidget()
        row = QHBoxLayout(header)
        row.setContentsMargins(12, 4, 12, 4)
        row.setSpacing(12)
        text = QVBoxLayout()
        text.setContentsMargins(0, 0, 0, 0)
        text.setSpacing(2)
        text.addWidget(self._title)
        text.addWidget(self._hint)
        row.addLayout(text, stretch=1)
        for label, theme in (("浅色", "light"), ("深色", ModernDark)):
            button = ghost_button(label)
            button.clicked.connect(lambda _checked=False, chosen=theme: self._app.set_theme(chosen))
            row.addWidget(button)
        row.addWidget(QLabel("动效"))
        self._motion = Switch(checked=not app.reduced_motion)
        self._motion.toggled.connect(lambda on: self._app.set_reduced_motion(not on))
        row.addWidget(self._motion)
        self.shell.set_content_header(header)
        for page_id, _title, _icon, _hint in _PAGES:
            self.shell.add_page(page_id, getattr(self, f"_page_{page_id}")())
        self.shell.page_changed.connect(self._on_page)
        self.shell.show_page("overview")
        self.setCentralWidget(self.shell)
        self.resize(1180, 780)

    def _on_page(self, page_id: str) -> None:
        for item_id, title, _icon, hint in _PAGES:
            if item_id == page_id:
                self._title.setText(title)
                self._hint.setText(hint)
                return

    def _swatches(self, pairs: tuple[tuple[str, str], ...]) -> QWidget:
        """一块色块加字段名。填充用 token 名，换主题后跟着变。"""

        host = QWidget()
        flow = FlowLayout(host, spacing=12)
        for title, field in pairs:
            cell = QWidget()
            column = QVBoxLayout(cell)
            column.setContentsMargins(0, 0, 0, 0)
            column.setSpacing(4)
            chip = QLabel()
            chip.setFixedSize(104, 40)
            set_style(chip, fill=field, radius=6)
            name = QLabel(title)
            name.setObjectName("psi6Hint")
            column.addWidget(chip)
            column.addWidget(name)
            flow.addWidget(cell)
        return host

    def _page_overview(self) -> QWidget:
        tokens = self._app.tokens
        intro = Card(elevated=True)
        title = QLabel("Graphite & Copper")
        set_style(title, size=tokens.font_size_title, weight=tokens.font_weight_title)
        intro.body.addWidget(title)
        note = QLabel(
            "暖灰负责界面，铜只用于主操作、选中和焦点。成功、警告、危险、信息跟品牌色分开。"
            "色块、圆角和时长都读当前主题。没有铜的九级色阶，强调色用主色和它推导出的悬停、按下。"
        )
        note.setWordWrap(True)
        intro.body.addWidget(note)
        intro.body.addWidget(
            _row(
                Tag("浅色主题", tone="info", checkable=False),
                Tag("令牌驱动", tone="neutral", checkable=False),
                Tag("状态分开", tone="neutral", checkable=False),
                Tag("动效可关", tone="neutral", checkable=False),
            )
        )
        display = QLabel("标题  ·  页面里最大的一档")
        set_style(display, size=tokens.font_size_title, weight=tokens.font_weight_title)
        body = QLabel("正文。桌面工具的默认字号。")
        set_style(body, size=tokens.font_size)
        caption = QLabel("辅助说明。字段下的句子、色块名字用这一档。")
        set_style(caption, size=tokens.font_size_sm, color="color_muted")
        mono = QLabel(f"{tokens.color_primary}   motion {tokens.motion_ms} ms")
        mono.setFont(QFont("Cascadia Mono", tokens.font_size_sm))
        set_style(mono, size=tokens.font_size_sm, color="color_primary")
        radii = QWidget()
        radius_row = QHBoxLayout(radii)
        radius_row.setContentsMargins(0, 0, 0, 0)
        radius_row.setSpacing(12)
        for label, value in (
            ("控件", tokens.radius),
            ("按钮", tokens.button_radius),
            ("窗口", tokens.window_radius),
        ):
            box = QLabel(f"{label}\n{value}")
            box.setAlignment(Qt.AlignmentFlag.AlignCenter)
            box.setFixedSize(88, 56)
            set_style(box, fill="color_hover", color="color_text", radius=value, padding=6)
            radius_row.addWidget(box)
        radius_row.addStretch(1)
        flat = Card()
        flat.body.addWidget(QLabel("平贴"))
        flat.body.addWidget(QLabel("只有弱边，没有投影。"))
        raised = Card(elevated=True)
        raised.body.addWidget(QLabel("浮起"))
        raised.body.addWidget(QLabel("页内唯一的轻投影。"))
        shadows = _row(flat, raised)
        shadow_layout = shadows.layout()
        assert shadow_layout is not None
        shadow_layout.setContentsMargins(4, 8, 24, 20)
        return _scroll(
            intro,
            _section(
                "色彩 · 中性",
                "画布、表面、悬停、边和文字。",
                self._swatches(
                    (
                        ("画布", "color_bg"),
                        ("表面", "color_surface"),
                        ("下沉", "color_sunken"),
                        ("悬停", "color_hover"),
                        ("边", "color_border"),
                        ("弱边", "color_border_subtle"),
                        ("正文", "color_text"),
                        ("辅助", "color_muted"),
                    )
                ),
            ),
            _section(
                "色彩 · 强调",
                "主色，以及悬停、按下、焦点和选中。不另做九级色阶。",
                self._swatches(
                    (
                        ("主色", "color_primary"),
                        ("主色上的字", "color_on_primary"),
                        ("悬停", "color_primary_hover"),
                        ("按下", "color_primary_pressed"),
                        ("焦点", "color_focus"),
                        ("选中", "color_selected"),
                    )
                ),
            ),
            _section(
                "色彩 · 语义",
                "成功、警告、危险、信息跟品牌色分开。",
                self._swatches(
                    (
                        ("成功", "color_success"),
                        ("警告", "color_warning"),
                        ("危险", "color_danger"),
                        ("信息", "color_info"),
                        ("侧栏", "color_sidebar"),
                        ("遮罩", "color_overlay"),
                    )
                ),
            ),
            _section(
                "字体",
                "标题、正文、辅助，外加一行等宽。没有 Display 档。",
                display,
                body,
                caption,
                mono,
            ),
            _section("圆角", "只有这三档，卡片不再单开一档。", radii),
            _section("阴影", "默认不投影。浮起的卡片是例外。", shadows),
            _section(
                "动效令牌",
                "只有两档。进入用减速，退出用加速，循环用线性。页头可以关掉。",
                QLabel(f"fast  {tokens.motion_fast_ms} ms    悬停、按下、开关"),
                QLabel(f"normal  {tokens.motion_ms} ms    位移、页签指示器"),
                _hint("加载圆弧转一圈是 normal 的四倍，线性循环。"),
            ),
        )

    def _page_buttons(self) -> QWidget:
        tokens = self._app.tokens
        disabled = primary_button("禁用")
        disabled.setEnabled(False)
        self._save = primary_button("提交")
        toggle = ghost_button("切换加载")
        toggle.clicked.connect(self._toggle_loading)
        plus = primary_button("新建")
        plus.setIcon(icon_for("plus", color=token_color("color_on_primary"), size=16))
        search = ghost_button("搜索")
        search.setIcon(icon_for("search", color=token_color("color_text"), size=16))
        return _scroll(
            _section(
                "变体",
                "主按钮、次按钮、危险、链接。次按钮是描边，没有单独的 outline。",
                _row(
                    primary_button("主要操作"),
                    ghost_button("次要操作"),
                    danger_button("危险操作"),
                    text_button("链接"),
                ),
                _row(
                    _disabled(primary_button("主要")),
                    _disabled(ghost_button("次要")),
                    _disabled(danger_button("危险")),
                    _disabled(text_button("链接")),
                ),
            ),
            _section(
                "尺寸",
                "文字按钮只有 control_height 一档。图标按钮用热区区分小、中、大。",
                _row(
                    _height_sample(f"小 {tokens.control_height_sm}", tokens.control_height_sm),
                    _height_sample(f"中 {tokens.control_height}", tokens.control_height),
                    _height_sample(f"大 {tokens.control_height + 8}", tokens.control_height + 8),
                ),
                _row(
                    IconButton("plus", label="小", extent=tokens.control_height_sm),
                    IconButton("plus", label="中", extent=tokens.control_height),
                    IconButton("plus", label="大", extent=tokens.control_height + 8),
                ),
            ),
            _section(
                "状态",
                "默认、禁用、加载。加载时颜色不变，点击、空格和回车被挡住。",
                _row(primary_button("默认"), disabled, self._save, toggle),
                _hint("悬停改填充，按下再深一档。焦点环默认不画，需要时在应用上打开。"),
            ),
            _section(
                "图标按钮",
                "纯图标，以及图标加文字。",
                _row(
                    IconButton("plus", label="新建"),
                    IconButton("search", label="搜索"),
                    IconButton("settings", label="设置"),
                    IconButton("copy", label="复制"),
                    IconButton("bell", label="通知"),
                    plus,
                    search,
                ),
            ),
            _section(
                "标签与徽标",
                "Tag 是可点的胶囊。StatusBadge 是计数或行状态。",
                _row(
                    Tag("默认", tone="neutral", checkable=False),
                    Tag("信息", tone="info", checkable=False),
                    Tag("成功", tone="success", checkable=False),
                    Tag("警告", tone="warning", checkable=False),
                    Tag("错误", tone="error", checkable=False),
                ),
                _row(
                    StatusBadge("3", tone="error"),
                    StatusBadge("12", tone="info"),
                    StatusBadge("就绪", tone="success"),
                    StatusBadge("等待", tone="warning"),
                ),
            ),
        )

    def _toggle_loading(self) -> None:
        self._loading = not self._loading
        set_loading(self._save, self._loading)

    def _page_inputs(self) -> QWidget:
        plain = QLineEdit()
        plain.setPlaceholderText("项目名称")
        invalid = QLineEdit("invalid@")
        invalid.setProperty("invalid", True)
        readonly = QLineEdit("只读内容")
        readonly.setReadOnly(True)
        locked = QLineEdit("禁用输入")
        locked.setEnabled(False)
        area = QPlainTextEdit()
        area.setPlaceholderText("多行文本")
        area.setFixedHeight(88)
        combo = QComboBox()
        combo.addItems(["石墨灰", "暖铜色", "语义绿", "语义红"])
        spin = QSpinBox()
        spin.setRange(0, 100)
        spin.setValue(24)
        decimal = QDoubleSpinBox()
        decimal.setRange(0, 1)
        decimal.setSingleStep(0.1)
        decimal.setValue(0.6)
        date = QDateEdit()
        date.setCalendarPopup(True)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 100)
        slider.setValue(60)
        slider.setMinimumWidth(320)
        checked = QCheckBox("启用自动保存")
        checked.setChecked(True)
        off = QCheckBox("显示网格")
        disabled = QCheckBox("禁用项")
        disabled.setEnabled(False)
        left = QRadioButton("左对齐")
        left.setChecked(True)
        center = QRadioButton("居中")
        right = QRadioButton("右对齐")
        group = QButtonGroup(left)
        group.addButton(left)
        group.addButton(center)
        group.addButton(right)
        switch = Switch(checked=True)
        switch_note = QLabel("动效已开启")
        switch.toggled.connect(lambda on: switch_note.setText("动效已开启" if on else "动效已关闭"))
        return _scroll(
            _section(
                "文本输入",
                "默认、错误、只读、禁用，以及多行。",
                _row(_labeled(plain, "默认"), _labeled(invalid, "错误")),
                _row(_labeled(readonly, "只读"), _labeled(locked, "禁用")),
                area,
            ),
            _section(
                "选择输入",
                "搜索、下拉、整数、小数和日期。",
                SearchField(),
                _row(
                    _labeled(combo, "下拉"),
                    _labeled(spin, "整数"),
                    _labeled(decimal, "小数"),
                    _labeled(date, "日期"),
                ),
            ),
            _section(
                "勾选 · 单选 · 开关 · 滑块",
                "选中的单选是同色的外环和圆心，中间留白。焦点环默认不画。",
                _row(checked, off, disabled),
                _row(left, center, right),
                _row(switch, switch_note),
                slider,
            ),
        )

    def _page_data(self) -> QWidget:
        table = DataTable(
            (
                TableColumn("name", "任务", stretch=True),
                TableColumn("owner", "负责人"),
                TableColumn("state", "状态"),
                TableColumn("priority", "优先级"),
            )
        )
        table.set_rows(
            (
                {"name": "设计令牌梳理", "owner": "林悦", "state": "进行中", "priority": "高"},
                {"name": "按钮加载状态", "owner": "陈默", "state": "已完成", "priority": "高"},
                {"name": "单选同色环", "owner": "周宁", "state": "待确认", "priority": "中"},
                {"name": "侧栏选中条", "owner": "林悦", "state": "进行中", "priority": "中"},
                {"name": "焦点环默认", "owner": "赵一", "state": "已关闭", "priority": "低"},
            )
        )
        table.setMinimumHeight(240)
        files = TreeNode(id="ui", data={"name": "ui", "kind": "目录"})
        files.children = [
            TreeNode(id="buttons", data={"name": "buttons.py", "kind": "文件"}, has_children=False),
            TreeNode(id="chrome", data={"name": "chrome.py", "kind": "文件"}, has_children=False),
            TreeNode(id="toast", data={"name": "toast.py", "kind": "文件"}, has_children=False),
        ]
        theme = TreeNode(id="theme", data={"name": "theme", "kind": "目录"})
        theme.children = [
            TreeNode(id="tokens", data={"name": "tokens.py", "kind": "文件"}, has_children=False),
            TreeNode(id="apply", data={"name": "apply.py", "kind": "文件"}, has_children=False),
            TreeNode(id="builtin", data={"name": "builtin.py", "kind": "文件"}, has_children=False),
        ]
        docs = TreeNode(id="docs", data={"name": "docs", "kind": "目录"})
        docs.children = [
            TreeNode(
                id="visual",
                data={"name": "01-visual-language.md", "kind": "文件"},
                has_children=False,
            ),
            TreeNode(
                id="spec",
                data={"name": "04-component-visual-spec.md", "kind": "文件"},
                has_children=False,
            ),
        ]
        root = TreeNode(id="psi6", data={"name": "psi6", "kind": "目录"})
        root.children = [files, theme, docs]
        tree = TreeView((TreeColumn("name", "名称", stretch=True), TreeColumn("kind", "类型")))
        tree.set_nodes([root])
        tree.expand_all()
        tree.setMinimumHeight(220)
        recent = QListWidget()
        recent.addItems(("设计稿.fig", "组件规范.md", "令牌清单.csv", "窗口截图.png"))
        recent.setFixedHeight(140)
        empty = DataTable((TableColumn("name", "名称", stretch=True),))
        empty.setMinimumHeight(140)
        return _scroll(
            _section("表格", "表内是白色表面。拖动表头边缘可以改列宽。", table),
            _section("树形视图", "展开箭头是主题图形。", tree),
            _section(
                "列表与分页",
                "列表走主题选中色。超过 7 页时页码收成首页、末页和当前页两侧。",
                recent,
                _pager(),
            ),
            _section("空表", "没有行时只显示空状态。", empty),
        )

    def _page_nav(self) -> QWidget:
        tabs = UnderlineTabs()
        tabs.add_tab("概览", QLabel("这是概览。底下的主色条会滑过来。"))
        tabs.add_tab("成员", QLabel("这是成员。再点回去，条跟着回去。"))
        tabs.add_tab("设置", QLabel("这是设置。减少动效时条直接跳过去。"))
        tabs.setMinimumHeight(140)
        crumbs = Breadcrumb()
        crumbs.set_crumbs(["工作台", "组件库", "导航", "页签"])
        mini = Sidebar(
            (
                NavDestination("home", "概览", "home"),
                NavDestination("buttons", "按钮", "grid"),
                NavDestination("inputs", "输入", "sliders"),
                NavDestination("data", "数据", "layers"),
                NavDestination("feedback", "反馈", "bell"),
            ),
            title="目录",
        )
        mini.set_brand("目录", "选中有主色竖条", "menu")
        mini.select("home")
        mini.setFixedHeight(440)
        menu_button = ghost_button("打开菜单")
        menu_button.setIcon(icon_for("menu", color=token_color("color_text"), size=16))
        menu = QMenu(menu_button)
        menu.addAction("新建项目")
        menu.addAction("导入文件")
        menu.addSeparator()
        preferred = menu.addAction("偏好设置")
        preferred.setCheckable(True)
        preferred.setChecked(True)
        menu.addAction("删除项目")
        menu_button.clicked.connect(
            lambda: menu.exec(menu_button.mapToGlobal(menu_button.rect().bottomLeft()))
        )
        steps = Stepper(("准备", "编辑", "完成"))
        steps.set_current(1)
        accent = Switch(checked=self.shell.nav_accent())
        accent.toggled.connect(self.shell.set_nav_accent)
        accent.toggled.connect(mini.set_nav_accent)
        return _scroll(
            _section("标签页", "活动指示器滑动，不推动文字。", tabs),
            _section("面包屑", "只表示当前位置。", crumbs),
            _section("侧栏导航", "和窗口左侧是同一套。选中是填充加主色竖条。", mini),
            _section("菜单", "勾选标记是主题图形。", menu_button),
            _section(
                "分段与步骤",
                "分段是互斥项。步骤条标出当前步。",
                SegmentedControl(("列表", "网格")),
                steps,
            ),
            _section(
                "侧栏选中条",
                "左侧竖条是 color_primary，跟主题走。关掉后只留选中填充，文字不位移。",
                _row(QLabel("显示竖条"), accent),
            ),
        )

    def _page_feedback(self) -> QWidget:
        notices = (
            ("这条是说明。", "info"),
            ("已经保存。", "success"),
            ("还有一项没填。", "warning"),
            ("写不进去。", "error"),
        )
        banners = [Banner() for _text, _tone in notices]
        page_bits = _section("横幅", "四种语气。字段错误仍写在字段下。", *banners)
        for banner, (text, tone) in zip(banners, notices, strict=True):
            banner.set_notice(text, tone=tone)
        toasts = (
            ("成功", "success", "保存成功，已写进本地。"),
            ("警告", "warning", "磁盘空间不足，请及时清理。"),
            ("错误", "error", "写不进去，请重试。"),
            ("信息", "info", "有 3 个组件待看。"),
        )
        toast_buttons = []
        for title, tone, message in toasts:
            if tone == "success":
                button = primary_button(title)
            elif tone == "error":
                button = danger_button(title)
            else:
                button = ghost_button(title)
            button.clicked.connect(
                lambda _checked=False, text=message, kind=tone: self._toasts.push(text, tone=kind)
            )
            toast_buttons.append(button)
        busy_host = Card()
        busy_host.body.addWidget(QLabel("这块会被盖住。"))
        busy_host.body.addWidget(_hint("不确定进度走 BusyOverlay。"))
        busy_host.setMinimumHeight(120)
        overlay = BusyOverlay(busy_host)
        busy_toggle = ghost_button("切换忙碌层")

        def _toggle_busy() -> None:
            if overlay.is_busy():
                overlay.hide_busy()
            else:
                overlay.show_busy("正在处理…")

        busy_toggle.clicked.connect(_toggle_busy)
        determinate = QProgressBar()
        determinate.setRange(0, 100)
        determinate.setValue(64)
        determinate.setFixedWidth(320)
        busy = BusyBar()
        busy.setFixedWidth(320)
        skeleton = Card()
        title_lines = _column(Skeleton(160, 14), Skeleton(120, 12), spacing=10)
        skeleton.body.addWidget(_row(Skeleton(40, 40, radius=20), title_lines, spacing=12))
        skeleton.body.addWidget(Skeleton(280, 12))
        skeleton.body.addWidget(Skeleton(240, 12))
        empty = EmptyState(
            "暂无项目",
            "创建第一条记录，或换一个筛选。",
            action_text="新建项目",
            icon="inbox",
        )
        empty.setMinimumHeight(200)
        empty.setMaximumHeight(240)
        empty.action_clicked.connect(lambda: self._toasts.push("已创建新项目。", tone="success"))
        return _scroll(
            _section(
                "Toast 通知",
                "右下角堆叠。左侧图标跟语气走。悬停暂停，移开后按剩余时间继续。",
                _row(*toast_buttons),
            ),
            _section(
                "加载",
                "旋转环和来回滑的轨道。还不知道总量时用它们，不用进度条。",
                _row(Spinner(18), Spinner(24), Spinner(32), _hint("加载中")),
                busy,
                busy_host,
                busy_toggle,
            ),
            _section("进度", "已经知道完成了多少，才用进度条。", determinate),
            _section(
                "骨架屏",
                "圆头像、两行标题、两条长短不一的正文。高光是半宽渐变，离开页面就停。",
                skeleton,
            ),
            page_bits,
            _section(
                "徽标",
                "短状态，不拿来做对话框。",
                _row(
                    StatusBadge("成功", tone="success"),
                    StatusBadge("警告", tone="warning"),
                    StatusBadge("错误", tone="error"),
                    StatusBadge("信息", tone="info"),
                ),
            ),
            _section("空状态", "图标、标题、说明和一步操作。", empty),
        )

    def _page_containers(self) -> QWidget:
        panel = Panel()
        panel.body.addWidget(QLabel("Panel"))
        panel.body.addWidget(QLabel("平面分区，边用 color_border，没有投影。"))
        flat = Card()
        flat.body.addWidget(QLabel("Card"))
        flat.body.addWidget(QLabel("弱边，圆角跟控件同一档。"))
        raised = Card(elevated=True)
        raised.body.addWidget(QLabel("Card elevated"))
        raised.body.addWidget(QLabel("需要浮起时才加投影。"))
        tokens = Collapsible("什么是设计令牌？", expanded=True)
        tokens.add_widget(_hint("颜色、字号、间距、圆角和时长。控件只引用令牌，不把数值写死。"))
        motion_fold = Collapsible("如何关闭动效？")
        motion_fold.add_widget(_hint("页头的动效开关关掉后，滑动和转圈直接到终点，功能不变。"))
        drawer = Drawer("组件详情", self)
        drawer.body().addWidget(QLabel("按钮 · 加载"))
        drawer.body().addWidget(_hint("按钮保留变体颜色。加载时挡住点击，不变成灰色。"))
        drawer.body().addWidget(Tag("样例", tone="info", checkable=False))
        drawer.body().addStretch(1)
        drawer_button = primary_button("打开抽屉")
        drawer_button.clicked.connect(drawer.open)
        dialog_button = ghost_button("打开对话框")
        dialog_button.clicked.connect(self._open_dialog)
        confirm_button = danger_button("确认删除")
        confirm_button.clicked.connect(
            lambda: confirm(self, "删除项目", "删除后不能恢复。要继续吗？")
        )
        return _scroll(
            _section("分区", "设置页用它，不用卡片墙。", panel),
            _section(
                "卡片", "平贴是默认。浮起才有一层轻投影。没有第三档阴影。", _row(flat, raised)
            ),
            _section("折叠", "标题行可聚焦。展开只显示下面这一块。", tokens, motion_fold),
            _section("抽屉", "从右侧盖住窗口。点遮罩或按 Esc 关闭。", drawer_button),
            _section(
                "对话框", "带主体的对话框，以及一句确认。", _row(dialog_button, confirm_button)
            ),
        )

    def _open_dialog(self) -> None:
        body = QWidget()
        column = QVBoxLayout(body)
        column.setContentsMargins(0, 0, 0, 0)
        column.addWidget(QLabel("项目名称"))
        name = QLineEdit()
        name.setPlaceholderText("输入项目名称")
        column.addWidget(name)
        column.addWidget(_hint("创建后仍留在这一页。"))
        ContentDialog("新建项目", body, primary="创建", secondary="取消", parent=self).run()

    def _page_motion(self) -> QWidget:
        tokens = self._app.tokens
        probe = _EaseProbe()
        curves = QComboBox()
        curve_names = {
            "进入 · OutCubic": "enter",
            "退出 · InCubic": "exit",
            "强调 · OutQuint": "emphasized",
            "展开 · InOutCubic": "in_out",
            "线性": "linear",
        }
        curves.addItems(tuple(curve_names))
        durations = QComboBox()
        duration_ms = {
            f"fast · {tokens.motion_fast_ms} ms": tokens.motion_fast_ms,
            f"normal · {tokens.motion_ms} ms": tokens.motion_ms,
            "演示 · 400 ms": 400,
        }
        durations.addItems(tuple(duration_ms))
        durations.setCurrentIndex(1)
        play = primary_button("播放")
        play.setIcon(icon_for("play", color=token_color("color_on_primary"), size=16))
        play.clicked.connect(
            lambda: probe.play(
                curve_names[curves.currentText()],
                duration_ms[durations.currentText()],
            )
        )
        tabs = UnderlineTabs()
        tabs.add_tab("快", QLabel("切页签看指示器。"))
        tabs.add_tab("慢", QLabel("减少动效时它直接跳过去。"))
        tabs.setMinimumHeight(110)
        spin = primary_button("加载")
        spin_toggle = ghost_button("开始转圈")
        spinning = {"on": False}

        def _toggle() -> None:
            spinning["on"] = not spinning["on"]
            set_loading(spin, spinning["on"])

        spin_toggle.clicked.connect(_toggle)
        notes = (
            ("按钮", "悬停改填充。加载圆弧一圈是 normal 的四倍，线性循环。"),
            ("开关", "圆钮用 normal 滑过去。减少动效时直接到位。"),
            ("页签", "底边的位置和宽度用 normal 滑动。"),
            ("抽屉", "从右侧滑入用 normal，退出用加速。点遮罩或 Esc 关闭。"),
            ("Toast", "高度进出场。悬停暂停，移开后续上剩余时间。"),
            ("骨架", "扫光一圈是 normal 的五倍，线性循环，离开页面就停。"),
        )
        return _scroll(
            _section(
                "动效原则",
                "只做颜色、透明度和位移。页头开关关掉后全部直接到终点。",
                _hint("进入用减速，退出用加速，循环用线性。"),
                _hint("控件不写死毫秒，时长只从 fast 和 normal 取。"),
                _hint("按下不另做回弹。焦点环默认关闭。"),
            ),
            _section(
                "缓动实验室",
                "选一条曲线和一段时长，看圆点怎么走。",
                _row(curves, durations, play),
                probe,
            ),
            _section(
                "组件动画清单",
                f"fast {tokens.motion_fast_ms} ms，normal {tokens.motion_ms} ms。",
                *[_pair(name, desc) for name, desc in notes],
            ),
            _section(
                "可以动手试",
                "页签指示器和加载圆弧都听页头的动效开关。",
                tabs,
                _row(spin, spin_toggle),
            ),
        )


def main() -> None:
    """打开样例。默认浅色（石墨铜），焦点环关着。"""

    app = App("psi6-showroom", theme="light")
    raise SystemExit(app.run(Showroom(app), restore_geometry=True))
