---
name: psi6-desktop
description: >-
  Build Python desktop tools with the psi6 PySide6 SDK (App, TaskRunner,
  theme tokens, DesktopWindow, TitleBar, TrayIcon, StatusProgress). Use when
  creating or modifying psi6 apps, PySide6 internal tools, batch GUIs, or when
  the user mentions psi6, QThread, QFileDialog, custom title bar, tray, or
  desktop forms.
---

# psi6 桌面框架

用 `psi6` 的 **运行时、任务、主题、窗壳** 拼桌面程序，不要从 PySide6 重写基建。框架入口只从 `psi6` 导入。控件从 `psi6.ui` 的模块导入，例如 `from psi6.ui.data_table import DataTable`。不要再找整页批处理窗或任务条，页面由应用自己排。
**本仓库不提供 Excel/PDF 等业务模板，也不为某个产品堆叠首页主键。** 行业逻辑写在应用仓库；这里只提供可复用的运行时与通用壳。改外观优先构造参数，不够再子类覆盖钩子，不要改 `_` 私有实现。

## 核心（先做这些）

1. **运行时 `App`**：`App(name)` 创建应用，`app.run(window)` 进入循环。不要手写 `QApplication(sys.argv)`。
   - 主题：`App(name, theme="light"|"dark"|"auto")`，或传入 `Theme` 子类。类属性必须是 `Tokens` 字段名，写错会在加载时抛错。不要写 QSS，也不要用 JSON / TOML / YAML 描述主题。运行中 `app.set_theme(...)`。
   - 响应式密度：`App(name, density="auto")` 默认在窗口变小 / 高 DPI 时自动套用 `compact` 尺寸，`density="modern"|"compact"` 固定，运行时用 `app.set_density_mode(...)` 切换、`app.density_mode` 读当前模式。这是 **App 级策略**，不要再引入 `Theme.density`；`auto` 只收紧不放宽。`app.density_changed` 可订阅生效风格（`modern` / `compact` / `theme`）。自定义控件若构造时缓存了间距或固定宽高，提供无参 `apply_metrics()`，主题 / 密度切换时框架会广播重算。
   - 键盘焦点环：`App` 默认**不画**焦点环（`focus_ring=False`），聚焦时只抑制 Qt 原生焦点框，不改控件外观与尺寸。需要键盘可见性时传 `App(name, focus_ring=True)`，或运行时 `app.set_focus_ring(True)`；`app.focus_ring` 读状态。换主题、系统浅深色跟随、密度切换都不会重置开关。`build_stylesheet(..., focus_ring=True)` 等纯函数默认仍生成焦点环。
   - 图标：与主题模块同目录的 `icons/search.svg` 覆盖 `Icon("search")`。路径相对该模块文件，不相对进程工作目录。仍可用 `register_icon`。
   - 窗壳：主窗口用 `DesktopWindow`，默认是 Qt 自带标题栏。只有用户明确要求无边框时才写 `DesktopWindow(..., frameless=True)`，那时才有自绘 `TitleBar` 和圆角。`app.run(window, tray=True)` 在系统有托盘时接到 `TrayIcon`：关窗口隐藏到托盘，菜单「退出」才结束进程。左键在最小化时展开窗口，不把最小化再藏一次；`add_action` 在「退出」前加菜单项，`set_status` 把短状态附在提示上。`app.run(window, float_ball=True)` 另留一个置顶圆标：单击显示或隐藏主窗口，拖动换位置，右键退出。悬浮球不依赖系统托盘。圆标自己就是窗口，先摆好位置再 `show()`，不要放进页面布局。
   - 默认允许多开，也不记住窗口位置。需要时 `app.run(window, single_instance=True, restore_geometry=True)`。
   - 关窗口、点取消、应用退出是三件事，见下文「三件事」。应用退出时按「窗口几何 → `runner.shutdown()` → 单实例锁 → 隐藏托盘和悬浮球」收尾。
   - `tray=True` 且系统有托盘时，或 `float_ball=True` 时，关窗口是隐藏，任务继续。两者都没有时，关最后一个窗口会退出进程，退出时才收尾。不要假设进程会留在后台。
   - 配置分三处，不要混：进程和环境变量用应用自己的 pydantic-settings；程序参数用 `App.load_config` / `save_config`（`~/.psi6/<app>/config.json`）；上次选过的路径用 `remember_path` / `recalled_path`。设置页用 `pydantic_settings`（`field_switch(..., group="扫描")`）。窗口位置只有 `restore_geometry=True` 才写入 `window.json`，不要在 `DesktopWindow` 里自动恢复。
   - 父子：子控件靠 `layout.addWidget` 获得父对象。不进布局的（覆盖层、边缘热区、Toast、对话框）才写 `parent=`。从布局移除时不要 `setParent(None)`，`hide()` 后 `deleteLater()`。初始化可以 `hide()`，不要主动 `show()`。还没进布局时 `show()` 会先开出一个独立窗口。主窗口树搭完后再 `show()`。
