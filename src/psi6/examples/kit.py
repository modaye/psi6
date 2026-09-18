"""场景图库：用真实桌面布局核对默认 UI，而不是控件堆砌。"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from psi6.icons.glyphs import icon_names
from psi6.runtime.app import App
from psi6.ui.action_bar import ActionBar
from psi6.ui.app_shell import AppShell, NavDestination
from psi6.ui.banner import Banner
from psi6.ui.buttons import ghost_button, primary_button, text_button
from psi6.ui.chat import Composer, MessageList
from psi6.ui.check_list import CheckItem, CheckList
from psi6.ui.chrome import PageHeader, StatCard
from psi6.ui.collapsible import Collapsible
from psi6.ui.command_palette import Command, CommandPalette
from psi6.ui.data_table import DataTable, TableColumn
from psi6.ui.desktop_window import DesktopWindow
from psi6.ui.diff_view import DiffView
from psi6.ui.drop_zone import DropZone
from psi6.ui.empty_state import EmptyState
from psi6.ui.flow_layout import FlowLayout
from psi6.ui.form import field_switch
from psi6.ui.icon import Icon
from psi6.ui.image_well import ImageWell
from psi6.ui.kbd import KbdHint
from psi6.ui.log_panel import LogPanel
from psi6.ui.playlist import Playlist
from psi6.ui.search_field import SearchField
from psi6.ui.segmented import SegmentedControl
from psi6.ui.settings_page import pydantic_settings
from psi6.ui.status_badge import StatusBadge
from psi6.ui.stepper import Stepper
from psi6.ui.tag import TagRow
from psi6.ui.task_panel import TaskPanel
from psi6.ui.transport import TransportBar
from psi6.ui.workbench import ChangeList, ToolTile

_DESTINATIONS = (
    NavDestination("tool", "批处理", "wrench"),
    NavDestination("video", "影视", "film"),
    NavDestination("music", "音乐", "music"),
    NavDestination("chat", "Agent", "bot"),
    NavDestination("dash", "仪表盘", "layout-dashboard"),
    NavDestination("git", "Git", "git-branch"),
    NavDestination("monitor", "监控", "activity"),
    NavDestination("box", "工具箱", "grid"),
    NavDestination("flow", "向导", "list"),
    NavDestination("icons", "图标", "search"),
    NavDestination("theme", "主题", "sun"),
)

_PRESET_BRASS = Path(__file__).resolve().parents[1] / "theme" / "presets" / "brass.json"
_PRESET_COMPACT = Path(__file__).resolve().parents[1] / "theme" / "presets" / "compact.json"


class KitPrefs(BaseModel):
    """图库主题页的示范设置模型，不是业务模板。"""

    recursive: bool = field_switch(
        default=True,
        description="包含子目录",
        hint="设置项用 Switch；批处理过滤仍可用勾选框。",
        group="扫描",
    )
    notify: bool = field_switch(
        default=False,
        description="完成后弹出通知",
        hint="成功走 Notifier.success，不要刷 info Toast。",
        group="扫描",
    )
    appearance: Literal["light", "dark", "auto"] = Field(
        default="light",
        description="外观",
        json_schema_extra={"group": "外观", "hint": "auto 跟随操作系统浅色/深色。"},
    )


class KitWindow(DesktopWindow):
    """侧栏切换场景，用来看默认主题和图标是否站得住。"""

    def __init__(self, app: App, parent: QWidget | None = None) -> None:
        super().__init__(title="psi6 场景图库", icon="grid", parent=parent)
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
            "tool": self._page_tool,
            "video": self._page_video,
            "music": self._page_music,
            "chat": self._page_chat,
            "dash": self._page_dash,
            "git": self._page_git,
            "monitor": self._page_monitor,
            "box": self._page_box,
            "flow": self._page_flow,
            "icons": self._page_icons,
            "theme": self._page_theme,
        }
        for page_id, factory in pages.items():
            self.shell.add_page(page_id, factory())
        self.shell.show_page("tool")
        self.statusBar().showMessage("默认钢蓝工作台 · SVG 描边图标 · JSON 覆盖主题")
        self._palette = CommandPalette(self)
        self._palette.set_commands(
            [
                Command("tool", "打开批处理", "文件索引骨架", "wrench", "Ctrl+1"),
                Command("chat", "打开 Agent", "气泡会话", "bot", "Ctrl+4"),
                Command("theme-dark", "切换深色", "token 主题", "moon", "Ctrl+D"),
                Command("theme-light", "切换浅色", "token 主题", "sun"),
            ]
        )
        self._palette.activated.connect(self._run_command)
        shortcut = QShortcut(QKeySequence("Ctrl+K"), self)
        shortcut.activated.connect(lambda: self._palette.popup(self))

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

    def _run_command(self, command_id: str) -> None:
        if command_id == "theme-dark":
            self._apply_theme("dark")
            return
        if command_id == "theme-light":
            self._apply_theme("light")
            return
        self.show_page(command_id)
        self._banner.set_notice(f"命令：{command_id}", tone="info")

    def _page_tool(self) -> QWidget:
        header = PageHeader("文件批处理", hint="选目录、跑任务、结果进表。少用参数在高级选项。", icon="wrench")
        body = QWidget()
        col = QVBoxLayout(body)
        col.setContentsMargins(0, 0, 0, 0)
        extra = Collapsible("高级选项")
        extra.add_widget(QCheckBox("包含子目录"))
        extra.add_widget(QCheckBox("忽略隐藏文件"))
        col.addWidget(extra)
        col.addWidget(TaskPanel())
        tags = TagRow()
        col.addWidget(tags)
        tags.set_labels((".md", ".csv", ".log"))
        table = DataTable(
            [
                TableColumn("name", "名称", stretch=True),
                TableColumn("kind", "类型"),
                TableColumn("size", "大小"),
            ],
        )
        table.set_rows(
            [
                {"name": "readme.md", "kind": ".md", "size": "2 KB"},
                {"name": "export.csv", "kind": ".csv", "size": "41 KB"},
            ]
        )
        col.addWidget(table, stretch=1)
        return self._wrap(header, body)

    def _page_video(self) -> QWidget:
        header = PageHeader("影片工作台", hint="解码器仍是业务；这里只提供时间轴、空播区和音量。", icon="film")
        body = QWidget()
        col = QVBoxLayout(body)
        col.setContentsMargins(0, 0, 0, 0)
        stage = EmptyState("没有打开影片", "从资料库选一部，或拖进此区域。", icon="film", tone="info")
        col.addWidget(stage, stretch=1)
        bar = TransportBar()
        bar.set_time("12:04", "1:42:18")
        bar.set_progress(220)
        bar.set_volume(70)
        col.addWidget(bar)
        return self._wrap(header, body)

    def _page_music(self) -> QWidget:
        header = PageHeader("播放队列", hint="曲目表 + 传输条。音量、静音与进度都是桌面习惯位。", icon="music")
        body = QWidget()
        col = QVBoxLayout(body)
        col.setContentsMargins(0, 0, 0, 0)
        search = SearchField(placeholder="筛选曲目…")
        col.addWidget(search)
        playlist = Playlist()
        playlist.set_tracks(
            [
                {"title": "Night Shift", "artist": "Harbor", "time": "3:41"},
                {"title": "Steel Wire", "artist": "Kite", "time": "4:02"},
                {"title": "Low Tide", "artist": "Harbor", "time": "2:58"},
            ]
        )
        playlist.set_current(0)
        search.query_changed.connect(playlist.set_filter)
        col.addWidget(playlist, stretch=1)
        transport = TransportBar()
        transport.set_playing(True)
        transport.set_time("1:12", "3:41")
        transport.set_progress(340)
        playlist.track_activated.connect(lambda _: transport.set_playing(True))
        col.addWidget(transport)
        return self._wrap(header, body)

    def _page_chat(self) -> QWidget:
        header = PageHeader("Agent 会话", hint="气泡 + 输入条。流式协议不在 UI 层。", icon="bot")
        body = QWidget()
        col = QVBoxLayout(body)
        col.setContentsMargins(0, 0, 0, 0)
        messages = MessageList()
        messages.add_message("把这个目录做成批处理窗口，结果进表。", role="user", timestamp="18:02")
        messages.add_message(
            "用 BatchToolWindow，参数走 Pydantic，任务放进 TaskRunner。",
            role="assistant",
            timestamp="18:02",
        )
        streaming = messages.add_message("正在整理变更摘要", role="assistant", timestamp="18:03", streaming=True)
        streaming.set_text("工作区有 3 个文件改动，下一步可以看 DiffView。")
        streaming.set_streaming(False)
        col.addWidget(messages, stretch=1)
        composer = Composer()
        composer.sent.connect(lambda text: messages.add_message(text, role="user", timestamp="现在"))
        col.addWidget(composer)
        return self._wrap(header, body)

    def _page_dash(self) -> QWidget:
        header = PageHeader("运行概览", hint="数字卡片看趋势，表看明细。", icon="layout-dashboard")
        body = QWidget()
        col = QVBoxLayout(body)
        col.setContentsMargins(0, 0, 0, 0)
        cards = QHBoxLayout()
        cards.addWidget(
            StatCard(
                "今日任务",
                "128",
                hint="比昨日 +12%",
                icon="activity",
                sparkline=(90, 96, 88, 110, 128),
            )
        )
        cards.addWidget(StatCard("失败", "3", hint="需人工", icon="warning", sparkline=(1, 4, 2, 5, 3)))
        cards.addWidget(StatCard("队列", "17", hint="最长 4 分钟", icon="clock", sparkline=(8, 12, 20, 15, 17)))
        cards.addStretch()
        col.addLayout(cards)
        table = DataTable(["job", "status", "duration"])
        table.set_columns(
            [
                TableColumn("job", "任务", stretch=True),
                TableColumn("status", "状态"),
                TableColumn("duration", "耗时"),
            ]
        )
        table.set_rows(
            [
                {"job": "index-docs", "status": "成功", "duration": "12s"},
                {"job": "mail-sync", "status": "运行中", "duration": "—"},
            ]
        )
        col.addWidget(table, stretch=1)
        return self._wrap(header, body)

    def _page_git(self) -> QWidget:
        header = PageHeader("工作区变更", hint="状态色 + 路径 + unified diff。不做完整 Git porcelain。", icon="git-branch")
        body = QWidget()
        split = QHBoxLayout(body)
        split.setContentsMargins(0, 0, 0, 0)
        changes = ChangeList()
        changes.set_changes(
            [
                ("src/psi6/ui/icon.py", "modified"),
                ("src/psi6/icons/svg/search.svg", "added"),
                ("src/psi6/examples/batch_demo.py", "deleted"),
            ]
        )
        diff = DiffView()
        sample = [
            (" ", "def token_color(widget, *, tone=\"neutral\"):"),
            ("-", "    return widget.palette().color()"),
            ("+", "    app = QApplication.instance()"),
            ("+", "    return app.property(key)"),
        ]
        diff.set_lines(sample)
        changes.current_changed.connect(lambda path: diff.set_lines(sample))
        changes.set_current("src/psi6/ui/icon.py")
        split.addWidget(changes, stretch=2)
        split.addWidget(diff, stretch=3)
        return self._wrap(header, body)

    def _page_monitor(self) -> QWidget:
        header = PageHeader("服务监控", hint="健康数字 + 操作日志。探针逻辑仍走 TaskRunner。", icon="activity")
        body = QWidget()
        col = QVBoxLayout(body)
        col.setContentsMargins(0, 0, 0, 0)
        row = QHBoxLayout()
        row.addWidget(
            StatCard("API", "200", hint="us-east · 41ms", icon="monitor", sparkline=(210, 198, 205, 200))
        )
        row.addWidget(StatCard("Worker", "4/4", hint="全部在线", icon="terminal"))
        row.addWidget(StatusBadge("健康", tone="success"))
        row.addStretch()
        col.addLayout(row)
        log = LogPanel()
        from psi6.runtime.logs import LogLevel, LogRecord

        log.append(LogRecord(LogLevel.SUCCESS, "health-check ok", extra={"ms": 41}))
        log.append(LogRecord(LogLevel.WARNING, "retry queue depth 17"))
        col.addWidget(log, stretch=1)
        return self._wrap(header, body)

    def _page_box(self) -> QWidget:
        header = PageHeader("内部工具箱", hint="一格一个入口，点进去才是 BatchToolWindow。", icon="grid")
        body = QWidget()
        flow = FlowLayout(body, spacing=12)
        tiles = (
            ("文件索引", "扫目录，结果进表", "folder"),
            ("邮件预览", "生成草稿不发送", "message"),
            ("表格合并", "多份 CSV 对齐", "table"),
            ("日志切片", "按级别导出", "list"),
        )
        for title, hint, icon in tiles:
            tile = ToolTile(title, hint, icon=icon)
            tile.clicked.connect(lambda t=title: self._app.notifier.success(f"打开 {t}"))
            flow.addWidget(tile)
        return self._wrap(header, body)

    def _page_flow(self) -> QWidget:
        header = PageHeader(
            "导入向导",
            hint="Stepper 管步骤；CommandPalette 管跳转。Ctrl+K 打开命令面板。",
            icon="list",
        )
        header.add_trailing(KbdHint("Ctrl+K"))
        body = QWidget()
        col = QVBoxLayout(body)
        col.setContentsMargins(0, 0, 0, 0)
        stepper = Stepper(("选择目录", "预览", "写入"))
        col.addWidget(stepper)
        stepper.set_current(1)
        drop = DropZone(
            "把文件拖到这里",
            "也可以点击选择。过滤用构造参数，不要写死扩展名。",
            icon="file",
            filters="Python (*.py *.pyw);;All Files (*)",
            browse_on_click=False,
        )
        drop.files_dropped.connect(lambda paths: self._banner.set_notice(f"收到 {len(paths)} 个路径", tone="success"))
        drop.clicked.connect(drop.browse)
        col.addWidget(drop)
        segments = SegmentedControl(("自己测试", "发给同事", "正式发布"))
        col.addWidget(segments)
        notice = Banner()
        col.addWidget(notice)
        notice.set_notice(
            "未找到可用的 Python。可以查看说明或先排除这项。",
            tone="warning",
            actions=[
                ("查看说明", lambda: self._banner.set_notice("短句请走 Notifier；长文用 ContentDialog。", tone="info")),
                ("继续", lambda: notice.clear()),
            ],
        )
        extra = Collapsible("专业选项")
        checks = CheckList()
        checks.set_items(
            [
                CheckItem("entry", "main.py", "入口脚本"),
                CheckItem("secret", "secrets.env", "密钥，默认排除", checked=False),
            ]
        )
        extra.add_widget(checks)
        extra.add_widget(ImageWell())
        col.addWidget(extra)
        stack = QStackedWidget()
        stack.addWidget(
            EmptyState("选择目录", "用 FolderInput，不要在业务里弹 QFileDialog。", icon="folder", tone="info")
        )
        preview = EmptyState("预览 128 个文件", "确认扩展名过滤后再写入。", icon="table", tone="info")
        stack.addWidget(preview)
        stack.addWidget(EmptyState("准备写入", "任务必须进 TaskRunner。", icon="play", tone="success"))
        stack.setCurrentIndex(1)
        stepper.current_changed.connect(stack.setCurrentIndex)
        col.addWidget(stack, stretch=1)
        actions = ActionBar()
        back = ghost_button("上一步")
        nxt = primary_button("下一步")
        back.clicked.connect(stepper.back)
        nxt.clicked.connect(stepper.next)
        paste = text_button("粘贴代码")
        paste.clicked.connect(lambda: self._banner.set_notice("粘贴草稿放进 ContentDialog 的 QPlainTextEdit。", tone="info"))
        open_cmd = primary_button("命令面板")
        open_cmd.clicked.connect(lambda: self._palette.popup(self))
        actions.add_left(back)
        actions.add_left(nxt)
        actions.add_left(paste)
        actions.add_right(open_cmd)
        col.addWidget(actions)
        return self._wrap(header, body)

    def _page_icons(self) -> QWidget:
        header = PageHeader("图标表", hint="全部为自绘 24×24 描边 SVG，随 token 着色。", icon="search")
        body = QWidget()
        grid = QGridLayout(body)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(10)
        names = icon_names()
        columns = 6
        for index, name in enumerate(names):
            cell = QWidget()
            cell_layout = QHBoxLayout(cell)
            cell_layout.setContentsMargins(6, 4, 6, 4)
            cell_layout.addWidget(Icon(name, size=18))
            label = QLabel(name)
            label.setObjectName("psi6Hint")
            cell_layout.addWidget(label)
            grid.addWidget(cell, index // columns, index % columns)
        return self._wrap(header, body)

    def _page_theme(self) -> QWidget:
        header = PageHeader(
            "主题与扩展",
            hint="light/dark 预设；JSON 覆盖色、尺寸、密度、图标；开关和自定义控件都读同一套 token。",
            icon="settings",
        )
        body = QWidget()
        col = QVBoxLayout(body)
        col.setContentsMargins(0, 0, 0, 0)
        actions = ActionBar()
        light = primary_button("浅色")
        dark = primary_button("深色")
        brass = primary_button("黄铜预设")
        compact = primary_button("紧凑")
        follow = primary_button("跟随系统")
        light.clicked.connect(lambda: self._apply_theme("light"))
        dark.clicked.connect(lambda: self._apply_theme("dark"))
        brass.clicked.connect(lambda: self._apply_theme(_PRESET_BRASS))
        compact.clicked.connect(lambda: self._apply_theme(_PRESET_COMPACT))
        follow.clicked.connect(lambda: self._apply_theme("auto"))
        actions.add_left(light)
        actions.add_left(dark)
        actions.add_left(brass)
        actions.add_left(compact)
        actions.add_left(follow)
        col.addWidget(actions)
        prefs = pydantic_settings(KitPrefs())
        prefs.applied.connect(self._on_kit_prefs)
        col.addWidget(prefs)
        help_text = QLabel(
            "自定义主题：JSON / TOML / YAML 覆盖 token。图标用主题旁 icons/ 同名 svg。\n"
            "自绘：token_color / token_int / token_ms。覆盖单个图标：register_icon。"
        )
        help_text.setObjectName("psi6Hint")
        help_text.setWordWrap(True)
        col.addWidget(help_text)
        sample = QPlainTextEdit()
        sample.setReadOnly(True)
        sample.setPlainText(
            "base = \"dark\"\n"
            "density = \"compact\"\n"
            "color_primary = \"#7a9e7e\"\n"
            "control_height = 30\n"
            "motion_fast_ms = 120\n"
            "\n"
            "[button]\n"
            "radius = 8\n"
            "\n"
            "# 同目录 icons/search.svg 会替换 Icon(\"search\")\n"
        )
        col.addWidget(sample, stretch=1)
        return self._wrap(header, body)

    def _on_kit_prefs(self, model: object) -> None:
        if not isinstance(model, KitPrefs):
            return
        self._app.save_config(model)
        self._apply_theme(model.appearance)
        if model.notify:
            self._banner.set_notice("通知已打开", tone="success")

    def _apply_theme(self, theme: str | Path) -> None:
        self._app.set_theme(theme)
        self.shell.sidebar.apply_metrics()
        self.shell.sidebar.refresh_icons()
        self.update()
        name = theme if isinstance(theme, str) else theme.stem
        self._banner.set_notice(f"已应用主题：{name}", tone="success")
        self.statusBar().showMessage(f"主题 {name} · primary {self._app.tokens.color_primary}")


def main() -> None:
    """打开场景图库。"""

    app = App("psi6-kit", theme="light")
    raise SystemExit(app.run(KitWindow(app), tray=True, single_instance=False))
