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
   - 图标：与主题模块同目录的 `icons/search.svg` 覆盖 `Icon("search")`。路径相对该模块文件，不相对进程工作目录。仍可用 `register_icon`。
   - 窗壳：主窗口用 `DesktopWindow`，默认是 Qt 自带标题栏。只有用户明确要求无边框时才写 `DesktopWindow(..., frameless=True)`，那时才有自绘 `TitleBar` 和圆角。`app.run(window, tray=True)` 在系统有托盘时接到 `TrayIcon`：关窗口隐藏到托盘，菜单「退出」才结束进程。
   - 默认允许多开，也不记住窗口位置。需要时 `app.run(window, single_instance=True, restore_geometry=True)`。
   - 关窗口、点取消、应用退出是三件事，见下文「三件事」。应用退出时按「窗口几何 → `runner.shutdown()` → 单实例锁 → 隐藏托盘」收尾。
   - `tray=True` 且系统有托盘时，关窗口是隐藏，任务继续。没有托盘时，关最后一个窗口会退出进程，退出时才收尾。不要假设进程会留在后台。
   - 配置：`App.load_config` / `save_config`。设置页用 `pydantic_settings`（`field_switch(..., group="扫描")`）。
   - 父子：子控件靠 `layout.addWidget` 获得父对象。不进布局的（覆盖层、边缘热区、Toast、对话框）才写 `parent=`。从布局移除时不要 `setParent(None)`，`hide()` 后 `deleteLater()`。初始化可以 `hide()`，不要主动 `show()`；主窗口树搭完后再 `show()`。
2. **任务 `TaskRunner`**：读盘、扫目录、网络必须 `app.runner.submit`。表单、结果表、日志由页面自己放。不要手写 `QThread`，也不要做整页任务模板。

```python
def run_job(params, *, on_progress, on_log, is_cancelled) -> JobOutcome: ...
```

`handle.cancel()` 只把 `handle.cancel_requested` 设为真，不会杀掉线程。工作函数看到 `is_cancelled()` 后 `raise InterruptedError`，返回之后 `TaskHandle.status` 才变成 `cancelled`。忽略取消并正常返回时，若请求已经发出，结束状态仍是 `cancelled`。`runner.shutdown()` 超时得到 `False` 表示线程还在跑。返回 `JobOutcome(rows=..., message=...)` 只表示要填进表的结果。同一槽同时只跑一份：`runner.submit(..., exclusive="batch")`。`runner.is_busy("scan")` 查的是这个槽。进度默认 50ms 节流。`LogPanel` 默认最多 2000 条，需要纯文本时不要用它，自己接 `on_log`。合同见 `psi6.jobs.file_index`，那不是要复制的行业模板。

进度条：

- 没有明确要求放在页面哪里时，用 `from psi6.ui.status_progress import StatusProgress`，构造时传入 `window.statusBar()`。它出现在状态栏右侧，说明文字用 `showMessage` 留在左侧。`on_progress` 直接传 `progress.set_progress`，结束时 `progress.finish(message)`。
- 「开始」是页面上的主按钮，放在表单或工具区。「取消」是另一个按钮，只在任务运行时启用。不要把开始、取消和进度条排成一行。
- 只有产品明确要求进度出现在页面中间或某块区域时，才在那里放 `QProgressBar`。这种情况不要再往状态栏放一条。
3. **主题**：颜色、尺寸、时长只用 token。`base` 只选 `light` 或 `dark`。`style` 只选 `modern` 或 `compact`。不要写 `density`。文字只用标题、正文、辅助三档。自绘 `create_painter` / `rounded_rect_path` / `mix_color`，读 `token_color` / `token_int` / `token_ms`。不要 emoji、不要页面私有 QSS。动画只调时长 token；`reduced_motion: 1` 或时长 `0` 关闭。按下缩小：`install_press_scale`。对比度用 `contrast_notes(tokens)`，它只返回说明，不阻止 `Theme` 加载。结构错误（未知字段、错误的 `base` / `style`、显式图标目录不存在）才抛错。高 DPI 使用 `PassThrough`，几何是逻辑像素，图标按 `devicePixelRatio` 栅格化。悬停和按下必须能分开。禁用改颜色和边框，不只降低透明度。键盘焦点环保留。校验错误要有文字，不能只靠红框。标签不适用按下。
4. **窗壳通用件**：默认不要自绘标题栏。`frameless=True` 时才用 `TitleBar`（拖动、双击最大化、从最大化拖出还原）。`DesktopWindow.set_icon`、`TrayIcon.refresh`（换主题重绘）、`SingleInstance`（仅在 `single_instance=True` 时使用）。多页用 `AppShell` + `NavDestination`（`set_sidebar_compact`，宽度走 `token_ms`）。浅色主题画布是纯白 `color_bg`。

