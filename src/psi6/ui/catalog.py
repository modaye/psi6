"""``psi6.ui`` 公共控件的机器可读索引。

Agent 不必读源码就能选对控件。名字来自 ``psi6.ui.__all__``，构造参数由
``inspect.signature`` 实时读取；适用场景和替代关系维护在本文件的说明表里。
``python -m psi6 catalog --json`` 输出同一份内容。

新增公开名字却没有说明，或说明指向已经删除的名字，测试会失败。
"""

from __future__ import annotations

import inspect
import json
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Any

from PySide6.QtWidgets import QWidget

import psi6.ui as ui

__all__ = [
    "Component",
    "Parameter",
    "catalog_json",
    "components",
    "find",
    "main",
    "render",
]

# 名字 -> (一句话职责, 何时用, 不要用它代替)
_USAGE: dict[str, tuple[str, str, str]] = {
    "ActionBar": (
        "工具行：左侧状态、右侧操作。",
        "页内需要一行稳定动作区时。",
        "任务条：不要用它把开始、取消和进度排成一行。",
    ),
    "AppShell": (
        "左侧导航加页面栈的应用壳。",
        "多页工具需要换页时。",
        "单页内的分栏（用 ``Workspace``）。",
    ),
    "Banner": (
        "页内横幅，可带 1～2 个动作。",
        "任务结果、可恢复错误、空目录提示。",
        "必须阻塞用户的确认（用 ``confirm`` / ``fail``）。",
    ),
    "Breadcrumb": (
        "只显示当前位置的面包屑。",
        "提示当前所在层级。",
        "页面切换（用 ``AppShell`` 导航）。",
    ),
    "Card": (
        "弱边卡片。",
        "把一组说明收成一块表面。需要浮起时 ``elevated=True``。",
        "文件索引、设置、任务页的卡片墙。平面分区用 Panel。",
    ),
    "BusyOverlay": (
        "盖在宿主控件上的忙碌层。",
        "任务运行期间禁止点选结果表。",
        "替代进度条或状态文字。",
    ),
    "ChangeList": (
        "文件变更列表容器。",
        "展示一组 Git 变更。",
        "通用结果表（用 ``DataTable``）。",
    ),
    "ChangeRow": (
        "单条文件变更行。",
        "放进 ``ChangeList``。",
        "可编辑的文件清单。",
    ),
    "CheckItem": (
        "可勾选清单项的数据。",
        "传给 ``CheckList.set_items``。",
        "通用列表模型。",
    ),
    "CheckList": (
        "带勾选的清单。",
        "选择要处理的文件或排除项。",
        "结果表（用 ``DataTable``）。",
    ),
    "Collapsible": (
        "可折叠分组。",
        "高级选项、次要说明。",
        "收纳主操作按钮。",
    ),
    "ColumnPicker": (
        "列的显隐与顺序面板，状态可持久化到 ``ConfigStore``。",
        "结果表列太多，用户要自己挑。",
        "直接改 ``DataTable`` 的列定义（用 ``set_columns``）。",
    ),
    "ColumnState": (
        "``ColumnPicker`` 里一列的状态：key、标题、是否可见、是否必显。",
        "构造列清单。",
        "表格的数据行。",
    ),
    "Command": (
        "命令面板条目的数据。",
        "传给 ``CommandPalette.set_commands``。",
        "菜单或工具栏定义。",
    ),
    "CommandPalette": (
        "命令检索面板。``install`` 后，条目上的 shortcut 会按键触发。",
        "动作较多的工具。",
        "把每个菜单项再登记一遍快捷键。",
    ),
    "Composer": (
        "对话输入条。",
        "``MessageList`` 下方的输入。",
        "普通表单（用 ``pydantic_form``）。",
    ),
    "ContentDialog": (
        "带主体控件的对话框。",
        "需要表单或预览的确认。",
        "一句短提示（用 ``confirm`` / ``inform`` / ``fail``）。",
    ),
    "DataTable": (
        "结果表：排序、筛选、空态、忙碌态；行按需增量渲染，几万行不卡首屏。"
        "``set_reorderable(True)`` 后可拖动一行调整原始顺序。",
        "任务结果预览。",
        "树表、分页网格或单元格编辑。",
    ),
    "DebugEventFilter": (
        "把事件记到 sink 的调试过滤器。",
        "排查悬停、按下和焦点。",
        "业务逻辑。",
    ),
    "DesktopWindow": (
        "主窗口壳，默认 Qt 标题栏。",
        "应用主窗口。",
        "无边框需求之外自绘标题栏。",
    ),
    "DiffView": (
        "统一 diff 的着色视图。",
        "展示补丁文本。",
        "Git 解析或合并。",
    ),
    "DropZone": (
        "大点击面加 URL 拖放热区。",
        "首页导入入口。",
        "路径输入行（用 ``FileInput``）。",
    ),
    "EditHistory": (
        "撤销 / 重做。``push`` 记下怎么做和怎么撤回，``install`` 接 Ctrl+Z。",
        "用户改了数据、并且需要退回上一步时。",
        "输入框内部的逐字撤销。",
    ),
    "EmptyState": (
        "无数据占位。",
        "日志、属性或自定义区域为空。",
        "结果表空态（``DataTable`` 已内置）。",
    ),
    "FileInput": (
        "文件路径输入，带浏览、拖放、清除和校验。",
        "表单里的文件字段。",
        "直接调用 ``QFileDialog``。",
    ),
    "FloatBall": (
        "始终置顶的小圆标。单击显示或隐藏主窗口，拖动换位置，右键退出。",
        "窗口藏起后仍要一个屏幕上的入口。``App.run(..., float_ball=True)`` 会在关窗口后留住进程。",
        "系统托盘菜单（用 ``tray=True``）。不要把它放进页面布局。",
    ),
    "FlowLayout": (
        "一行放不下就换行的布局。",
        "标签、磁贴。",
        "手算坐标。",
    ),
    "FolderInput": (
        "目录路径输入。",
        "表单里的目录字段。",
        "直接调用 ``QFileDialog.getExistingDirectory``。",
    ),
    "FormError": (
        "表单校验失败异常，带字段错误。",
        "捕获 ``get_model`` 的错误。",
        "普通运行时异常。",
    ),
    "FormView": (
        "由 pydantic 模型生成的任务参数表单。",
        "参数页。",
        "手写每个输入框。",
    ),
    "Icon": (
        "主题图标。",
        "按钮、标题旁的小图标。",
        "emoji 或另一套图标字体。",
    ),
    "IconButton": (
        "只有图标的按钮，必须带 label。",
        "工具栏、行内操作。",
        "没有可访问名称的图形按钮。",
    ),
    "IconPreview": (
        "图标缩略图预览。",
        "查看选中的图标文件。",
        "图片编辑器。",
    ),
    "ImageWell": (
        "图片缩略图加选择、清除。",
        "图标或图片字段。",
        "表单里的文件对话框（用 ``FileInput``）。",
    ),
    "KbdHint": (
        "快捷键提示块。",
        "提示 Ctrl+K 等组合键。",
        "登记快捷键（用 ``ShortcutBook``）。",
    ),
    "LogConsole": (
        "终端式日志控件。",
        "``logging`` 诊断输出。",
        "用户可读的操作日志（用 ``LogPanel``）。",
    ),
    "LogConsoleHandler": (
        "把 ``logging`` 记录接到 ``LogConsole``。",
        "``logger.addHandler(console.handler())``。",
        "某一种日志库的专用桥。",
    ),
    "LogPanel": (
        "可筛选的操作日志表，默认最多 2000 条。",
        "任务过程日志。",
        "诊断日志（用 ``LogConsole``）。",
    ),
    "MenuAction": (
        "``ContextMenu`` 里的一项：图标、快捷键提示、危险项、勾选 / 单选态、分隔线。",
        "描述一份右键菜单。",
        "工具栏按钮（用 ``ActionBar``）。",
    ),
    "MenuTarget": (
        "右键命中目标：``kind`` 是容器名，``key`` 是命中行 / 节点 / 页签的标识。",
        "菜单回调里判断「右键点到了什么」。",
        "长期保存的状态（行数据是命中时的快照）。",
    ),
    "MessageList": (
        "Agent 对话气泡列表。",
        "展示对话历史。",
        "流式协议实现。",
    ),
    "attach_context_menu": (
        "给 ``DataTable`` / ``TreeView`` / ``TabView`` 挂右键菜单。",
        "容器需要自定义右键动作时；右键会自动选中命中行。",
        "登记快捷键（用 ``ShortcutBook``，每个键只登记一次）。",
    ),
    "build_menu": (
        "把 ``MenuAction`` 序列渲染成 ``QMenu``，图标按当前 token 着色并跟随换肤。",
        "自己控制弹出时机（例如托盘、标题栏）。",
        "容器右键（用 ``attach_context_menu``）。",
    ),
    "clear_style": (
        "去掉 ``set_style`` 写上的样式。",
        "控件要回到主题默认。",
        "自己清空样式表。",
    ),
    "column_toggle_menu": (
        "列头右键用的「勾选显示哪些列」菜单项序列。",
        "表格列多，用户要自己挑显示哪几列。",
        "完整的列管理面板（用 ``ColumnPicker``）。",
    ),
    "NavDestination": (
        "``AppShell`` 的导航目标数据。",
        "构造 ``AppShell``。",
        "单页内的面包屑。",
    ),
    "Panel": (
        "平面表面。",
        "设置分组和侧栏说明。",
        "需要弱边或投影时用 Card。",
    ),
    "PageHeader": (
        "页面标题、说明和图标。",
        "每页顶部。",
        "窗口标题栏。",
    ),
    "PathState": (
        "路径输入状态：空、已选、无效。",
        "判断 ``FileInput.state``。",
        "自己解析路径是否有效。",
    ),
    "Playlist": (
        "播放队列列表。",
        "媒体工具。",
        "通用数据表。",
    ),
    "PressScaleFilter": (
        "按下缩小的反馈过滤器。",
        "自绘控件需要按压反馈。",
        "改布局尺寸做按压效果。",
    ),
    "PropertyList": (
        "只读属性表。",
        "查看选中对象的字段。",
        "编辑字段（用 ``pydantic_form``）。",
    ),
    "SearchField": (
        "带图标的搜索输入。",
        "表格或清单筛选。",
        "``DataTable.set_filter`` 已经够用时再包一层。",
    ),
    "Section": (
        "带标题和说明的分区容器。",
        "表单或设置分组。",
        "卡片式堆叠层次。",
    ),
    "SegmentedControl": (
        "二选一或三选一的分段开关。",
        "少量互斥选项。",
        "长列表（用下拉）。",
    ),
    "SettingRow": (
        "标题加开关的设置行。",
        "非可选布尔设置。",
        "可选布尔（表单会改用三态编辑）。",
    ),
    "ShortcutBook": (
        "一个窗口上的快捷键登记。同一序列只保留一条命令。",
        "命令或撤销要能按键触发时。",
        "在每个右键菜单里各注册一遍。",
    ),
    "SettingsPage": (
        "由 pydantic 模型生成的设置页。",
        "应用设置。",
        "任务参数页（用 ``pydantic_form``）。",
    ),
    "Sparkline": (
        "迷你折线。",
        "``StatCard`` 或监控。",
        "完整图表。",
    ),
    "StatCard": (
        "指标卡片。",
        "概览数字。",
        "主内容容器。",
    ),
    "StatusBadge": (
        "状态标签。",
        "任务或文件状态。",
        "可点击按钮。",
    ),
    "StatusProgress": (
        "状态栏右侧的进度。",
        "没有另行指定位置的任务进度。",
        "页面中间的进度需求（那里改用 ``QProgressBar``，且不要重复）。",
    ),
    "Stepper": (
        "分步向导指示条。点击发出 ``clicked``，不自己跳步。",
        "多步流程。",
        "页面切换本身。",
    ),
    "Style": (
        "贴在单个控件上的字号、字重、字色和底色。",
        "这一处要和旁边不同，或运行中改样式。",
        "整页样式表。主题密度仍用 modern / compact。",
    ),
    "Switch": (
        "开关控件。",
        "设置项。",
        "表单里手写复选框。",
    ),
    "UnderlineTabs": (
        "页内文字页签，底部主色条会滑到当前项。",
        "同一页里切换几段说明。",
        "可关闭的文档页签（用 TabView）。",
    ),
    "TabView": (
        "多文档标签页：可关闭、可拖动重排、空态；标签顺序与当前项可持久化。",
        "一次打开多份文档，按 ``key`` 复用控件。",
        "侧栏换页（用 ``AppShell``）或单页分栏（用 ``Workspace``）。",
    ),
    "TableColumn": (
        "``DataTable`` 的列定义。",
        "构造 ``DataTable``。",
        "隐藏列等显示逻辑。",
    ),
    "Tag": (
        "标签芯片。",
        "分类、状态。",
        "按钮。",
    ),
    "TagRow": (
        "可换行的标签行。",
        "放多个 ``Tag``。",
        "手动排列标签。",
    ),
    "TitleBar": (
        "无边框窗口的自绘标题栏。",
        "``DesktopWindow(frameless=True)``。",
        "默认 Qt 标题栏。",
    ),
    "ToolBar": (
        "``Workspace`` 顶部工具栏，主要动作在左。",
        "页内的开始、取消等动作。",
        "把进度条也塞进来。",
    ),
    "ToastCard": (
        "单条角落通知卡片。",
        "由 ``ToastHost`` 管理。",
        "必须看见的错误（用 ``fail``）。",
    ),
    "ToastHost": (
        "窗口右上角的通知栈。",
        "短通知。",
        "替代 ``fail`` / ``warn`` 对话框。",
    ),
    "Tone": (
        "界面语气：neutral、info、success、warning、error。",
        "传给 Banner、StatusBadge、Tag 等 tone 参数。",
        "自定义颜色。",
    ),
    "ToolTile": (
        "工具箱磁贴。",
        "首页功能入口。",
        "普通按钮。",
    ),
    "TransportBar": (
        "播放控制条。",
        "媒体工具。",
        "解码实现。",
    ),
    "TrayIcon": (
        "系统托盘图标。左键展开或隐藏窗口，右键菜单可追加动作。",
        "``app.run(tray=True)`` 时由 ``App`` 管理。最小化时单击改为展开。",
        "手动创建多个托盘图标。没有系统托盘时用 ``FloatBall``。",
    ),
    "TreeColumn": (
        "``TreeView`` 的列定义。",
        "构造 ``TreeView``。",
        "隐藏列等显示逻辑。",
    ),
    "TreeNode": (
        "``TreeView`` 的层级节点数据。",
        "传给 ``TreeView.set_nodes``。",
        "通用树模型。",
    ),
    "TreeView": (
        "层级结果视图：嵌套节点、多列、筛选保留祖先。",
        "文件树、依赖树、大纲等层级浏览。",
        "可编辑单元格或分页网格（另起控件）。",
    ),
    "confirm": (
        "确认对话框。",
        "需要用户决定的操作。",
        "信息提示（用 ``inform``）。",
    ),
    "danger_button": (
        "危险动作按钮。",
        "删除、覆盖。",
        "普通主按钮。",
    ),
    "fail": (
        "错误对话框，支持 detail。",
        "必须看见的错误。",
        "状态栏短句（用 ``app.notifier.info``）。",
    ),
    "field_advanced": (
        "标记字段进入高级选项。",
        "模型字段 metadata。",
        "手写 ``Collapsible``。",
    ),
    "field_dir": (
        "目录字段，生成 ``FolderInput``。",
        "模型字段 metadata。",
        "直接构造 ``FolderInput``。",
    ),
    "field_file": (
        "文件字段，生成 ``FileInput``。",
        "模型字段 metadata。",
        "直接构造 ``FileInput``。",
    ),
    "field_secret": (
        "密码字段。",
        "密钥、令牌。",
        "明文输入。",
    ),
    "field_switch": (
        "布尔字段，生成 ``Switch``。",
        "设置项。",
        "可选布尔（会改用三态编辑）。",
    ),
    "ghost_button": (
        "次要按钮。",
        "取消、次要动作。",
        "主操作。",
    ),
    "inform": (
        "信息对话框。",
        "需要用户确认已读的说明。",
        "状态栏短句（用 ``app.notifier.info``）。",
    ),
    "install_press_scale": (
        "给控件安装按下缩小的反馈。",
        "自绘控件。",
        "布局控件。",
    ),
    "link_button": (
        "文字链按钮。",
        "跳转、次要入口。",
        "主操作。",
    ),
    "is_loading": (
        "按钮是否在加载。",
        "读取 ``set_loading`` 的状态。",
        "用 ``isEnabled`` 判断，加载时按钮仍然可用外观。",
    ),
    "set_loading": (
        "按钮加载态：左侧圆弧，挡住点击，文字和颜色保留。",
        "保存、提交正在进行，进度不另开一条按钮皮肤。",
        "把按钮 ``setEnabled(False)``，那会变成灰色禁用。",
    ),
    "primary_button": (
        "主按钮。",
        "开始、保存。",
        "同一页放多个。",
    ),
    "pydantic_form": (
        "由模型构造 ``FormView``。",
        "任务参数。",
        "设置页（用 ``pydantic_settings``）。",
    ),
    "set_style": (
        "给一个控件设置字号、字重、字色或底色。",
        "同一页里各项样式不同，或随状态改样式。",
        "在页面里写样式表。颜色用字面色或 token 名。",
    ),
    "pydantic_settings": (
        "由模型构造 ``SettingsPage``。",
        "应用设置。",
        "任务参数（用 ``pydantic_form``）。",
    ),
    "text_button": (
        "无边框文字按钮。",
        "行内弱操作。",
        "需要明确边界的操作。",
    ),
    "warn": (
        "警告对话框。",
        "可以继续但需要提醒。",
        "错误（用 ``fail``）。",
    ),
    "Workspace": (
        "页内工具栏、面包屑和可拖拽分栏；栏可显隐，拖动后的宽度与显隐状态可导出并持久化。",
        "单页工作区，需要记住面板布局时。",
        "多页换页（用 ``AppShell``）或浮动停靠窗口。",
    ),
}

