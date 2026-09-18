# M0 挖矿报告：从现有 PySide6 项目抽出最小原语

文档状态：M0 完成稿  
范围：对照 `ai20260401` 下真实桌面项目，判断 `psi6` 第一刀该抽什么、不该抽什么。  
结论用法：M1 只实现本文「最小公开 API」；超出清单的组件一律后置。

## 1. 看了哪些项目

按「对小工具基建的参考价值」分成两类。

| 项目 | 类型 | 为什么看它 |
| --- | --- | --- |
| `littool` | 批处理小工具 | 最接近 Batch Tool 模板：选目录 → 配置 → 后台任务 → 操作日志 → 结果统计 |
| `memail` | 办公工具产品 | 已有 `FilePicker`、主题常量、`LogDock`、QThreadPool Worker、Pydantic 设置 |
| `pyhub` | 多页安装/检测工具 | 最完整的异步任务管理器（`AsyncWorkerManager`）和 Pydantic 领域模型 |
| `fx` | 文档/表格工作台 | 每个耗时操作用独立 `QThread` 子类，状态栏任务，禁止 `terminate()` |
| `marklines` | 工程计算 + CAD | 对话框 + 可编辑表很多；计算/CAD 加载在 UI 线程，是反面教材 |
| `editor` | 可嵌入编辑器 | 启动壳很薄；文件对话框、表单对话框手写重复 |
| `wander` | 完整工业产品 | 有自己的壳层、QSS、asyncio 设备循环；**不要作为第一刀抽象来源** |

`ol` 也依赖 PySide6，但是 Outlook/OneDrive 产品，和第一阶段小工具模板距离远，M0 不纳入抽取。

## 2. 一句话发现

重复的不是 Button/Label，而是下面这条流水线：

**启动应用 → 选文件/目录 → 用 Pydantic 存参数 → 后台跑任务 → 进度/取消 → 日志 → 弹窗报错 → 各写一份 QSS。**

几乎每个项目都有 Pydantic 模型，但没有任何一个从 Model 生成表单。表单全是手绑 `QLineEdit` / `.ui` / `QFormLayout`。这是 Agent 每次都在重复、也最值得做成 SDK 的缺口。

## 3. 重复原语清单（第一刀只取 8 个）

下列「出现次数」按本节看过的项目计。API 名称是 `psi6` 拟用名，不是现有类名。

| # | 原语 | 出现 | 现有实现 | 抽什么 | 不抽什么 |
| --- | --- | --- | --- | --- | --- |
| 1 | `App` | 全员 | 各 `main()` 里手写 `QApplication` | 名称/组织、主题、未捕获异常、`exec` | wander 的 HWND/闪烁门闩、memail 的 i18n/插件引导 |
| 2 | `TaskRunner` | 5 | pyhub `AsyncWorkerManager`；memail `_PreviewWorker`；littool `ArchiveWorker`；fx 多个 `QThread` 子类 | 提交可调用对象、进度、成功/失败、协作取消 | wander `AsyncioRunner`（设备事件循环）；每业务一个 Worker 子类 |
| 3 | `FileInput` / `FolderInput` | 6 | memail `FilePicker`；littool `PathSelector`；其余直接 `QFileDialog` | 单文件/多文件/目录、过滤器、`Path`、空/选中/非法状态 | 工作空间树、最近文件复杂逻辑 |
| 4 | `LogPanel` | 4 | littool 操作日志表；memail `LogDock`（loguru）；pyhub `QPlainTextEdit` | 任务过程日志：级别、过滤、清空、导出 | 把 loguru 诊断日志和操作日志混成一个组件 |
| 5 | `TaskPanel` | 3 | littool 开始/取消 + 状态栏进度；pyhub Installation 页；memail preview 进度条 | 忙碌态、进度、取消、禁用冲突按钮 | pyhub 的 checkpoint / skip / retry 计划引擎 |
| 6 | `pydantic_form` | 0（缺口） | 模型在 littool/pyhub/memail/wander 都有，UI 全手写 | `BaseModel` → 表单 + 校验回填 | 可视化表单设计器、任意布局 DSL |
| 7 | `Theme` | 5 | littool 整段 QSS；memail `theme_colors.py`；wander 超长 QSS；pyhub 内嵌 `_STYLE` | 一小份 token（色/间距/圆角/字体）生成 QSS | 复制 wander/memail 品牌色或完整产品皮肤 |
| 8 | `ConfigStore` | 3 | pyhub JSON；memail YAML + `BaseSettings`；littool 仅 env 默认值 | 把 Pydantic 模型存到用户目录 | 多配置文件、插件目录、工作空间格式 |

