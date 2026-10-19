# 变更

## 0.5.0

- `on_failed` 声明第二个位置参数时同时收到原异常对象。数据错误可以直接读异常上的结构，不再把错误码和说明塞进一段文字。单参数回调行为不变，堆栈仍在 `TaskHandle.error_traceback`。
- 新增 `psi6.runtime.logs.task_log`：任务执行期间任意调用深度都能写一行日志，不必把 `on_log` 逐层传下去。日志仍批量节流送回界面；任务之外调用回退到标准库 `logging`。
- `runner.submit(..., on_busy=...)`：同名 `exclusive` 槽还在跑时，被挡下的提交会同步触发一次 `on_busy`。不给则保持原来的静默行为。按钮禁用仍由界面负责。

以上三条来自第一个真实应用（DBS）的集成反馈。它自绘页眉、路径行和按钮，验证了 0.4.0 删除 `BatchToolWindow` 后的组合模型。

以下五条来自 DBS 与 HK 的第二轮反馈：

- 日志与进度缓冲加锁：joblib 等工作线程并发调用注入的 `on_log` / `on_progress` 不再丢记录，应用不必在外面自己加锁。应用的收尾回调抛错也不再污染 Qt 事件循环，错误打印到 stderr。
- `on_failed` 声明第三个位置参数时再带堆栈文本，可直接交给 `fail(..., detail=...)`。
- `runner.submit(..., on_finished=...)`：成功、失败、取消任一收尾后都执行一次，即使收尾回调自己抛错。界面用它恢复按钮；被 `exclusive` 挡下的提交走 `on_busy`。
- `App.remember_path` / `App.recalled_path`：界面路径记进 `QSettings`；恢复时路径已不在就清掉该项。程序参数仍走 pydantic 配置。
- 新增 `LogConsole`（`QTextBrowser`）：按时间往下滚的终端式日志。时间戳用辅助色，级别名和正文用该级别的主题色。`LogConsoleHandler` 用标准库 `logger.addHandler(console.handler())` 接入，工作线程会排队回界面线程。表格型 `LogPanel` 仍然保留。

以下来自第三个应用的集成反馈：

- `TaskRunner` 把提交线程的 `ContextVar` 带进工作线程。任务内部再开的线程不会自动继承，用 `psi6.runtime.logs.capture_task_context().run(...)`。
- `FormView.set_model` / `restore` 回填时挡住全部子控件信号，即改即存不会把还没回填的字段写成空。
- `FileInput` / `FolderInput` 默认带清除按钮（`clearable=False` 可关）。`path_changed` 仍随按键发出；`path_edited` 在编辑结束、浏览、拖放或清除后发出，用来保存。多个路径仍用分号分隔。

## 0.4.1

- 默认浅色和深色调色板重调：中性色带轻微冷色倾向，边框更细，浅色主色改为更明确的蓝，深色主色更透亮。字体栈优先 `Segoe UI Variable Text`。
- 新增内置主题：`Mono`（黑白极简）、`Obsidian`（深黑 + 靛紫）、`Pine`（墨绿）、`ModernDark`、`CompactDark`。`python -m psi6 kit` 的主题页可以预览。
- 修复勾选框和单选框：未选时画出边框矩形，勾选时填充主色并显示勾选图。焦点、悬停、禁用和半选（indeterminate）也各有样式。QSS 里的勾选图改用逻辑尺寸的 SVG，由样式表引擎按当前分辨率绘制，高 DPI 缩放下不再裁切、涂出界或起毛边。

## 0.4.0

- 不再提供 `BatchToolWindow` 和 `TaskPanel`。表单、结果和日志由应用自己组合。
- `DesktopWindow` 默认使用 Qt 标题栏。`frameless=True` 才使用自绘标题栏。
- 进度没有指定位置时用 `StatusProgress`，放在状态栏右侧。开始和取消是分开的按钮。
- 浅色主题的 `color_bg` 改为纯白 `#ffffff`。
- 默认窗口的客户区和状态栏使用主题底色。只有 `frameless=True` 时主窗口才透明，背景画在圆角壳上。
- 项目模板包含主题、任务页和 `python app.py --check`。业务写在模板的 `job.py`。
- 关窗口、点取消、应用退出是三件事。文件索引页按这个区分：关窗口不取消任务，取消按钮只发请求，退出才 `shutdown`。
- `Theme.style` 取 `modern` 或 `compact`，只决定尺寸。`base` 仍只决定浅色或深色。未写尺寸的主题改为现代度量：控件高 36、圆角 6。`density` 已删除，旧主题改写 `style`。
- 文字只有标题、正文、辅助三档。表面是窗口、面板、输入、浮层四层。选中用同一套悬停底加正文色。主按钮实心，次按钮描边，危险按钮用危险色。
- `python -m psi6 kit` 按组件分组，并有状态矩阵和四种组合。文件索引组合页放在同一窗口里。macOS、Linux 和 150% 缩放尚未在本机验证。

## 0.3.0

- 根包只导出框架入口：`App`、`TaskRunner`、`TaskHandle`、`TaskStatus`、`JobOutcome`、`Theme`、`Tokens`、`contrast_notes`、`DesktopWindow`、`TitleBar`、`TrayIcon`。控件改从 `psi6.ui` 导入，`BatchToolWindow` 改从 `psi6.templates` 导入。对照见 [MIGRATION.md](MIGRATION.md)。
- `cancel()` 只发出取消请求，`TaskHandle.cancel_requested` 立即为真。`status` 等工作函数结束后才变成 `cancelled`。`shutdown` 超时返回 `False`，不强制结束线程。
- `App` 只能在主线程使用。`run` 不能嵌套。已有 `QApplication` 时复用。
- `LogPanel` 默认最多保留 2000 条。
- 安装后可运行 `python -m psi6.examples.minimal --check`，以及 `task_job`、`custom_theme`、`task_status`。项目骨架在 `skills/psi6-desktop/template/`，不属于运行时依赖。

## 0.2.0

- `App.run` 默认允许多开，也不再记住窗口位置。需要时显式传入 `single_instance=True` 或 `restore_geometry=True`。
- 主题改为 Python 类（`psi6.theme.Theme`）。不再读取 JSON、TOML、YAML 主题文件，安装也不再需要 PyYAML。
- 未知 token 名称会抛错。图标目录相对主题模块文件，不相对当前工作目录。
- 任务模型保持三条线：`TaskRunner` 执行，`JobOutcome` 只表示批处理表格结果，`BatchToolWindow` 是可选界面，并调用同一个 runner。
- 关闭窗口不取消任务。应用退出时才取消任务并等待线程池。回调碰到已销毁的控件时不再把这个错误当成任务失败。
- 对比度不足由 `contrast_notes` 报告，不阻止主题加载。配置或窗口几何损坏时退回默认值，不阻止启动。
- 单实例锁只在 `single_instance=True` 时创建和释放。
- 系统没有托盘时，`tray=True` 不把关闭改成隐藏，进程仍随最后一个窗口退出。
- 高 DPI 使用 `PassThrough`。窗口几何按逻辑像素恢复。图标按设备像素比栅格化，占位仍是逻辑尺寸。
- 稳定接口名单见 `psi6.api.STABLE`。`BatchToolWindow` 仍导出，但是可选界面。

## 版本

0.x 期间，上文「稳定接口」里的职责保持不变。新增参数使用默认值。破坏性变更写在本文件并升一个次版本。顶层导出的其余控件可用，但不单独承诺与核心接口同一稳定级别。内部模块以 `_` 开头。
