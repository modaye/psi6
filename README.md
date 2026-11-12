# psi6

给编码 Agent 用的 PySide6 桌面框架：运行时、后台任务、Python 主题与窗口外壳。新窗口用 `Workspace` 放工具栏、面包屑和左右栏（栏可显隐，布局可持久化）；多份文档用 `TabView` 的标签页；结果用 `DataTable` 排序筛选；参数用 `pydantic_form`，校验错误留在字段下；侧栏换页用 `AppShell`。

> **状态**：0.6.0。根包公开入口（`psi6.api.STABLE`）在 0.x 内职责不变；控件层（`psi6.ui`）可用但不逐个承诺稳定级别。色板与部分 token **尚未冻结**，主题相关字段可能随版本微调。详见「稳定边界」。

## 要求与支持平台

- **Python**：≥ 3.13
- **依赖**：`pyside6>=6.8`、`pydantic>=2.11`（Qt 是较大的二进制依赖，首次安装会拉取对应平台的 wheel）
- **已验证**：Windows 本机，常规 DPI
- **待补验证**：macOS、Linux，以及高 DPI（150%+）缩放——交互与视觉尚未在这些环境完整跑过。CI 已在三平台执行 wheel 冒烟测试，但功能/视觉验证待补。

## 安装

```powershell
pip install psi6
python -m psi6 kit
```

## 5 分钟快速开始

```python
from psi6 import App, DesktopWindow
from psi6.ui.buttons import primary_button, ghost_button
from psi6.ui.workspace import Workspace
from psi6.ui.data_table import DataTable

app = App("demo")
window = DesktopWindow(title="演示")
work = Workspace()
work.set_crumbs(["文件", "索引"])
work.toolbar.add_primary(primary_button("开始"))
work.toolbar.add_secondary(ghost_button("取消"))
table = DataTable(("name", "value"))
table.set_rows([{"name": "记录", "value": 1}])
work.set_pane("center", table)
window.set_body(work)
raise SystemExit(app.run(window))
```

开始和取消是分开的按钮。进度没有指定位置时，用 `StatusProgress(window.statusBar())`。不要把开始、取消和进度排成一行。

组件目录里先看 **壳**、**检查**、**密度**。`python -m psi6` 打开文件索引，用来看开始、取消、状态栏进度和日志怎么接在一起，不是要复制的行业模板。

`python -m psi6 catalog --json` 输出全部公开控件、构造参数和适用场景，Agent 不必读源码就能选控件。`python -m psi6 check <目录>` 检查业务代码有没有直接创建 `QApplication`、手写 `QThread`、调用 `QFileDialog` 或写内联 QSS。`python -m psi6 theme --check` 检查内置主题的对比度，`--json` 输出 token 和诊断。

浅色和深色是同一套语言。`style` 只选 `modern` 或 `compact`。具体色值还没冻结。

## 稳定边界（0.6.0）

- 根包只导出 `psi6.api.STABLE` 名单：`App`、`TaskRunner`、`TaskHandle`、`TaskStatus`、`JobOutcome`、`Theme`、`Tokens`、`contrast_notes`、`DesktopWindow`、`TitleBar`、`TrayIcon`。0.x 内职责不变，新增参数带默认值。其它控件从 `psi6.ui` 导入。
- 以 `_` 开头的模块是内部实现，不要直接依赖。
- 主题 `Tokens` 的字段名与 `Theme` 子类接口是稳定契约，但具体色值在 0.6 阶段仍可能调整（色板未冻结）。
- 破坏性变更写入 `MIGRATION.md` 并升一个次版本。

## 一页窗口

默认用 Qt 标题栏。只有明确要求无边框时才传 `frameless=True`。