# 公开导入位置与本模块内部实现不同时，在这里纠正。
_MODULE_OVERRIDES = {
    "PathState": "psi6.ui.file_input",
    "Tone": "psi6.ui.tone",
}


@dataclass(frozen=True, slots=True)
class Parameter:
    """一个构造参数的只读描述。"""

    name: str
    kind: str
    annotation: str
    default: str | None


@dataclass(frozen=True, slots=True)
class Component:
    """一个公共控件的只读描述。"""

    name: str
    module: str
    kind: str
    summary: str
    use: str
    avoid: str
    params: tuple[Parameter, ...]

    @property
    def import_line(self) -> str:
        return f"from {self.module} import {self.name}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "module": self.module,
            "kind": self.kind,
            "summary": self.summary,
            "use": self.use,
            "avoid": self.avoid,
            "import": self.import_line,
            "params": [
                {
                    "name": param.name,
                    "kind": param.kind,
                    "annotation": param.annotation,
                    "default": param.default,
                }
                for param in self.params
            ],
        }


def _kind(name: str, obj: Any) -> str:
    if name == "Tone":
        return "alias"
    if isinstance(obj, type):
        if issubclass(obj, QWidget):
            return "widget"
        if issubclass(obj, Enum):
            return "enum"
        if issubclass(obj, BaseException):
            return "error"
        return "type"
    if inspect.isfunction(obj):
        return "function"
    return "value"


