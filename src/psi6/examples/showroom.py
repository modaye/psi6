"""样例工作台。

侧栏换页，页内按令牌、按钮、输入、数据、导航、反馈、容器、动效展开。
默认石墨铜，焦点环默认关着。状态矩阵仍在 ``python -m psi6 kit --workbench``。
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QRadioButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from psi6 import App
from psi6.icons.render import icon_for
from psi6.theme.builtin import Graphite, ModernDark
from psi6.theme.runtime import token_color
from psi6.ui.app_shell import AppShell, NavDestination
from psi6.ui.banner import Banner
from psi6.ui.buttons import danger_button, ghost_button, primary_button, set_loading, text_button
from psi6.ui.chrome import Card, Panel
from psi6.ui.collapsible import Collapsible
from psi6.ui.data_table import DataTable, TableColumn
from psi6.ui.desktop_window import DesktopWindow
from psi6.ui.empty_state import EmptyState
from psi6.ui.flow_layout import FlowLayout
from psi6.ui.icon import IconButton
from psi6.ui.search_field import SearchField
from psi6.ui.section import Section
from psi6.ui.segmented import SegmentedControl
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
    ("overview", "概览", "home", "当前主题的色、字、圆角、阴影和动效。"),
    ("buttons", "按钮", "grid", "变体、尺寸、状态、图标按钮、标签和徽标。"),
    ("inputs", "输入", "sliders", "文本、选择、勾选、单选、开关和滑块。"),
    ("data", "数据", "layers", "表格、空表和树。"),
    ("nav", "导航", "menu", "页签、面包屑、分段、步骤，以及侧栏选中条。"),
    ("feedback", "反馈", "bell", "横幅、徽标、空状态和 Toast。"),
    ("containers", "容器", "copy", "平面分区、平贴卡片、浮起卡片和折叠。"),
    ("motion", "动效", "spark", "时长令牌。页头开关关掉后，滑动和转圈直接到位。"),
)


def _row(*widgets: QWidget) -> QWidget:
    """横排，末尾吃掉剩余宽度。"""

    host = QWidget()
    layout = QHBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    for widget in widgets:
        layout.addWidget(widget)
    layout.addStretch(1)
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
        for label, theme in (("石墨", Graphite), ("浅色", "light"), ("深色", ModernDark)):
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
            "下面的色块、圆角和时长都读当前主题，不另写一套。"
        )
        note.setWordWrap(True)
        intro.body.addWidget(note)
        display = QLabel("标题")
        set_style(display, size=tokens.font_size_title, weight=tokens.font_weight_title)
        body = QLabel("正文。桌面工具的默认字号。")
        set_style(body, size=tokens.font_size)
        caption = QLabel("辅助说明。")
        set_style(caption, size=tokens.font_size_sm, color="color_muted")
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
                "色彩 · 强调与语义",
                "铜是主色。语义色不跟它混。",
                self._swatches(
                    (
                        ("主色", "color_primary"),
                        ("焦点", "color_focus"),
                        ("成功", "color_success"),
                        ("警告", "color_warning"),
                        ("危险", "color_danger"),
                        ("信息", "color_info"),
                    )
                ),
            ),
            _section("字体", "标题、正文、辅助。", display, body, caption),
            _section("圆角", "只有这三档，卡片不再单开一档。", radii),
            _section("阴影", "默认不投影。浮起的卡片是例外。", shadows),
            _section(
                "动效令牌",
                "进入用减速。加载圆弧转一圈是 normal 的四倍。",
                QLabel(f"fast  {tokens.motion_fast_ms} ms"),
                QLabel(f"normal  {tokens.motion_ms} ms"),
            ),
        )

    def _page_buttons(self) -> QWidget:
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
                "主按钮、次按钮、危险、文字、链接。",
                _row(
                    primary_button("主要操作"),
                    ghost_button("次要操作"),
                    danger_button("危险操作"),
                    text_button("链接"),
                ),
            ),
            _section(
                "尺寸",
                "文字按钮跟 control_height。图标按钮用 extent 取三档热区。",
                _row(
                    IconButton("plus", label="小", extent=28),
                    IconButton("plus", label="中", extent=36),
                    IconButton("plus", label="大", extent=44),
                ),
            ),
            _section(
                "状态",
                "默认、禁用、加载。加载时颜色不变，点击被挡住。",
                _row(primary_button("默认"), disabled, self._save, toggle),
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
        combo.addItems(["石墨", "铜", "成功", "危险"])
        spin = QSpinBox()
        spin.setRange(0, 100)
        spin.setValue(24)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 100)
        slider.setValue(60)
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
        return _scroll(
            _section(
                "文本",
                "默认、错误、只读、禁用，以及多行。",
                _row(plain, invalid),
                _row(readonly, locked),
                area,
            ),
            _section("选择", "搜索、下拉、步进、滑块。", SearchField(), _row(combo, spin), slider),
            _section(
                "勾选 · 单选 · 开关",
                "选中的单选是同色的外环和圆心，中间留白。焦点环默认不画。",
                _row(checked, off, disabled),
                _row(left, center, right),
                Switch(checked=True),
            ),
        )

    def _page_data(self) -> QWidget:
        table = DataTable(
            (
                TableColumn("name", "任务", stretch=True),
                TableColumn("owner", "负责人"),
                TableColumn("state", "状态"),
            )
        )
        table.set_rows(
            (
                {"name": "设计令牌", "owner": "林悦", "state": "进行中"},
                {"name": "按钮状态", "owner": "陈默", "state": "已完成"},
                {"name": "单选样式", "owner": "周宁", "state": "待确认"},
            )
        )
        table.setMinimumHeight(180)
        empty = DataTable((TableColumn("name", "名称", stretch=True),))
        empty.setMinimumHeight(140)
        root = TreeNode(id="src", data={"name": "src", "kind": "目录"})
        root.children = [
            TreeNode(id="app", data={"name": "app.py", "kind": "文件"}, has_children=False),
            TreeNode(id="theme", data={"name": "theme.py", "kind": "文件"}, has_children=False),
        ]
        tree = TreeView((TreeColumn("name", "名称", stretch=True), TreeColumn("kind", "类型")))
        tree.set_nodes([root])
        tree.setMinimumHeight(160)
        return _scroll(
            _section("表格", "行悬停和选中走主题色。", table),
            _section("空表", "没有行时只显示空状态。", empty),
            _section("树", "展开箭头是主题图形。", tree),
        )

    def _page_nav(self) -> QWidget:
        tabs = UnderlineTabs()
        tabs.add_tab("概览", QLabel("底下的主色条会滑到这一项。"))
        tabs.add_tab("明细", QLabel("再点回去，条跟着回去。"))
        tabs.setMinimumHeight(120)
        crumbs = Breadcrumb()
        crumbs.set_crumbs(["样例", "导航", "页签"])
        steps = Stepper(("准备", "编辑", "完成"))
        steps.set_current(1)
        accent = Switch(checked=self.shell.nav_accent())
        accent.toggled.connect(self.shell.set_nav_accent)
        return _scroll(
            _section("页签", "活动指示器滑动，不推动文字。", tabs),
            _section("面包屑", "只表示当前位置。", crumbs),
            _section("分段与步骤", "分段是互斥项。步骤条标出当前步。", SegmentedControl(("列表", "网格")), steps),
            _section(
                "侧栏选中条",
                "左侧竖条是 color_primary，跟主题走。关掉后只留选中填充。",
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
        empty = EmptyState("没有记录", "换一个筛选，或新建一条。", icon="inbox")
        empty.setMinimumHeight(180)
        empty.setMaximumHeight(220)
        toast = primary_button("弹出 Toast")
        toast.clicked.connect(lambda: self._toasts.push("已放进右下角。", tone="success"))
        return _scroll(
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
            _section("空状态", "只在宿主里面居中。", empty),
            _section("Toast", "出现在窗口右下角，悬停会暂停。", toast),
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
        folded = Collapsible("不常用", expanded=False)
        folded.add_widget(QLabel("展开只改这一块的高度。"))
        return _scroll(
            _section("分区", "设置页用它，不用卡片墙。", panel),
            _section("卡片", "平贴是默认。浮起是显式打开的。", _row(flat, raised)),
            _section("折叠", "标题行可聚焦。", folded),
        )

    def _page_motion(self) -> QWidget:
        tokens = self._app.tokens
        probe = UnderlineTabs()
        probe.add_tab("快", QLabel("切页签看指示器。"))
        probe.add_tab("慢", QLabel("减少动效时它直接跳过去。"))
        probe.setMinimumHeight(100)
        spin = primary_button("加载")
        spin_toggle = ghost_button("开始转圈")

        spinning = {"on": False}

        def _toggle() -> None:
            spinning["on"] = not spinning["on"]
            set_loading(spin, spinning["on"])

        spin_toggle.clicked.connect(_toggle)
        return _scroll(
            _section(
                "时长",
                "控件不写毫秒。fast 给悬停和开关，normal 给位移。",
                QLabel(f"motion_fast_ms = {tokens.motion_fast_ms}"),
                QLabel(f"motion_ms = {tokens.motion_ms}"),
                QLabel("加载圆弧一圈 = motion_ms × 4，线性循环。"),
            ),
            _section("指示器", "页头的动效开关关掉后，这条直接到位。", probe),
            _section("加载", "减少动效时圆弧停住，仍然挡住点击。", _row(spin, spin_toggle)),
        )


def main() -> None:
    """打开样例。默认石墨铜，焦点环关着。"""

    app = App("psi6-showroom", theme="graphite")
    raise SystemExit(app.run(Showroom(app), restore_geometry=True))