```python
from psi6 import App, DesktopWindow
from psi6.ui.buttons import ghost_button, primary_button
from psi6.ui.data_table import DataTable
from psi6.ui.workspace import Workspace

app = App("demo")
window = DesktopWindow(title="演示")
work = Workspace()
work.set_crumbs(["文件", "索引"])
work.toolbar.add_primary(primary_button("开始"))
work.toolbar.add_secondary(ghost_button("取消"))
table = DataTable(("name", "value"))
table.set_rows([{"name": "记录", "value": 1}])
work.set_pane("center", table)
window.set_body(work)
raise SystemExit(app.run(window))
```

开始和取消是分开的按钮。进度没有指定位置时，用 `StatusProgress(window.statusBar())`。不要把开始、取消和进度排成一行。

参数表由模型生成。`group` 出分组标题，`search` 让选项可以输入筛选。控件能接受的值仍以模型校验为准，错误文字留在该字段下。

```python
from pydantic import BaseModel, Field
from psi6.ui.form import pydantic_form

class Scan(BaseModel):
    count: int = Field(
        default=1,
        gt=0,
        le=10,
        description="数量",
        json_schema_extra={"group": "扫描"},
    )

form = pydantic_form(Scan)
```

## 后台任务

界面只展示，执行在 `TaskRunner`。`cancel()` 只发出请求，结束看 `TaskHandle.status`。关掉窗口不会取消任务，应用退出时才收尾。

```python
def run_job(*, on_progress, is_cancelled) -> str:
    on_progress(1, 1, "完成")
    if is_cancelled():
        raise InterruptedError
    return "ok"

handle = app.runner.submit(
    run_job,
    on_succeeded=lambda value: None,
    on_failed=lambda message: None,
)
handle.cancel()
```

同一槽还在跑时，用 `exclusive="batch"`。被挡下走 `on_busy`，按钮恢复走 `on_finished`。`on_failed` 可以只接说明文字，也可以再接原异常和堆栈（第三参数）。工作函数任意深度写日志用 `psi6.runtime.logs.task_log`。提交线程上的 `ContextVar` 会进这次任务；任务里再开的线程用 `psi6.runtime.logs.capture_task_context().run(fn)`。

日志有两种。要筛选用 `LogPanel`。要接到标准库 logging：

```python
import logging
from psi6.ui.log_console import LogConsole

console = LogConsole()
logging.getLogger("myapp").addHandler(console.handler())
```

`LogConsole` 把记录留在控件里，切换主题时整片按新配色重画。

## 主题

主题是 `Theme` 的子类。`base` 选 `light`、`dark` 或 `auto`，`style` 选 `modern` 或 `compact`。其余类属性必须是 `Tokens` 的字段，写错会在加载时抛错。对比度不足只返回说明，不阻止加载。

```python
from psi6 import Theme, contrast_notes

class Desk(Theme):
    name = "desk"
    base = "light"
    style = "compact"

app = App("demo", theme=Desk)
contrast_notes(app.tokens)
```

`base = "auto"` 跟随系统浅色/深色。给出 `light` / `dark` 两个变体时配色取当前方案那一份，本类显式写的 `style` 和 token 覆盖压在它上面：

```python
class Desk(Theme):
    name = "desk"
    base = "auto"
    light = DeskLight   # Theme 子类、实例或 Tokens
    dark = DeskDark
    style = "compact"
```

`App` 收到系统方案变化时，`"auto"` 和这类主题对象都会重套；`base` 固定为 `light` / `dark` 的主题不受影响。

状态色不必逐个写。`color_pressed`、`color_selected`、`color_primary_hover`、`color_primary_pressed`、`color_danger_hover`、`color_danger_pressed` 留空时由基础色推导：按下比悬停对比更强，选中是主色的浅底。只改 `color_primary` 也会得到配套的悬停和按下色；需要特殊效果时再写值覆盖。

与主题模块同目录的 `icons/search.svg` 会覆盖同名图标。`psi6.theme.builtin_themes()` 列出随包提供的主题。`python -m psi6 theme` 列出主题，`python -m psi6 theme obsidian --check` 检查对比度（退出码 0 无问题、1 有诊断、2 无法加载），加 `--json` 输出全部 token 与诊断。自定义主题用 `模块:类名`。