def _format_default(value: Any) -> str:
    if isinstance(value, Enum):
        return repr(value.value)
    return repr(value)


def _parameters(obj: Any, kind: str) -> tuple[Parameter, ...]:
    if kind in {"alias", "enum"}:
        return ()
    try:
        signature = inspect.signature(obj)
    except (TypeError, ValueError):
        return ()
    params: list[Parameter] = []
    for param in signature.parameters.values():
        if param.name == "self":
            continue
        default = (
            None if param.default is inspect.Parameter.empty else _format_default(param.default)
        )
        params.append(
            Parameter(
                name=param.name,
                kind=param.kind.name.lower(),
                annotation=""
                if param.annotation is inspect.Parameter.empty
                else str(param.annotation),
                default=default,
            )
        )
    return tuple(params)


def components() -> tuple[Component, ...]:
    """按名字排序返回全部公共控件的描述。"""

    missing = [name for name in ui.__all__ if name not in _USAGE]
    if missing:
        raise RuntimeError(f"控件索引缺少说明：{', '.join(sorted(missing))}")
    extra = sorted(set(_USAGE) - set(ui.__all__))
    if extra:
        raise RuntimeError(f"控件索引包含已删除的名字：{', '.join(extra)}")
    result: list[Component] = []
    for name in sorted(ui.__all__):
        obj = getattr(ui, name)
        kind = _kind(name, obj)
        summary, use, avoid = _USAGE[name]
        result.append(
            Component(
                name=name,
                module=_MODULE_OVERRIDES.get(name, getattr(obj, "__module__", "psi6.ui")),
                kind=kind,
                summary=summary,
                use=use,
                avoid=avoid,
                params=_parameters(obj, kind),
            )
        )
    return tuple(result)


