# 迁移

## 从 0.4 迁到 0.5

0.5 只增加调用方式，不替换 0.4 的根包入口。

| 0.4 写法 | 0.5 |
| --- | --- |
| `on_failed` 只收一句说明 | 仍可用。声明第二个参数收到原异常，第三个参数收到堆栈文本 |
| 任务结束自己把按钮设回可用 | `submit(..., on_finished=...)`。同槽被挡下用 `on_busy`，不会触发 `on_finished` |
| 把 `on_log` 逐层传入 | 任务里直接 `task_log(...)`。任务内部再开的线程用 `capture_task_context().run(fn)` |
| 只有 `LogPanel` | 表格仍用 `LogPanel`。终端式日志用 `LogConsole`，`logger.addHandler(console.handler())` |
| 逐个 `set_path` 回填 | `form.restore(model)`，回填时不逐字段发信号 |
| 保存接 `path_changed` | `path_changed` 仍每次按键都发。保存改接 `path_edited`。清除按钮默认开启 |
| 路径记在自己的 `QSettings` 或 `.env` | 上次路径用 `remember_path` / `recalled_path`。程序参数仍用 `load_config`。进程参数留在应用自己的 pydantic-settings |

## 从 0.3 迁到 0.4

| 0.3 | 0.4 |
| --- | --- |
| `from psi6.templates import BatchToolWindow` | 不再提供。用 `DesktopWindow`、`pydantic_form`、`DataTable`、`LogPanel` 和 `app.runner.submit` 自己组合。参考 `python -m psi6` |
| `from psi6.ui.task_panel import TaskPanel` | 不再提供。开始、取消各自放按钮。进度用 `StatusProgress(window.statusBar())` |
| `DesktopWindow(title=...)` 自绘标题栏 | 默认是 Qt 标题栏。需要无边框时传 `frameless=True` |
| 浅色底 `#eef1f5` | 浅色底 `#ffffff` |
| 未写尺寸的主题，控件高 32、圆角 4 | 默认 `style="modern"`：控件高 36、圆角 6。`style="compact"`：控件高 30、圆角 4 |
| `density = "compact"` | 已删除。改成 `style = "compact"`。再写 `density` 会在加载时抛错 |

## 从 0.2 迁到 0.3

0.3 收窄了 `import psi6` 的入口。类还在原来的模块里，没有另做一套兼容转发。

## 框架入口

仍从根包导入：

```python
from psi6 import (
    App,
    DesktopWindow,
    JobOutcome,
    TaskHandle,
    TaskRunner,
    TaskStatus,
    Theme,
    TitleBar,
    Tokens,
    TrayIcon,
    contrast_notes,
)
```

`Theme` 和 `contrast_notes` 也可以继续从 `psi6.theme` 导入，是同一个对象。

## 移出根包

| 0.2 | 0.3 |
| --- | --- |
| `from psi6 import DataTable` 以及其他控件 | `from psi6.ui.data_table import DataTable`，其余控件仍在 `psi6.ui` 的对应模块 |
| `from psi6 import BatchToolWindow` | 0.4 起不再提供，见上一节 |
| `from psi6 import run_file_index` | `from psi6.jobs.file_index import run_file_index` |
| `from psi6 import ConfigStore, Notifier` | `from psi6.runtime import ConfigStore, Notifier` |

## 行为

- `TaskHandle.cancel()` 之后先看 `cancel_requested`。`status` 要等工作函数结束才变成 `cancelled`。
- `runner.shutdown()` 超时返回 `False` 时，线程还在跑，不会被杀掉。
- `App` 在非主线程构造或 `run` 会抛出 `RuntimeError`。不要在事件循环里再调用 `run`。
- `LogPanel` 默认只留最近 2000 条。需要更长历史时传入 `max_entries`。

未发布版本里主题的改法：

| 0.5 写法 | 之后 |
| --- | --- |
| `console.append_record(record)` | 用 `console.append(record)`。`append` 同时接受 `LogRecord` 和纯文本 |
| `base` 只能 `light` / `dark` | 增加 `auto`。跟随系统时给 `light` / `dark` 两个变体，本类显式写的 `style` 和覆盖压在变体上 |
| 主题切换自己重画 | `LogConsole` 按存下来的记录整片重画，`Sparkline` 重绘。字体族和字号也会进 `QApplication.setFont` |
| 主题选择只活在本次进程 | `App(..., remember_theme=True)` 把选择写进 `theme.json`；默认仍不记 |
| 按下态沿用画布色，和悬停拉不开 | `color_pressed` 自动推导或显式覆盖。普通、幽灵、导航、图标、标题按钮和拖放区都已接入 |
| 对比度只看正文与背景 | `contrast_notes` 覆盖按钮、辅助文字、侧栏和气泡，并支持半透明色。旧调用方式不变 |
| 主题检查靠肉眼看预览 | `python -m psi6 theme <名称> --check`；`--json` 给脚本读。自定义主题用 `模块:类名` |

## 示例

安装后运行：

```powershell
python -m psi6.examples.minimal --check
python -m psi6.examples.task_job --check
python -m psi6.examples.custom_theme --check
python -m psi6.examples.task_status --check
```

新项目可从 `skills/psi6-desktop/template/` 复制 `app.py` 和 `theme.py`。该目录不是运行时依赖。