## 默认行为

默认可以多开，也不写窗口位置。需要时再打开：

```python
app.run(window, tray=True, single_instance=True, restore_geometry=True)
```

配置分四处：进程和环境变量用应用自己的 pydantic-settings；程序参数用 `load_config` / `save_config`；上次路径用 `remember_path` / `recalled_path`；主题选择只有 `App(..., remember_theme=True)` 才写 `theme.json`。表单回填用 `form.restore(model)`，期间不逐字段发信号。路径保存接 `path_edited`，即时校验才用 `path_changed`。多个路径用分号分隔。

配置文件损坏时用模型默认值。窗口几何损坏时保持调用方给的尺寸。系统没有托盘时，`tray=True` 不阻止关闭窗口和退出进程。`float_ball=True` 会在屏幕上留一个可拖动的圆标，关闭主窗口改为隐藏，单击圆标再打开。

## 主题选择

运行中切换用 `set_theme`，`theme_name` 读当前标识。字符串既可以是方案，也可以是注册过的主题名。

```python
app.set_theme("auto")        # light / dark / auto
app.set_theme("obsidian")    # 内置主题名
app.set_theme(MyBrand)       # Theme 类会自动登记名字

App("demo", theme="light", theme_choices=[MyBrand, Mono])
```

`remember_theme=True` 时 `set_theme` 把名字写进 `theme.json`，下次启动覆盖 `theme` 参数。可恢复的只有注册过的主题（内置主题、`theme_choices`、`theme` 与 `set_theme` 用过的 `Theme`）；`Tokens` 没有名字，不写配置。`theme.json` 被改成认不出的名字时记一行 warning，用默认主题。

## 响应式密度

配色和尺寸分开：`Theme.base` / `Theme.style` 是静态主题，`density` 是 **`App` 级的运行时策略**——不新增 `Theme.density`，也不往 `Tokens` 里加字段。

```python
App("demo", theme="light", density="auto",
    compact_max_width=760, compact_max_height=540)

app.density_mode                  # "auto" / "modern" / "compact"
app.set_density_mode("compact")   # 手动固定；传 "auto" 交回窗口判定
app.density_changed.connect(on_density_changed)
```

`density_changed` 的参数是**当前生效的尺寸风格**：`compact`、`modern`，或 `theme`（`auto` 且空间充足，沿用主题自带尺寸）。手动切换和窗口 Resize 触发的自动翻转都会发；换主题、跟随系统浅深色不发。

- `auto`（默认）：主窗口逻辑宽 < `compact_max_width` 或高 < `compact_max_height` 时，把 `compact` 尺寸预设压到当前主题上；`devicePixelRatio() >= 2` 时阈值乘 1.25 更容易收紧。Resize 去抖 120ms，只在生效密度真正翻转时重套主题。
- **只收紧、不放宽**：空间充足时沿用主题自带尺寸，显式选了紧凑主题或写了自定义度量的主题不会被悄悄改掉；只有手动 `modern` 会主动放宽。密度在主题解析末尾叠加，所以 `set_theme` 与系统浅深色跟随之后仍然生效。
- `apply_theme` 除了重设 QSS，还会广播 `apply_metrics()`：遍历所有控件及整棵布局树，让构造时缓存了间距 / 固定宽高的控件和自定义 `QLayout`（收不到 `StyleChange`）跟着重排。自定义控件只要提供**可无参调用**的 `apply_metrics()` 就会被自动刷新；签名不合约定或单个 hook 抛错只跳过它，不影响其它控件。
- `psi6.theme.style_metrics("compact")` 返回某风格全部尺寸预设的副本；`psi6.theme.runtime.metrics_scale()` 给出当前控件高度相对 `modern` 的比例（钳在 0.5 ~ 2.0），用来缩放没有对应 token 的硬编码留白。
- 组件目录「主题」页有 自动 / 宽松 / 紧凑 三个手动按钮，状态随 `density_changed` 更新。