def find(name: str) -> Component:
    """按名字查找控件；找不到时抛出 ``KeyError`` 并列出近似项。"""

    for component in components():
        if component.name == name:
            return component
    known = [component.name for component in components()]
    raise KeyError(f"未知控件 {name!r}。可用：{', '.join(known)}")


def catalog_json(*, indent: int = 2) -> str:
    """整份索引的 JSON 文本，供 Agent 或检查脚本读取。"""

    return json.dumps(
        [component.to_dict() for component in components()],
        ensure_ascii=False,
        indent=indent,
    )


def _param_text(param: Parameter) -> str:
    text = param.name
    if param.annotation:
        text += f": {param.annotation}"
    if param.default is not None:
        text += f" = {param.default}"
    return text


def render(component: Component) -> str:
    """单个控件的多行说明，供命令行直接展示。"""

    lines = [
        f"{component.name}  [{component.kind}]  {component.import_line}",
        f"  职责：{component.summary}",
        f"  何时用：{component.use}",
        f"  不要用于：{component.avoid}",
    ]
    if component.params:
        lines.append("  参数：")
        lines.extend(f"    - {_param_text(param)}" for param in component.params)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """``python -m psi6 catalog [--json] [name]``。"""

    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    args = sys.argv[1:] if argv is None else argv
    as_json = "--json" in args
    names = [arg for arg in args if not arg.startswith("-")]
    if not names:
        if as_json:
            sys.stdout.write(catalog_json() + "\n")
            return 0
        for component in components():
            sys.stdout.write(f"{component.name:<20} {component.summary}\n")
        return 0
    for name in names:
        try:
            component = find(name)
        except KeyError as exc:
            sys.stderr.write(f"{exc.args[0]}\n")
            return 2
        sys.stdout.write((catalog_json_one(component) if as_json else render(component)) + "\n")
    return 0


def catalog_json_one(component: Component) -> str:
    return json.dumps(component.to_dict(), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    raise SystemExit(main())