2. **任务 `TaskRunner`**：读盘、扫目录、网络必须 `app.runner.submit`。表单、结果表、日志由页面自己放。不要手写 `QThread`，也不要做整页任务模板。

```python
def run_job(params, *, on_progress, on_log, is_cancelled) -> JobOutcome: ...
```

`handle.cancel()` 只把 `handle.cancel_requested` 设为真，不会杀掉线程。工作函数看到 `is_cancelled()` 后 `raise InterruptedError`，返回之后 `TaskHandle.status` 才变成 `cancelled`。忽略取消并正常返回时，若请求已经发出，结束状态仍是 `cancelled`。`runner.shutdown()` 超时得到 `False` 表示线程还在跑。返回 `JobOutcome(rows=..., message=...)` 只表示要填进表的结果。进度默认 50ms 节流，日志缓冲有锁。合同见 `psi6.jobs.file_index`，那不是要复制的行业模板。0.5 的任务、日志、表单和配置约定见下一节。

进度条：

- 没有明确要求放在页面哪里时，用 `from psi6.ui.status_progress import StatusProgress`，构造时传入 `window.statusBar()`。它出现在状态栏右侧，说明文字用 `showMessage` 留在左侧。`on_progress` 直接传 `progress.set_progress`，结束时 `progress.finish(message)`。
- 「开始」是页面上的主按钮，放在表单或工具区。「取消」是另一个按钮，只在任务运行时启用。不要把开始、取消和进度条排成一行。
- 只有产品明确要求进度出现在页面中间或某块区域时，才在那里放 `QProgressBar`。这种情况不要再往状态栏放一条。
3. **主题**：颜色、尺寸、时长只用 token。`base` 只选 `light` 或 `dark`。`style` 只选 `modern` 或 `compact`。不要写 `density`。文字只用标题、正文、辅助三档。状态色用 `color_pressed` / `color_selected` / `color_primary_hover` / `color_primary_pressed` / `color_danger_hover` / `color_danger_pressed`；留空会自动推导，不要自己混色。控件描边用 `color_control_border`，留空时等于 `color_border`，不要在 QSS 里写死描边色。自绘 `create_painter` / `rounded_rect_path` / `mix_color`，读 `token_color` / `token_int` / `token_ms`。不要 emoji、不要页面私有 QSS。动画只调时长 token；`reduced_motion: 1` 或时长 `0` 关闭。按下缩小：`install_press_scale`。对比度用 `contrast_notes(tokens)`，它只返回说明，不阻止 `Theme` 加载。检查主题用 `python -m psi6 theme <名称> --check`，`--json` 给脚本读。结构错误（未知字段、错误的 `base` / `style`、显式图标目录不存在）才抛错。高 DPI 使用 `PassThrough`，几何是逻辑像素，图标按 `devicePixelRatio` 栅格化。悬停和按下必须能分开。禁用改颜色和边框，不只降低透明度。键盘焦点环保留。校验错误要有文字，不能只靠红框。标签不适用按下。
4. **窗壳通用件**：默认不要自绘标题栏。`frameless=True` 时才用 `TitleBar`（拖动、双击最大化、从最大化拖出还原）。`DesktopWindow.set_icon`、`TrayIcon.refresh`（换主题重绘）、`SingleInstance`（仅在 `single_instance=True` 时使用）。多页用 `AppShell` + `NavDestination`（`set_sidebar_compact`，宽度走 `token_ms`）。一页内部的工具栏、面包屑和左右栏用 `Workspace`，不要再手排一列按钮当页眉。浅色主题画布是纯白 `color_bg`。旗舰方向是 Modern Desktop Workbench。色板待原型审定；审定完成前不加整套新皮肤。树表、图表、Markdown 仍随后做，不要当成永久排除。结果表行拖放用 `DataTable.set_reorderable(True)`。