## 键盘焦点环

焦点环默认**关闭**：`App` 应用里 Tab 聚焦不画彩色环，控件边框、间距和高度完全不变，只用 `outline: none` 抑制 Qt 原生焦点框。需要键盘可见性（纯键盘操作、无障碍需求）时显式开启：

```python
App("demo", theme="light", focus_ring=True)

app.focus_ring               # False / True
app.set_focus_ring(True)     # 运行时开关，立即重套主题
```

开关同时作用于全局 QSS 和「按控件样式化」的 8 组主题按钮；`set_theme`、系统浅深色跟随、响应式密度切换都不会重置它。`build_stylesheet(tokens, focus_ring=True)` 与 `psi6_button_stylesheet(kind, tokens, focus_ring=True)` 两个纯函数默认仍生成焦点环，方便单独预览与测试。

组件目录 `python -m psi6 kit` 为展示「状态矩阵」页的焦点态显式开启，并在「主题」页提供 关闭 / 开启 两个按钮，可现场对比。

## 多视图文档与面板布局

`TabView` 管一页里的多份文档，`Workspace` 管这一页的分栏；两者的布局都能持久化到应用数据目录。

```python
from PySide6.QtWidgets import QLabel
from psi6.runtime.config import ConfigStore
from psi6.ui.tab_view import TabView
from psi6.ui.workspace import Workspace

store = ConfigStore()  # 测试可传临时目录：ConfigStore(tmp_path)
work = Workspace()
tabs = TabView()                     # 可关闭、可拖动重排，全关掉显示空态
tabs.add_tab("readme", "说明", QLabel("说明"))
tabs.add_tab("diff", "变更", QLabel("变更"))
work.set_pane("left", QLabel("导航"))
work.set_pane("center", tabs)
work.set_pane("right", QLabel("属性"))
work.set_pane_visible("right", False)  # 隐藏只是摘下来，控件保留

# 退出前
tabs.save_state(store, "demo")
work.save_state(store, "demo")

# 下次启动：先用 add_tab 把控件放回来，再恢复顺序与当前项
tabs.restore_state(store, "demo")
work.restore_state(store, "demo")
```

- `TabView.state()` 只记 `keys` 顺序和 `current`，**不记控件**：状态里出现但没有对应控件的 key 会被忽略，当前多出来的标签追加到末尾，文件里少写几个 key 也丢不掉已打开的文档。`close_tab` 把控件交还调用方（`setParent(None)`，不销毁），需要复用就自己留引用。
- `Workspace.state()` 记 `hidden` / `sizes` / `dragged`。宽度按 **栏名** 而不是下标保存，隐藏一栏后再恢复不会让其余栏的宽度串位；拖动释放后发 `layout_changed`，`set_pane_visible` 改变显隐时也发。
- 两者都只做分栏与标签，**不提供 `QDockWidget` 浮动窗口或自由停靠**；文件不存在、损坏或字段类型不对时安全跳过，布局保持原样。
- 布局写进 `tabs.json` / `layout.json`，与窗口几何的 `window.json` 分开；文件名可用构造参数 `state_file` 覆盖。

## 右键上下文菜单

`DataTable` / `TreeView` / `TabView` 都支持右键菜单。用 `MenuAction` 描述项，菜单回调能拿到右键命中的行、节点或页签：

```python
from psi6.ui import MenuAction, MenuTarget

def row_menu(target: MenuTarget) -> list[MenuAction]:
    if not target.hit:
        return []
    row = target.data          # 命中行的副本
    return [
        MenuAction("打开", lambda: open_row(row), icon="external-link"),
        MenuAction("复制路径", lambda: copy_path(row), shortcut="Ctrl+C"),
        MenuAction.line(),
        MenuAction("删除", lambda: delete_row(row), dangerous=True),
    ]

table.context_menu(row_menu)
```