表单用 Pydantic + `pydantic_form` / `field_dir` / `field_file`。路径行用 `FileInput` / `FolderInput`，不要业务里直接 `QFileDialog`。用户短句用 `app.notifier`（`info` 只进状态栏）；必须看见的错误用 `fail`/`warn`；过程记录用 `LogPanel` + `LogRecord`。任务进行中 `DataTable.set_busy`。

对照窗口：`python -m psi6 kit`，侧栏按按钮、输入、选择、导航、数据、反馈、窗口分组，另有状态矩阵、四种组合和一页组合。整页参考：`python -m psi6`（文件索引）。它示范表单、开始、取消、状态栏进度、日志和结果如何拼在一起，不是要复制的行业模板。

## 新项目

复制 `skills/psi6-desktop/template/` 到应用仓库。四个文件分工固定，业务只写在 `job.py`：

| 文件 | 职责 |
| --- | --- |
| `app.py` | 创建 `App`、挂上主题、`run`。`--check` 核对主题和任务页 |
| `theme.py` | `Theme` 子类。`base` 选配色，`style` 选 modern 或 compact，其余类属性必须是 `Tokens` 字段 |
| `window.py` | 系统标题栏、开始、取消、状态栏进度、`LogPanel` |
| `job.py` | `run_job(*, on_progress, on_log, is_cancelled)`。行业逻辑只放这里 |

在模板目录执行（本仓库用已经装好的解释器，不要在模板里单独 `uv sync`，依赖要等对应版本发布）：

```powershell
python app.py --check
```

退出码 0：主题已加载，页面上有「开始」和「取消」，任务以 `succeeded` 结束。主题字段写错会在创建 `App` 时抛错。任务失败或被取消时返回 2。

## 三件事

文件索引页（`python -m psi6`）和模板任务页都按这个区分，不要合成一个「停止」：

1. **关窗口。** `close` 不调用 `cancel()`。任务保持 `running`。有托盘时窗口只是隐藏。没有托盘时，关最后一个窗口会退出进程，接着才走到下面的退出收尾。
2. **点取消。** 只对当前 `TaskHandle.cancel()`。`cancel_requested` 立即为真，`status` 等工作函数结束才变成 `cancelled`。窗口还在，进程还在。
3. **应用退出。** `aboutToQuit` 调用 `runner.shutdown()`：对未完成任务发取消并等待。超时返回 `False`，不 `terminate` 线程。

## 选择风格

普通窗口、设置页和表单用 `style = "modern"`。表格多、面板多的工具用 `style = "compact"`。浅色写 `base = "light"`，深色写 `base = "dark"`。不要再发明第三套密度。

构建时只用根包入口和 `psi6.ui` 里已有控件。表单用 `pydantic_form`，结果用 `DataTable`（空数据用它自带的空态，进行中用 `set_busy`），过程用 `LogPanel`，短错误用 `Notifier`。进度用 `StatusProgress(window.statusBar())`。

核对顺序：`python -m psi6 kit` 看状态矩阵和组合页，再跑模板的 `python app.py --check` 和仓库里的 `uv run pytest`。本机自动化只覆盖 Windows。macOS、Linux 和 150% 缩放没有跑过，不要写成已通过。

## 交互

- 默认使用 Qt 标题栏。只有明确要求无边框时才写 `frameless=True`。
- 确认框只用于需要用户决定的操作。危险操作使用 `danger_button`。
- 错误要有人能看懂的短句和下一步，不要只写「失败」。空状态用 `EmptyState`。成功、警告和失败用 `Banner` 或 `Notifier`。`info` 只进状态栏。
- 焦点顺序跟视觉顺序一致。不要覆盖系统常见快捷键。校验错误不能只靠颜色。
- 图标放在主题模块旁边的 `icons/`。绘制尺寸用 `icon_size`，默认可点区域不小于 28。
- 层次用背景和边框区分：窗口 `color_bg`，面板 `color_surface`，浮层 `color_elevated`，输入 `color_sunken`。不要靠阴影堆层次。
- 组件预览 `python -m psi6 kit` 按组件分组。主题页切换现代浅色、现代深色、紧凑浅色、紧凑深色。状态页把悬停、按下和焦点画在同一屏。

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