## 0.5 接口

Agent 写任务、日志、表单和配置时按这里，不要再手搓线程桥、`QSettings` 或某种日志库的专用接入。

- 状态：提交后是 `queued`，工作函数开始才是 `running`。排队期间可以 `cancel()`，结束状态是 `cancelled`。`runner.started` / `runner.finished` 在界面线程给出这次的 `TaskHandle`。`handle.progress` 是最新的 `(current, total, message)`，界面上的 `on_progress` 仍按间隔合并。
- 同一槽：`runner.submit(..., exclusive="batch")`。被挡下时 `on_busy` 触发一次，不触发 `on_finished`。`runner.is_busy("scan")` 查这个槽。回调抛错不会占住槽。两个线程同时提交同一槽也只会启动一份。
- 按钮恢复：`on_finished`。成功、失败、取消都会触发。不声明参数时无参调用；声明一个位置参数时收到 `TaskHandle`。`shutdown` 之后不能再 `submit`。
- 失败：`on_failed` 只声明一个参数时仍是说明文字。第二个参数是原异常，第三个是堆栈文本，直接给 `fail(..., detail=...)`。数据错误读异常结构。
- 深层日志：`psi6.runtime.logs.task_log`。不要把 `on_log` 逐层传下去。提交线程的 `ContextVar` 会进工作线程。任务里再 `Thread()` 或 joblib `threading` 不会继承，进去之前 `capture_task_context().run(fn)`。
- 表格日志：`LogPanel`，默认可筛选，最多 2000 条。要落盘用 `LogJournal(path)`，`runner.submit(..., journal=journal)`。写盘在后台线程，结束时 `journal.close()`。不要把 journal 再当作 `on_log`，否则同一条会写两遍。
- 配置迁移：旧 JSON 用 `ConfigMigrations`。`add(0, step)` 把没有 `version` 的文件升到 1，再传给 `load` / `load_data` 的 `migrate=`。迁移失败会备份原文件并退回默认值。
- 快捷键：`ShortcutBook(window)`，同一序列只登记一次。菜单里的 `shortcut` 仍只是提示。命令面板 `palette.install(window)`，或传入同一本 `ShortcutBook`。撤销用 `EditHistory`，`push(label, apply=, revert=)` 立刻执行 `apply`，`install(window)` 接 Ctrl+Z / Ctrl+Y / Ctrl+Shift+Z。焦点在输入框里时，这些键仍留给输入框。
- 结果表换序：`DataTable.set_reorderable(True)` 后可拖动一行，改变 `rows()` 的原始顺序。有排序或筛选时拖动无效。`set_history(history)` 后这次移动可以撤销；`set_rows` / `clear` 会使旧的撤销步骤失效。
- 终端日志：`from psi6.ui.log_console import LogConsole`，然后 `logger.addHandler(console.handler())`。颜色用主题 token。其它日志库先送进标准库 `logging`。
- 表单回填：`form.restore(model)`，与 `set_model` 相同，期间挡住子控件信号。
- 路径：`FileInput` / `FolderInput`。`path_changed` 每次按键都发，用来即时校验。保存接 `path_edited`（编辑结束、浏览、拖放、清除）。`clearable=False` 关掉清除按钮。多个路径用分号分隔，路径本身不要含 `;`。不要在业务里直接 `QFileDialog`。
- 配置分三处：进程和环境变量用应用自己的 pydantic-settings；程序参数用 `load_config` / `save_config`；上次路径用 `app.remember_path` / `app.recalled_path`，失效路径自动清掉。窗口几何只有 `restore_geometry=True` 才写入 `window.json`。

用户短句用 `app.notifier`（`info` 只进状态栏）；必须看见的错误用 `fail`/`warn`。任务进行中 `DataTable.set_busy`。