- `MenuAction` 支持 `icon`（按当前 token 着色，换肤自动重画）、`shortcut`（菜单里只显示文字；真正按键用下面的 `ShortcutBook`，避免同一动作在多个菜单里各注册一遍）、`dangerous`（用错误色画图标）、`checked` + `group`（同组自动互斥）、`separator=True`。
- `MenuTarget` 带 `kind`（`table` / `tree` / `tabs`）、`key`（可见行号 / 节点 id / 页签 key）、`data`（行副本 / `TreeNode` / 标题）、`hit`（右键是否落在真实条目上）。
- 右键落在**未选中**的行 / 节点 / 页签上会先选中它，菜单里的「选中项」才和行为一致。
- `data` 是命中时的**快照**，别把它存下来当状态用；要长期状态请用 `select_row` / `select_node` / `set_current`。
- 自己控制弹出时机（托盘、标题栏）时用 `build_menu(actions, host=...)`。

## 列管理

按 ADR 0003 的约定，列管理**单独成控件**，不塞进 `DataTable`。`DataTable` 只提供四个读写口：

```python
from psi6.ui import ColumnPicker

table.columns()               # 全部列（含标题）
table.visible_columns()       # 当前可见列的 key，按显示顺序
table.set_visible_columns(["id", "name"])   # 隐藏其余列
table.column_menu(build)      # 给列头挂右键菜单，target.kind == "columns"

picker = ColumnPicker()
picker.set_columns(table.columns())
picker.columns_changed.connect(table.set_visible_columns)
```

- **显隐走视图层**（`setColumnHidden`），不改 `_columns`，所以 `cell_text(row, column)` 的列号语义不受影响；只有**调序**才重排 `_columns`。
- `required=True` 的列（通常是主键）不可隐藏，勾选框被禁用。
- **数据刷新后显隐与顺序仍在**：`set_rows` 重建列时不覆盖列管理设过的状态。
- 列头右键用 `column_toggle_menu(columns, visible, on_toggle=...)` 就地勾选，完整面板才用 `ColumnPicker`，两者共享同一份状态。
- `state()` / `set_state()` / `save_state()` / `restore_state()` 持久化到 `ConfigStore`（默认 `columns.json`）；`set_state` 只按文件里出现的 key 重排，文件没提到的列留在原位。

## 常用配方

- **表单 + 结果表 + 日志**：`pydantic_form` 接模型，`DataTable` 接结果，`LogConsole` / `LogPanel` 接日志，三者各自独立、靠回调串起来。
- **几万行的结果表**：`DataTable` 只存一份行数据，筛选和排序只重排**原始行索引**（无操作时是 `range`，零拷贝），视图通过 `fetchMore` 首屏发布 512 行、之后每批 256 行按需取，不用自己写分页或虚拟滚动。`visible_rows()` / `selected_rows()` / `cell_text()` 仍按全部可见行工作，排序和筛选保留选中行、当前行与滚动位置。
- **托盘驻留**：`app.run(window, tray=True)`；没有系统托盘时关闭最后一个窗口即退出进程。左键在窗口最小化时展开它。`add_action` 在「退出」前加自己的菜单项，`set_status` 把短状态写进提示。
- **悬浮球**：`app.run(window, float_ball=True)`。圆标置顶，不放进页面布局；拖动换位置，单击显示或隐藏主窗口，右键退出。不依赖系统托盘。`set_status` 在圆标右下角加一个主色点。
- **单实例**：`single_instance=True` 加锁，重复启动只激活已有窗口。
- **记住几何与路径**：`restore_geometry=True` 读写窗口几何；`remember_path` / `recalled_path` 记界面路径到 `QSettings`。
- **键盘焦点环**：默认关闭，聚焦不改外观与尺寸；需要键盘可见性时用 `App(..., focus_ring=True)` 或 `app.set_focus_ring(True)` 开启（见上一节）。
- **一次打开多份文档 + 记住面板布局**：`TabView` 按 `key` 复用控件、可关闭可重排，`Workspace.set_pane_visible` 显隐栏，两者用 `save_state` / `restore_state` 把标签顺序与分栏显隐宽度写进 `ConfigStore`（见上一节）。
- **结果表的右键操作**：`table.context_menu(builder)`，回调里用 `target.data` 拿行、用 `target.key` 拿可见行号（见上一节）。
- **让用户自己选看哪几列**：`ColumnPicker` 接 `DataTable.columns()`，勾选显隐、上下调序，`columns_changed` 直接接 `set_visible_columns`，`save_state` / `restore_state` 记住选择（见上一节）。

