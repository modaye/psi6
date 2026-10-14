---
name: psi6-desktop
description: >-
  Build Python desktop tools with the psi6 PySide6 SDK (App, TaskRunner,
  theme tokens, DesktopWindow, TitleBar, TrayIcon, BatchToolWindow). Use when
  creating or modifying psi6 apps, PySide6 internal tools, batch GUIs, or when
  the user mentions psi6, QThread, QFileDialog, custom title bar, tray, or
  desktop forms.
---

# psi6 桌面框架

用 `psi6` 的 **运行时、任务、主题、窗壳** 拼桌面程序，不要从 PySide6 重写基建。框架入口只从 `psi6` 导入。控件从 `psi6.ui` 的模块导入，例如 `from psi6.ui.data_table import DataTable`。批处理窗是 `from psi6.templates import BatchToolWindow`。
**本仓库不提供 Excel/PDF 等业务模板，也不为某个产品堆叠首页主键。** 行业逻辑写在应用仓库；这里只提供可复用的运行时与通用壳。改外观优先构造参数，不够再子类覆盖钩子，不要改 `_` 私有实现。

## 核心（先做这些）

1. **运行时 `App`**：`App(name)` 创建应用，`app.run(window)` 进入循环。不要手写 `QApplication(sys.argv)`。
   - 主题：`App(name, theme="light"|"dark"|"auto")`，或传入 `Theme` 子类。类属性必须是 `Tokens` 字段名，写错会在加载时抛错。不要写 QSS，也不要用 JSON / TOML / YAML 描述主题。运行中 `app.set_theme(...)`。
   - 图标：与主题模块同目录的 `icons/search.svg` 覆盖 `Icon("search")`。路径相对该模块文件，不相对进程工作目录。仍可用 `register_icon`。
   - 窗壳：主窗口用 `DesktopWindow`（自定义 `TitleBar`、圆角边框；最大化取消圆角）。`app.run(window, tray=True)` 在系统有托盘时接到 `TrayIcon`：关窗口隐藏到托盘，菜单「退出」才结束进程。
   - 默认允许多开，也不记住窗口位置。需要时 `app.run(window, single_instance=True, restore_geometry=True)`。
   - 关掉窗口不取消任务。应用退出时才按「窗口几何 → `runner.shutdown()` → 单实例锁 → 隐藏托盘」收尾。
   - `tray=True` 且系统有托盘时，关窗口是隐藏。没有托盘时关闭仍退出，不要假设进程会留在后台。
   - 配置：`App.load_config` / `save_config`。设置页用 `pydantic_settings`（`field_switch(..., group="扫描")`）。
   - 父子：子控件靠 `layout.addWidget` 获得父对象。不进布局的（覆盖层、边缘热区、Toast、对话框）才写 `parent=`。从布局移除时不要 `setParent(None)`，`hide()` 后 `deleteLater()`。初始化可以 `hide()`，不要主动 `show()`；主窗口树搭完后再 `show()`。
2. **任务 `TaskRunner`，界面 `BatchToolWindow`**：读盘、扫目录、网络必须 `app.runner.submit`。`BatchToolWindow` 只接表单和结果表，不自己调度。不要手写 `QThread`。

```python
def run_job(params, *, on_progress, on_log, is_cancelled) -> JobOutcome: ...
```

`handle.cancel()` 只把 `handle.cancel_requested` 设为真，不会杀掉线程。工作函数看到 `is_cancelled()` 后 `raise InterruptedError`，返回之后 `TaskHandle.status` 才变成 `cancelled`。忽略取消并正常返回时，若请求已经发出，结束状态仍是 `cancelled`。`runner.shutdown()` 超时得到 `False` 表示线程还在跑。返回 `JobOutcome(rows=..., message=...)` 只表示要填进表的结果。同一槽同时只跑一份：`runner.submit(..., exclusive="batch")`。`runner.is_busy("scan")` 查的是这个槽。进度默认 50ms 节流。任务条用 `from psi6.ui.task_panel import TaskPanel`。`LogPanel` 默认最多 2000 条。合同见 `psi6.jobs.file_index`，那不是要复制的行业模板。
3. **主题**：颜色、尺寸、时长只用 token。自绘 `create_painter` / `rounded_rect_path` / `mix_color`，读 `token_color` / `token_int` / `token_ms`。不要 emoji、不要页面私有 QSS。动画只调时长 token；`reduced_motion: 1` 或时长 `0` 关闭。按下缩小：`install_press_scale`。对比度用 `contrast_notes(tokens)`，它只返回说明，不阻止 `Theme` 加载。结构错误（未知字段、错误的 `base`、显式图标目录不存在）才抛错。高 DPI 使用 `PassThrough`，几何是逻辑像素，图标按 `devicePixelRatio` 栅格化。
4. **窗壳通用件**：`TitleBar`（拖动、双击最大化、从最大化拖出还原）、`DesktopWindow.set_icon`、`TrayIcon.refresh`（换主题重绘）、`SingleInstance`（仅在 `single_instance=True` 时使用）。多页用 `AppShell` + `NavDestination`（`set_sidebar_compact`，宽度走 `token_ms`）。

表单用 Pydantic + `pydantic_form` / `field_dir` / `field_file`。路径行用 `FileInput` / `FolderInput`，不要业务里直接 `QFileDialog`。用户短句用 `app.notifier`（`info` 只进状态栏）；必须看见的错误用 `fail`/`warn`；过程记录用 `LogPanel` + `LogRecord`。任务进行中 `DataTable.set_busy`。

批处理窗：`BatchToolWindow(title=..., params=..., job=..., app=..., icon=..., exclusive=...)`。改结果展示覆盖 `present_outcome` / `tag_values`。

对照窗口：`python -m psi6 kit`。截图验收：`python -m psi6 shot`。

## 验证

在仓库里：

```powershell
uv run pytest
uv run python -m psi6.examples.minimal --check
uv run python -m psi6.examples.task_job --check
uv run python -m psi6.examples.custom_theme --check
uv run python -m psi6.examples.task_status --check
```

`--check` 返回 0 表示示例能启动并退出。新项目复制 `skills/psi6-desktop/template/`。模板不是 psi6 的安装依赖，里面的 `pyproject.toml` 要等 0.3 发布后才适合单独 `uv sync`。在本仓库用已装好的环境，于模板目录执行 `python app.py --check`。迁移见仓库根目录 `MIGRATION.md`。

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
- 复制 `LogPanel` / `TaskPanel` / `Section` / `EmptyState` 自己做一套
- 把 loguru 诊断日志和操作日志混在一个控件
- 为了改一行业务逻辑去改 `psi6.ui._path_picker` 等私有模块
- 用 emoji 当图标，或引入另一套图标字体
- 为换皮肤复制整份 QSS；只覆盖 token
- 在 psi6 里加 Excel/PDF/合并导出等业务模板，或为某个打包器/构建器堆叠首页主键