对照窗口：`python -m psi6 kit`。侧栏仍按控件分组，另有壳、表单、检查、密度和组合。主题页只切换浅色、深色和密度。整页参考：`python -m psi6`（文件索引，工具栏加结果与日志分栏）。它示范任务怎么接，不是要复制的行业模板。结果表排序用 `DataTable.sort_by` 或点击表头；排序和筛选会保留选中行与滚动位置。双击读 `record_activated` 拿记录副本，需要可见行号再接 `row_activated`。表单分组写 `json_schema_extra={"group": "扫描"}`，选项可搜索写 `{"search": True}`。

## 新项目

复制 `skills/psi6-desktop/template/` 到应用仓库。四个文件分工固定，业务只写在 `job.py`：

| 文件 | 职责 |
| --- | --- |
| `app.py` | 创建 `App`、挂上主题与响应式密度（默认 `density="auto"`）、`run`；焦点环默认关闭，`--check` 核对主题和任务页 |
| `theme.py` | `Theme` 子类。`base` 选 `light`/`dark`/`auto`，`style` 选 modern 或 compact，其余类属性必须是 `Tokens` 字段 |
| `window.py` | 系统标题栏、`Workspace` 工具栏里的开始和取消、状态栏进度、`LogPanel` |
| `job.py` | `run_job(*, on_progress, on_log, is_cancelled)`。行业逻辑只放这里 |

在模板目录执行（本仓库用已经装好的解释器，不要在模板里单独 `uv sync`，依赖要等对应版本发布）：

```powershell
python app.py --check
```

退出码 0：主题已加载，页面上有「开始」和「取消」，任务以 `succeeded` 结束。主题字段写错会在创建 `App` 时抛错。任务失败或被取消时返回 2。

## 三件事

文件索引页（`python -m psi6`）和模板任务页都按这个区分，不要合成一个「停止」：

1. **关窗口。** `close` 不调用 `cancel()`。任务保持 `running`。有托盘或悬浮球时窗口只是隐藏。两者都没有时，关最后一个窗口会退出进程，接着才走到下面的退出收尾。
2. **点取消。** 只对当前 `TaskHandle.cancel()`。`cancel_requested` 立即为真，`status` 等工作函数结束才变成 `cancelled`。窗口还在，进程还在。
3. **应用退出。** `aboutToQuit` 调用 `runner.shutdown()`：对未完成任务发取消并等待。超时返回 `False`，不 `terminate` 线程。

## 选择风格

普通窗口、设置页和表单用 `style = "modern"`。表格多、面板多的工具用 `style = "compact"`。浅色写 `base = "light"`，深色写 `base = "dark"`。跟着系统切换写 `base = "auto"`：给 `light` 和 `dark` 各配一个 `Theme`（或 `Tokens`）当变体，本类显式写的 `style` 和 token 覆盖压在变体上；没写变体就把本类覆盖套到系统底色上。变体自己的 `base` 不能再是 `auto`。不要再发明第三套密度。

主题切换用 `app.set_theme("light" / "dark" / "auto" / 主题名 / Theme / Tokens)`。要记住用户选过什么，写 `App(..., remember_theme=True)`：选择进 `theme.json`，下次启动覆盖 `theme` 参数。配置里只存名字，所以能恢复的只有注册过的主题（内置主题、`theme_choices`、`theme` 与 `set_theme` 用过的 `Theme`）；`Tokens` 没有名字，不写进配置。`app.theme_name` 读当前标识。

自绘控件在 `changeEvent` 里跟 `PaletteChange` 与 `StyleChange`，颜色只在绘制时从 `token_color` 取。`Sparkline`、`Switch`、`TitleBar`、`LogConsole` 已经这么做；把配色写进文档或缓存的控件必须自己重画。

构建时只用根包入口和 `psi6.ui` 里已有控件。表单用 `pydantic_form`，结果用 `DataTable`（空数据用它自带的空态，进行中用 `set_busy`），过程用 `LogPanel`，短错误用 `Notifier`。进度用 `StatusProgress(window.statusBar())`。

核对顺序：`python -m psi6 kit` 看状态矩阵和组合页，再跑模板的 `python app.py --check` 和仓库里的 `uv run pytest`。本机自动化只覆盖 Windows。macOS、Linux 和 150% 缩放没有跑过，不要写成已通过。

