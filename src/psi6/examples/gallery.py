"""示例画廊：像 web UI 一样列出用例，点开即看 psi6 的组件与组合。

``python -m psi6 gallery`` 打开一个首屏，按「入门 / 数据与任务 / 组件 / 场景」
分组列出可点击的用例卡片。点击卡片会复用同一个 ``App`` 打开对应窗口——
主题切换时所有已开的窗口一起换肤。``custom_theme`` 因为是演示自定义主题本身，
单独起一个进程，好让它的绿色主题不被画廊主题盖掉。

新增的三个「场景」用例（数据看板 / 偏好设置 / 即时对话）也都是 ``build(app)``
返回 ``DesktopWindow`` 的函数，show 出来即可，方便在画廊里直接体验组件组合。
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import QEvent, Qt, QTimer, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from psi6 import App, DesktopWindow
from psi6.examples import file_index, minimal, task_job, task_status
from psi6.examples.kit import KitWindow
from psi6.theme.builtin import Compact
from psi6.ui.banner import Banner
from psi6.ui.chat import Composer, MessageList
from psi6.ui.chrome import PageHeader, StatCard
from psi6.ui.data_table import DataTable, TableColumn
from psi6.ui.flow_layout import FlowLayout
from psi6.ui.icon import Icon
from psi6.ui.segmented import SegmentedControl
from psi6.ui.settings_page import SettingsPage
from psi6.ui.tag import TagRow


@dataclass
class UseCase:
    """画廊里一张卡片的元数据。``launcher`` 收 ``App``，返回要 show 的窗口或 None。"""

    id: str
    title: str
    description: str
    icon: str
    category: str
    tags: tuple[str, ...]
    launcher: Callable[[App], QWidget | None]


class _BrandTile(QWidget):
    """实心主色方块里放一个反色图标，主题切换时图标自动跟上。"""

    def __init__(self, icon_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("psi6GalleryBrand")
        # 纯 QWidget 画 QSS 背景必须显式开 WA_StyledBackground，否则主色方块不落色
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedSize(44, 44)
        self._icon = Icon(icon_name, size=22)
        self._icon.setFixedSize(22, 22)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self._icon, alignment=Qt.AlignmentFlag.AlignCenter)
        self._sync()

    def _sync(self) -> None:
        app = QApplication.instance()
        color = app.property("psi6ColorOnPrimary") if app is not None else None
        if isinstance(color, str) and color:
            self._icon.setProperty("psi6IconColor", color)

    def changeEvent(self, event: QEvent) -> None:
        if event.type() in {QEvent.Type.PaletteChange, QEvent.Type.StyleChange}:
            self._sync()
        super().changeEvent(event)


class UseCaseCard(QWidget):
    """一张可点击的用例卡片。鼠标按下即触发 ``activated``。"""

    activated = Signal()

    def __init__(self, case: UseCase, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("psi6Tile")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedWidth(300)
        self._case = case

        row = QHBoxLayout(self)
        row.setContentsMargins(16, 16, 16, 16)
        row.setSpacing(14)

        icon = Icon(case.icon, size=26, tone="info")
        icon.setFixedSize(26, 26)
        row.addWidget(icon, alignment=Qt.AlignmentFlag.AlignTop)

        column = QVBoxLayout()
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(6)

        title = QLabel(case.title)
        title.setObjectName("psi6TileTitle")
        column.addWidget(title)

        desc = QLabel(case.description)
        desc.setObjectName("psi6TileDesc")
        desc.setWordWrap(True)
        column.addWidget(desc)

        if case.tags:
            tag_row = QHBoxLayout()
            tag_row.setContentsMargins(0, 2, 0, 0)
            tag_row.setSpacing(6)
            for tag in case.tags:
                label = QLabel(tag)
                label.setObjectName("psi6TileTag")
                tag_row.addWidget(label)
            tag_row.addStretch()
            column.addLayout(tag_row)

        row.addLayout(column, stretch=1)

        arrow = QLabel("›")
        arrow.setObjectName("psi6TileArrow")
        row.addWidget(arrow, alignment=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.activated.emit()
        super().mousePressEvent(event)


def build_dashboard(app: App) -> DesktopWindow:
    """数据看板：统计卡 + 迷你折线 + 表格 + 分段切换，演示组件组合。"""

    window = DesktopWindow(title="数据看板")
    window.resize(900, 640)

    header = PageHeader(
        "数据看板",
        hint="统计卡 + 迷你折线 + 表格 + 分段切换。切换时段时数据一起换。",
        icon="layout-dashboard",
    )

    periods: dict[str, dict[str, Any]] = {
        "今日": {
            "stats": ("1,284", "99.2%", "3.2s", "5"),
            "spark": (
                (3, 5, 4, 6, 7, 6, 8, 7, 9),
                (98, 99, 97, 99, 98, 99, 99, 100, 99),
                (4, 3, 5, 3, 2, 4, 3, 3, 2),
                (6, 5, 7, 4, 5, 6, 5, 5, 5),
            ),
            "rows": [
                {"name": "索引 logs", "kind": "索引", "status": "成功", "duration": "2.1s"},
                {"name": "导出报告", "kind": "导出", "status": "成功", "duration": "4.6s"},
                {"name": "同步配置", "kind": "同步", "status": "运行中", "duration": "—"},
                {"name": "清理缓存", "kind": "清理", "status": "失败", "duration": "0.4s"},
            ],
        },
        "本周": {
            "stats": ("8,902", "98.7%", "3.6s", "12"),
            "spark": (
                (6, 7, 5, 8, 9, 7, 10, 8, 11),
                (97, 98, 96, 99, 98, 97, 99, 98, 97),
                (5, 4, 6, 4, 3, 5, 4, 4, 3),
                (9, 8, 11, 7, 9, 10, 8, 9, 9),
            ),
            "rows": [
                {"name": "索引 logs", "kind": "索引", "status": "成功", "duration": "2.0s"},
                {"name": "导出报告", "kind": "导出", "status": "成功", "duration": "4.2s"},
                {"name": "批量重命名", "kind": "索引", "status": "成功", "duration": "6.8s"},
                {"name": "镜像同步", "kind": "同步", "status": "失败", "duration": "1.1s"},
                {"name": "增量备份", "kind": "清理", "status": "运行中", "duration": "—"},
            ],
        },
        "本月": {
            "stats": ("37,415", "97.9%", "4.1s", "28"),
            "spark": (
                (9, 11, 10, 13, 12, 14, 13, 15, 16),
                (96, 97, 95, 98, 97, 96, 98, 97, 96),
                (6, 5, 7, 5, 4, 6, 5, 5, 4),
                (14, 12, 16, 11, 14, 15, 13, 14, 14),
            ),
            "rows": [
                {"name": "全量索引", "kind": "索引", "status": "成功", "duration": "38.4s"},
                {"name": "月度导出", "kind": "导出", "status": "成功", "duration": "12.7s"},
                {"name": "合规扫描", "kind": "同步", "status": "成功", "duration": "9.3s"},
                {"name": "归档旧数据", "kind": "清理", "status": "失败", "duration": "3.2s"},
                {"name": "镜像同步", "kind": "同步", "status": "运行中", "duration": "—"},
                {"name": "用户反馈", "kind": "导出", "status": "成功", "duration": "1.9s"},
            ],
        },
    }

    stat_cards = [
        StatCard("今日索引", "1,284", icon="table"),
        StatCard("成功率", "99.2%", icon="check"),
        StatCard("平均耗时", "3.2s", icon="clock"),
        StatCard("队列中", "5", icon="list"),
    ]
    stat_row = QHBoxLayout()
    stat_row.setSpacing(12)
    for card in stat_cards:
        stat_row.addWidget(card)

    segment = SegmentedControl(("今日", "本周", "本月"))
    tags = TagRow()

    table = DataTable(
        (
            TableColumn("name", "任务", stretch=True),
            TableColumn("kind", "类型"),
            TableColumn("status", "状态"),
            TableColumn("duration", "耗时"),
        )
    )

    banner = Banner()

    def apply_period(period: str) -> None:
        data = periods[period]
        for card, value, spark in zip(stat_cards, data["stats"], data["spark"], strict=True):
            card.set_value(value)
            card.set_sparkline(spark)
        table.set_filter("")
        tags.set_checked("")
        table.set_rows(data["rows"])

    def on_tag(label: str) -> None:
        table.set_filter("" if label in {"", "全部"} else label)

    segment.changed.connect(lambda index: apply_period(("今日", "本周", "本月")[index]))
    tags.tag_selected.connect(on_tag)
    apply_period("今日")

    body = QWidget()
    layout = QVBoxLayout(body)
    layout.setContentsMargins(20, 16, 20, 16)
    layout.setSpacing(12)
    layout.addWidget(header)
    layout.addWidget(banner)
    layout.addLayout(stat_row)
    layout.addWidget(segment)
    layout.addWidget(tags)
    layout.addWidget(table, stretch=1)
    banner.set_notice(
        "数据每 30 秒自动刷新；下面是本月样本。",
        tone="info",
        actions=(("立即刷新", lambda: app.notifier.success("已刷新数据")),),
    )
    tags.set_labels(("全部", "成功", "失败", "运行中"))
    window.set_body(body)
    return window


def build_settings(app: App) -> DesktopWindow:
    """偏好设置：pydantic 模型直接生成设置页。"""

    from pydantic import BaseModel, Field

    class Prefs(BaseModel):
        theme: str = Field(
            default="浅色", description="界面主题", json_schema_extra={"group": "外观"}
        )
        auto_start: bool = Field(
            default=False, description="开机自启", json_schema_extra={"group": "外观"}
        )
        max_workers: int = Field(
            default=4, ge=1, le=16, description="并发任务数", json_schema_extra={"group": "性能"}
        )
        output_dir: str = Field(
            default="", description="输出目录", json_schema_extra={"group": "路径"}
        )
        notify: bool = Field(
            default=True, description="任务完成通知", json_schema_extra={"group": "通知"}
        )

    window = DesktopWindow(title="偏好设置")
    window.resize(720, 560)

    header = PageHeader(
        "偏好设置", hint="pydantic 模型直接生成设置页。点「应用」会弹出成功通知。", icon="settings"
    )

    page = SettingsPage(Prefs)
    page.applied.connect(lambda _model: app.notifier.success("已保存偏好设置"))

    body = QWidget()
    layout = QVBoxLayout(body)
    layout.setContentsMargins(20, 16, 20, 16)
    layout.setSpacing(12)
    layout.addWidget(header)
    layout.addWidget(page, stretch=1)
    window.set_body(body)
    return window


def build_chat(app: App) -> DesktopWindow:
    """即时对话：气泡列表 + 输入条，演示聊天结构。"""

    window = DesktopWindow(title="即时对话")
    window.resize(760, 600)

    header = PageHeader("即时对话", hint="气泡列表 + 输入条。接你自己的协议即可。", icon="message")

    messages = MessageList()
    messages.add_message("我是 psi6 助手，问点什么？", role="assistant", timestamp="09:30")
    messages.add_message("怎么把后台任务接到状态栏？", role="user", timestamp="09:31")
    messages.add_message(
        "用 StatusProgress(window.statusBar())，提交任务时回调 set_progress。",
        role="assistant",
        timestamp="09:31",
    )

    composer = Composer()

    def on_sent(text: str) -> None:
        messages.add_message(text, role="user")
        reply = messages.add_message("…", role="assistant", streaming=True)
        QTimer.singleShot(
            700,
            lambda: (
                reply.set_text(f"收到：{text}。psi6 的组件都能直接用，在画廊里挑一个看看？"),
                reply.set_streaming(False),
            ),
        )

    composer.sent.connect(on_sent)

    body = QWidget()
    layout = QVBoxLayout(body)
    layout.setContentsMargins(20, 16, 20, 16)
    layout.setSpacing(12)
    layout.addWidget(header)
    layout.addWidget(messages, stretch=1)
    layout.addWidget(composer)
    window.set_body(body)
    return window


def _build_minimal(app: App) -> QWidget:
    return minimal.build(app)


def _build_file_index(app: App) -> QWidget:
    return file_index.build(app)


def _build_task_job(app: App) -> QWidget:
    return task_job.build(app)


def _build_task_status(app: App) -> QWidget:
    return task_status.build(app)[0]


def _build_kit(app: App) -> QWidget:
    return KitWindow(app)


def _build_theme(app: App) -> QWidget | None:
    """自定义主题本身要展示绿色，单独起进程，别被画廊主题盖掉。"""

    subprocess.Popen([sys.executable, "-m", "psi6.examples.custom_theme"])
    return None


_USE_CASES = (
    UseCase(
        "quick-start",
        "最小窗口",
        "一个标题栏加一行文字，验证 psi6 起得来、主题套得上。",
        "monitor",
        "入门",
        ("入门",),
        _build_minimal,
    ),
    UseCase(
        "theme",
        "主题定制",
        "用一个 Python 类覆盖强调色，其余配色自动派生。",
        "sun",
        "入门",
        ("主题",),
        _build_theme,
    ),
    UseCase(
        "file-index",
        "文件批处理",
        "pydantic 表单 + 结果表 + 日志 + 进度 + 后台任务，全在一个窗口里。",
        "table",
        "数据与任务",
        ("数据", "任务"),
        _build_file_index,
    ),
    UseCase(
        "task",
        "后台任务",
        "开始 / 取消是分开的按钮，进度只在状态栏右侧。",
        "play",
        "数据与任务",
        ("任务",),
        _build_task_job,
    ),
    UseCase(
        "task-status",
        "任务状态",
        "两步进度，界面只读 TaskHandle.status，不轮询。",
        "activity",
        "数据与任务",
        ("任务",),
        _build_task_status,
    ),
    UseCase(
        "kit",
        "组件总览",
        "14 页组件目录，含状态矩阵与浅色 / 深色 / 密度切换。",
        "grid",
        "组件",
        ("组件",),
        _build_kit,
    ),
    UseCase(
        "dashboard",
        "数据看板",
        "统计卡 + 迷你折线 + 表格 + 分段切换，看组件怎么拼成监控页。",
        "layout-dashboard",
        "场景",
        ("场景",),
        build_dashboard,
    ),
    UseCase(
        "settings",
        "偏好设置",
        "pydantic 模型直接生成设置页，分组与错误提示都自动。",
        "settings",
        "场景",
        ("场景",),
        build_settings,
    ),
    UseCase(
        "chat",
        "即时对话",
        "气泡列表 + 输入条，结构齐全，接你自己的协议即可。",
        "message",
        "场景",
        ("场景",),
        build_chat,
    ),
)


class GalleryWindow(DesktopWindow):
    """示例画廊主窗口：首屏 + 分组卡片网格 + 主题切换。"""

    def __init__(self, app: App, parent: QWidget | None = None) -> None:
        super().__init__(title="psi6 示例画廊", icon="grid", frameless=True, parent=parent)
        self._app = app
        self.resize(1080, 720)
        self._opened: list[QWidget] = []

        header = QWidget()
        header.setObjectName("psi6GalleryHeader")
        hrow = QHBoxLayout(header)
        hrow.setContentsMargins(22, 14, 22, 14)
        hrow.setSpacing(14)

        brand = _BrandTile("grid")
        titles = QVBoxLayout()
        titles.setContentsMargins(0, 0, 0, 0)
        titles.setSpacing(2)
        title = QLabel("psi6 示例画廊")
        title.setObjectName("psi6GalleryTitle")
        subtitle = QLabel("挑一个用例，看 psi6 怎么把桌面组件拼成好用的工具。")
        subtitle.setObjectName("psi6GallerySub")
        titles.addWidget(title)
        titles.addWidget(subtitle)
        hrow.addWidget(brand)
        hrow.addLayout(titles, stretch=1)

        theme = SegmentedControl(("浅色", "深色", "紧凑"))
        theme.changed.connect(self._on_theme)
        hrow.addWidget(theme, alignment=Qt.AlignmentFlag.AlignVCenter)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content.setObjectName("psi6GalleryBody")
        cv = QVBoxLayout(content)
        cv.setContentsMargins(24, 22, 24, 24)
        cv.setSpacing(22)
        for category, cases in self._grouped():
            label = QLabel(category)
            label.setObjectName("psi6GalleryCat")
            cv.addWidget(label)
            host = QWidget()
            flow = FlowLayout(host)
            for case in cases:
                card = UseCaseCard(case)
                card.activated.connect(lambda chosen=case: self._launch(chosen))
                flow.addWidget(card)
            cv.addWidget(host)
        cv.addStretch()

        scroll.setWidget(content)

        main = QWidget()
        mv = QVBoxLayout(main)
        mv.setContentsMargins(0, 0, 0, 0)
        mv.setSpacing(0)
        mv.addWidget(header)
        mv.addWidget(scroll, stretch=1)
        self.set_body(main)
        self.statusBar().showMessage(f"共 {len(_USE_CASES)} 个用例 · 点击卡片打开")

    def _grouped(self) -> list[tuple[str, list[UseCase]]]:
        order: list[str] = []
        groups: dict[str, list[UseCase]] = {}
        for case in _USE_CASES:
            if case.category not in groups:
                groups[case.category] = []
                order.append(case.category)
            groups[case.category].append(case)
        return [(category, groups[category]) for category in order]

    def _on_theme(self, index: int) -> None:
        choice = ("light", "dark", "compact")[index]
        if choice == "compact":
            self._app.set_theme(Compact)
        else:
            self._app.set_theme(choice)

    def _launch(self, case: UseCase) -> None:
        window = case.launcher(self._app)
        if isinstance(window, QWidget):
            window.show()
            self._opened.append(window)


def main(argv: list[str] | None = None) -> int:
    """打开示例画廊。``--check`` 显示后立刻退出，供安装验证。"""

    args = sys.argv[1:] if argv is None else argv
    app = App("psi6-gallery", theme="light")
    _ = app.qt_app  # 先确保 QApplication 与 token 就绪，品牌图标才能取到正确反色
    window = GalleryWindow(app)
    if "--check" in args:
        QTimer.singleShot(0, app.qt_app.quit)
    return app.run(window)


if __name__ == "__main__":
    raise SystemExit(main())