## 示例

先打开**示例画廊**挑一个用例，像 web UI 那样看 psi6 能拼出什么：

```powershell
python -m psi6 gallery
```

画廊按「入门 / 数据与任务 / 组件 / 场景」分组列出用例卡片，点开即用；右上角切换浅色 / 深色 / 紧凑，所有已开窗口一起换肤。三个「场景」用例（数据看板、偏好设置、即时对话）演示组件怎么拼成真实界面。

安装后可单独核对各示例能否启动：

```powershell
python -m psi6.examples.minimal --check
python -m psi6.examples.task_job --check
python -m psi6.examples.custom_theme --check
python -m psi6.examples.task_status --check
```

`python -m psi6 kit` 打开组件与主题预览；`python -m psi6 file_index` 看开始/取消/状态栏进度/日志如何组合在一个窗口里。

关窗口、点取消、应用退出是三件事。

## 故障排查

- **主题 / 样式不生效**：只从 `psi6` 根包或 `psi6.ui` 公开模块导入；不要从 `_` 私有模块导入，也不要在页面里写内联 QSS（`python -m psi6 check` 会报 PSI005 / PSI004）。全局大样式表里 `QPushButton#psi6X` 这类 ID 规则落在通用 `QPushButton` 之后过远会被静默丢弃——主题按钮一律用按控件 `setStyleSheet`，不要往全局表塞。
- **焦点出现浅色内框**：Qt 原生焦点框（`PE_FrameFocusRect`）与 QSS 焦点环叠加会产生浅色内框，主题里用 `outline: none` 消除；焦点环关闭时这条也保留。注意 `QT_QPA_PLATFORM=offscreen` 不画原生焦点框，验证要在真实显示平台抓图。
- **高 DPI 模糊**：图标按 `devicePixelRatio` 栅格化；高 DPI 在 Windows 已验证，其他平台待补。

## 开发

```powershell
uv sync --extra dev
uv run pytest
uv run pytest --cov=psi6   # 覆盖率低于 80% 会失败
uv run ruff check .
uv run mypy
```

## 许可证

MIT，见 [`LICENSE`](LICENSE)。

## 接着看

| 文档 | 内容 |
| --- | --- |
| [`skills/psi6-desktop/SKILL.md`](skills/psi6-desktop/SKILL.md) | Agent 写窗口时要遵守的约定 |
| [`skills/psi6-desktop/template/`](skills/psi6-desktop/template/) | 新项目复制这里，在该目录执行 `python app.py --check` |
| [`docs/components.md`](docs/components.md) | 这一阶段常用的 `psi6.ui` 控件清单 |
| [`docs/adr/0003-workbench.md`](docs/adr/0003-workbench.md) | 旗舰方向。色板等三个原型的真实窗口通过后再冻结 |
| [`docs/adr/0002-roadmap.md`](docs/adr/0002-roadmap.md) | 0.5 / 0.6 的发布门禁与路线 |
| [`MIGRATION.md`](MIGRATION.md) | 升级时要改的调用 |
| [`CHANGELOG.md`](CHANGELOG.md) | 破坏性变更与版本说明 |