## 交互

- 默认使用 Qt 标题栏。只有明确要求无边框时才写 `frameless=True`。
- 确认框只用于需要用户决定的操作。危险操作使用 `danger_button`。
- 错误要有人能看懂的短句和下一步，不要只写「失败」。空状态用 `EmptyState`。成功、警告和失败用 `Banner` 或 `Notifier`。`info` 只进状态栏。
- 焦点顺序跟视觉顺序一致。不要覆盖系统常见快捷键。校验错误不能只靠颜色。焦点环默认关闭；纯键盘操作 / 无障碍要求高的界面显式开 `focus_ring=True`，不要为了「看得见焦点」自己写 `:focus` 内联 QSS。
- 图标放在主题模块旁边的 `icons/`。绘制尺寸用 `icon_size`，默认可点区域不小于 28。
- 层次用背景和边框区分：窗口 `color_bg`，面板 `color_surface`，浮层 `color_elevated`，输入 `color_sunken`。悬停用中性 `color_hover`。持久选中用强调色浅底。实心强调色留给主按钮和焦点。不要靠阴影堆层次。
- 组件预览 `python -m psi6 kit` 按组件分组。主题页切换现代浅色、现代深色、紧凑浅色、紧凑深色，并可开关焦点环（组件目录为展示焦点态显式开启）。状态页把悬停、按下和焦点画在同一屏。

## 验证

在仓库里：

```powershell
uv run pytest
uv run python -m psi6.examples.minimal --check
uv run python -m psi6.examples.task_job --check
uv run python -m psi6.examples.custom_theme --check
uv run python -m psi6.examples.task_status --check
```

`--check` 返回 0 表示示例能启动并退出。模板检查见上一节。迁移见仓库根目录 `MIGRATION.md`。

选控件前先查索引，不要凭记忆猜导入路径：

```powershell
python -m psi6 catalog          # 全部控件一行一个
python -m psi6 catalog --json   # 名称、导入位置、构造参数、适用场景、替代关系
python -m psi6 catalog DataTable
```

业务仓库提交前跑规范检查。它用 AST 找直接创建 `QApplication`、手写 `QThread`、直接调用 `QFileDialog`、内联 QSS、`processEvents` 和私有模块导入；`as` 别名按原名字判断，路径不存在或不是 `.py` 文件时报 `PSI007`。模板的 `--check` 已经内置：

```powershell
python -m psi6 check .
python -m psi6 check . --exclude src/vendor
```

## 页面控件（按需，不要当成产品主线）

| 需求 | 用 |
| --- | --- |
| 主按钮 / 危险 / 幽灵 / 文字链 | `primary_button` / `danger_button` / `ghost_button` / `text_button` |
| 分区 / 空态 / 筛选 / 状态 | `Section` / `EmptyState` / `SearchField` + `DataTable.set_filter` / `StatusBadge` |
| 设置开关 | `Switch` / `SettingRow` / `field_switch` |
| 页内提示 | `Banner`（`actions=` 最多两个） |
| 工具行 / 页头 | `ActionBar` / `PageHeader` / `StatCard` |
| 类型芯片 / 换行 | `Tag` / `TagRow` / `FlowLayout` |
| 高级字段 | `field_advanced` → `Collapsible` |
| 拖放热区 / 分段 / 清单 | `DropZone` / `SegmentedControl` / `CheckList` |
| 带主体的对话框 | `ContentDialog`（短句仍用 `confirm` / `fail` / `inform`） |
| 图标缩略图 | `ImageWell`（底层 `FileInput`） |
| Agent 对话 | `MessageList` + `Composer` |
| 命令面板 / 分步 | `CommandPalette` / `Stepper` |
| 自定义控件 | 参数 → 子类钩子 → 自绘读 token。不要私有 QSS，不要在 psi6 里加业务模板 |

## 禁止