### 3.1 原语对照（证据）

**启动**

- `littool`：`QApplication` + 全局 QSS + `MainWindow.show()`。
- `memail`：设置加载 → `QApplication` → 主题 → 主窗；已接近 `App.run()`。
- `marklines`：启动前强行 import WebEngine，无统一异常钩子。
- `editor`：`setStyle("Fusion")` 后塞一个 `QMainWindow`。

**后台任务**

- `pyhub.async_workers.manager.AsyncWorkerManager`：`QThreadPool` + `QRunnable` + 跨线程 Signal，这是 TaskRunner 的首选骨架。
- `littool.workers.archive_worker.ArchiveWorker`：每个业务一个 `QThread` 子类，信号是 `progress_changed` / `log_emitted` / `finished_ok` / `failed`。语义对，形状不应复制。
- `memail` preview 页：临时 `_PreviewWorker(QRunnable)`，和 pyhub 同构但未抽公共管理器。
- `fx`：`SpreadsheetPreviewLoadWorker(QThread)` 等，注释明确禁止 `QThread.terminate()`。
- `marklines._run_calc` / CAD 打开：`QApplication.setOverrideCursor(WaitCursor)`，计算发生在 UI 线程。

**选路径**

- `memail.ui.widgets.file_picker.FilePicker`：已有 `directory_mode` + filter，最接近 `FileInput`。
- `littool.ui.widgets.PathSelector`：只支持目录，可编辑路径文本。
- `editor` / `marklines` / `wander` / `fx`：窗口方法里直接 `getOpenFileName` / `getExistingDirectory`。

**日志**

- `littool.ui.log_panel.LogPanel`：结构化操作记录 + 过滤 + CSV 导出。Batch Tool 要的是这个。
- `memail.ui.widgets.log_dock.LogDockWidget`：loguru sink，给开发者看，不是给用户看任务结果。
- `pyhub`：安装页 `QPlainTextEdit.appendPlainText`。

**表单与配置**

- `littool.config.AppSettings`、`pyhub.domain.models.MirrorSettings`、`memail.models.settings.AppSettings`、`wander2.adapters.qt.ui.forms.HomeFormData` 都是 Pydantic。
- wander 甚至有 `format_home_form_error()`，但控件仍在 `home_window._build_form_widgets()` 手写，再 `_build_form()` 填回 Model。
- pyhub Settings 页用 Qt Designer `.ui` + `findChild` 填值。

**主题**

- 颜色全部硬编码：`#3b82f6`（littool）、`#1A3C2B`（pyhub）、`#e16336`（memail）、wander 一整页 zinc/绿。
- memail 把品牌色拆到 `theme_colors.py`，方向对，但仍是项目私有常量，组件里还有另一套 hex（如 `StatusIndicator`）。

### 3.2 明确后置（现在看起来像组件，但复用率不够或过重）

| 能力 | 为什么现在不抽 |
| --- | --- |
| `DataTable` / `TableEditor` | marklines 可编辑参数表、memail 预览表、pyhub 软件表，列语义差太远。Batch Tool 第一版用 `LogPanel` 展示结果即可 |
| 主窗口导航壳（侧栏 + Stack） | pyhub / memail / wander 各做一套，小工具用不到 |
| Qt Designer `.ui` 加载 | 只有 pyhub 作为主路径；和「AI 写 Python」冲突 |
| 计划引擎 checkpoint / retry / skip | pyhub 安装器领域，不是通用小工具 |
| CAD / WebEngine / asyncio 设备循环 | 单项目能力 |
| i18n、插件、工作空间格式 | memail 产品层 |

## 4. Agent 每次最容易写错的 10 件事

来自真实代码，不是想象：

1. 在 UI 线程读 Excel / 开 CAD / 跑计算（`marklines`）。
2. 为每个任务再写一个 `QThread` 子类（`littool`、`fx`）。
3. 用 `QApplication.processEvents()` 假装异步（`memail` 发信/生成草稿）。
4. 直接 `QFileDialog`，不处理空路径、不存在、只读。
5. 开始后不禁用按钮，取消后状态机乱掉。
6. 有 Pydantic 模型，仍手写一份平行表单。
7. 页面或控件里散落 `setStyleSheet("background-color: #...")`。
8. 操作日志和诊断日志混在一起。
9. 失败只用 `QMessageBox.critical(str(exc))`，没有全局未捕获异常。
10. 强杀线程（`fx` 已经踩过并写了禁令）。

