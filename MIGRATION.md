# 迁移

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

## 示例

安装后运行：

```powershell
python -m psi6.examples.minimal --check
python -m psi6.examples.task_job --check
python -m psi6.examples.custom_theme --check
python -m psi6.examples.task_status --check
```

新项目可从 `skills/psi6-desktop/template/` 复制 `app.py` 和 `theme.py`。该目录不是运行时依赖。