- UI 线程做文件扫描、IO、HTTP
- 每个任务一个 `QThread` 子类，或 `QThread.terminate()` / `processEvents()` 假装异步
- 页面私有大段 QSS，或复制一套浅色/深色皮肤
- 复制 `LogPanel` / `Section` / `EmptyState` 自己做一套，或把进度条和开始、取消按钮焊在同一行
- 把 loguru 诊断日志和操作日志混在一个控件
- 为了改一行业务逻辑去改 `psi6.ui._path_picker` 等私有模块
- 用 emoji 当图标，或引入另一套图标字体
- 为换皮肤复制整份 QSS；只覆盖 token
- 在 psi6 里加 Excel/PDF/合并导出等业务模板，或为某个打包器/构建器堆叠首页主键

## QSS 坑（只在 `psi6.theme.apply` 这一处写 QSS）

- **大样式表丢弃窗口 ≈ 7 条顶层规则**：在 `build_stylesheet` 这种全局大表里，`QPushButton#psi6X` 这类 ID 规则只要落在通用 `QPushButton` 规则之后**超过约 7 条顶层规则**，就会被 Qt 的 QSS 引擎**静默丢弃**（不报错）。通用 `:hover/:pressed/:disabled/:focus` 四条已占 4 个槽位，再多塞 ID 组就装不下。插入空 `QPushButton {}` 或带声明的完整 `QPushButton {...}` 都**无法重置**这个窗口。
- **后果**：想靠"把 8 组主题按钮规则集中到通用 `QPushButton` 旁边"来修样式是行不通的，它们永远退化为普通次级按钮外观。
- **正解**：主题按钮必须用**按控件 `setStyleSheet`**（`psi6.ui` 控件构造时调 `apply_psi6_button_stylesheet` 里的 `apply_psi6_button_style`），独立解析、不受全局层叠丢弃影响；主题切换由 `PaletteChange` 事件过滤器重新套用。`apply.py` 已封装好这些，新主题按钮照抄即可。
- **顶层 `#` 行注释会吞掉其后所有规则**：QSS 只认 `/* */`。f-string 里写 `# 说明` 会被当成坏 ID 选择器，导致该行之后全部规则失效（连前面的规则都退化）。注释一律用 `/* ... */`，或移到 f-string 之外。
- **纯 `QWidget` 子类要 `WA_StyledBackground`**：不设该属性时 QSS 的 `background`/`border` 不绘制（横幅底色会一直是空的）。凡是挂了带背景/边框全局规则的 `QWidget` 子类（`Banner`/`EmptyState`/`ActionBar`/…），`__init__` 里都加 `self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)`。
- **原生焦点框（PE_FrameFocusRect）与 QSS 焦点环叠加 = 双框**：`QPushButton`（以及 `QLineEdit`/`QTabBar::tab`/`QToolButton` 等）获得键盘焦点时，Fusion 会通过 QSS 的 `outline` 属性画一圈 1px 浅灰框（`PE_FrameFocusRect`）。这圈原生灰框会叠在 psi6 自己用 `border` 画的彩色焦点环**内侧**，看起来像"浅色内部线条/方框"。**正解**：在每个 `:focus` 规则里加 `outline: none;`（见 `apply.py` 全部 `:focus` 规则都已加）。注意这和"不要用 outline 画焦点环"（第九轮教训，outline 在内容矩形内画框、压住文字）是两回事——`outline: none` 是**关掉**原生框，用法正确且必需。
- **`setStyleSheet` 会重置底层 style，`QProxyStyle` 套不进去**：想用 `QProxyStyle` 包一层 `Fusion`（比如 `drawPrimitive(PE_FrameFocusRect)` 直接 return 来消原生焦点框）在 psi6 里基本无效——`QApplication.setStyleSheet(...)` 内部会用**默认** style 重建 `QStyleSheetStyle`，把之前 `setStyle` 装的代理风格丢掉，且设置过 stylesheet 后再次 `setStyle` 也会被忽略。所以消原生焦点框只能靠 QSS 的 `outline: none`，不要指望 `QProxyStyle`。
- **offscreen 渲染看不到原生焦点框**：`QT_QPA_PLATFORM=offscreen` 下 Qt 不画 `PE_FrameFocusRect`，所以离屏 `grab()`/`render()`（以及 `psi6-theme-visual-check` 出图）永远干净——但真实平台上用户照样能看到那圈灰框。验证"原生焦点框是否消除"必须在**真实显示平台**抓图，离屏只能验证 QSS 彩色环本身。