这些应直接变成 M2 Skills 的反模式，而不是等 SDK 写完再补。

## 5. 最小公开 API 草案

包名保持 `psi6`。第一阶段全部具体到 PySide6，不为 QML/Web 做空接口。

```text
src/psi6/
  runtime/
    app.py          # App
    tasks.py        # TaskRunner / TaskHandle / TaskStatus
    config.py       # ConfigStore
    errors.py       # 未捕获异常 → 日志 + 用户可读对话框
  ui/
    file_input.py   # FileInput, FolderInput
    log_panel.py    # LogPanel, LogRecord, LogLevel
    task_panel.py   # TaskPanel
    form.py         # pydantic_form
  theme/
    tokens.py
    apply.py
examples/
  batch_tool/       # 可运行的 Batch Tool 骨架
```

### 5.1 `App`

```python
class App:
    """进程内唯一的桌面应用入口。"""

    def __init__(self, name: str, *, organization: str = "psi6") -> None: ...
    def run(self, window: QWidget) -> int:
        """套用主题、安装异常钩子、show 窗口、exec。"""
```

业务代码不再写 `QApplication(sys.argv)`。

### 5.2 `TaskRunner`

采用 pyhub 的线程池模型，加上 littool 的进度/日志/取消语义。

```python
class TaskStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskHandle:
    id: str
    status: TaskStatus
    def cancel(self) -> None: ...

class TaskRunner(QObject):
    """UI 线程只提交；工作在线程池。取消是协作式的，禁止 terminate。"""

    def submit(
        self,
        fn: Callable[..., Any],
        *,
        on_progress: Callable[[int, int, str], None] | None = None,
        on_log: Callable[[LogRecord], None] | None = None,
        on_succeeded: Callable[[Any], None] | None = None,
        on_failed: Callable[[str], None] | None = None,
        on_cancelled: Callable[[], None] | None = None,
    ) -> TaskHandle: ...
```

`fn` 若接受 `on_progress` / `on_log` / `is_cancelled`，由 Runner 注入。这正好覆盖 `littool.ArchiveService.run(...)` 的回调形状。

### 5.3 `FileInput` / `FolderInput`

以 memail `FilePicker` 为底，补 littool 的可编辑路径和校验状态。

```python
class FileInput(QWidget):
    """选择本地文件。"""

    path_changed: Signal  # Path | None

    def __init__(
        self,
        *,
        filters: str = "All Files (*)",
        multiple: bool = False,
        parent: QWidget | None = None,
    ) -> None: ...

    def path(self) -> Path | None: ...
    def paths(self) -> list[Path]: ...
    def set_path(self, path: Path | str | None) -> None: ...
    def is_valid(self) -> bool: ...   # 空 / 不存在 / 扩展名不符 → False
```

`FolderInput` 同源，只走 `getExistingDirectory`。

### 5.4 `LogPanel`

以 littool `LogPanel` 为底，去掉品牌/发票列，改成通用 `extra: dict`。

```python
class LogLevel(StrEnum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"

@dataclass
class LogRecord:
    level: LogLevel
    message: str
    detail: str = ""
    extra: dict[str, str] = field(default_factory=dict)

class LogPanel(QWidget):
    def append(self, record: LogRecord) -> None: ...
    def clear(self) -> None: ...
    def count_by_level(self) -> dict[LogLevel, int]: ...
    def export_csv(self, path: Path) -> None: ...
```

诊断日志（loguru）不进这个面板。需要的话以后再加 `DebugLogDock`。

### 5.5 `TaskPanel`

从 littool 主窗工具条 + 状态栏进度抽出，不再让每个 `MainWindow` 自己管按钮 enable。

```python
class TaskPanel(QWidget):
    """开始 / 取消 / 进度 / 状态文本。"""

    start_requested: Signal
    cancel_requested: Signal

    def set_idle(self, message: str = "就绪") -> None: ...
    def set_running(self, current: int, total: int, message: str) -> None: ...
    def set_finished(self, message: str) -> None: ...
    def set_failed(self, message: str) -> None: ...
```

主窗只连接 `start_requested` → 校验参数 → `TaskRunner.submit`。

### 5.6 `pydantic_form`

这是现有项目里唯一「人人需要、无人实现」的原语。

```python
def pydantic_form(
    model: type[BaseModel] | BaseModel,
    *,
    parent: QWidget | None = None,
) -> FormView:
    """由 Model / Field 生成表单。Path 字段映射 FileInput 或 FolderInput。"""

class FormView(QWidget):
    def get_model(self) -> BaseModel:
        """校验失败时抛出用户可读错误，不抛原始 ValidationError。"""
    def set_model(self, model: BaseModel) -> None: ...
```

第一版字段映射：

| Field 类型 | 控件 |
| --- | --- |
| `str` | `QLineEdit` |
| `int` / `float` | `QSpinBox` / `QDoubleSpinBox` |
| `bool` | `QCheckBox` |
| `Path` + metadata `kind=dir` | `FolderInput` |
| `Path`（默认） | `FileInput` |
| `Enum` / `Literal` | `QComboBox` |

`Field(description=...)` 作为 label；`Field(json_schema_extra={"filters": "Excel (*.xlsx)"})` 传给 `FileInput`。校验错误贴在字段旁，参考 wander 的中文错误思路，但不要复制那张字段标签表。

### 5.7 `Theme` + `ConfigStore`

```python
# theme/tokens.py — 唯一允许出现的色值/间距来源
class Tokens:
    color_bg: str
    color_text: str
    color_primary: str
    color_danger: str
    color_success: str
    color_warning: str
    space_md: int
    radius: int
    font_family: str
    font_size: int

def apply_theme(app: QApplication, tokens: Tokens | None = None) -> None: ...

class ConfigStore:
    """把 BaseModel 存到 ~/.psi6/<app_name>/config.json。"""

    def load(self, model_type: type[T], *, app_name: str) -> T: ...
    def save(self, model: BaseModel, *, app_name: str) -> None: ...
```

组件禁止再写 hex。M1 提供一套中性 token，不引入 memail 橙或 pyhub 墨绿。

## 6. 第一个模板：Batch Tool

五个模板里只做这一个。页面结构直接对应 `littool` 主窗，而不是对应 `memail` 多页向导。

```text
[ 表单：FolderInput / FileInput / pydantic_form ]
[ TaskPanel：开始 / 取消 / 进度 ]
[ 统计：成功 / 警告 / 错误 ]
[ LogPanel ]
[ 状态栏 ]
```

业务函数签名约定（给 Agent 和模板共同遵守）：

```python
def run_job(
    params: BaseModel,
    *,
    on_progress: Callable[[int, int, str], None],
    on_log: Callable[[LogRecord], None],
    is_cancelled: Callable[[], bool],
) -> Any: ...
```

模板只替换 `params` 模型和 `run_job`。窗口、线程、日志、主题不准再手写。

## 7. 狗粮工具建议

| 候选 | 结论 |
| --- | --- |
| `examples/batch_tool`（仓库内） | **先做。** SDK 自己的可运行验收，不绑业务包袱 |
| `littool` | **第一个真实迁移。** 体量小，原语一一对应：`PathSelector`→`FolderInput`，`ArchiveWorker`→`TaskRunner`，`LogPanel` 可替换，`AppSettings` 可走 `pydantic_form` + `ConfigStore` |
| `memail` / `fx` / `pyhub` | 不迁。它们会倒逼导航壳、计划引擎、文档模型，把 M1 撑爆 |
| `marklines` | 不迁。先把它当成「UI 线程做重活」的反例写进 Skills |
| `wander` | 不迁。它已经是独立设计系统 |

迁移 `littool` 的验收：业务层只剩 `services/` 与 `models.py`；`ui/` 不再出现 `QThread`、`QFileDialog`、整段 QSS。

## 8. M1 施工顺序（建议）

1. `Tokens` + `apply_theme` + `App`（含异常钩子）
2. `TaskRunner`（先写不依赖 UI 的单元测试）
3. `FileInput` / `FolderInput`
4. `LogPanel` + `TaskPanel`
5. `pydantic_form`（只覆盖第 5.6 节映射表）
6. `ConfigStore`
7. `examples/batch_tool` 跑通：选目录 → 假装处理文件 → 日志与进度 → 取消
8. 停下来看 API 是否还要改；稳定后再迁 `littool`

不要在这一步建 Registry、MCP、DataTable、多模板。

## 9. Go / No-Go 预告（给后面 A/B 用）

M1 完成后，用同一个新需求（例如「Excel 多文件合并」）做一次 A/B：

- A：Agent 只用 PySide6
- B：Agent 必须用 `psi6` + Batch Tool 模板

若 B 组首次可运行时间没有明显下降，先改 API 和示例，不加组件。
