# psi6

给编码 Agent 用的轻量 PySide6 桌面框架。它把应用生命周期、后台任务、Python 主题和通用窗壳收成一套稳定入口。业务窗口留在应用自己的代码里，控件库不塞进框架入口。

## 安装

```powershell
pip install psi6
```

## 三个最短用法

普通窗口：

```python
from psi6 import App, DesktopWindow

app = App("demo")
window = DesktopWindow(title="Demo")  # 默认 Qt 标题栏；frameless=True 才自绘
raise SystemExit(app.run(window))
```

后台任务。界面只展示，执行在 `TaskRunner`。关掉窗口不会取消任务；应用退出时才会取消并等待线程结束。

```python
handle = app.runner.submit(run_job, on_succeeded=show_rows, on_failed=show_error)
handle.cancel()
```

`run_job` 用 `on_progress`、`on_log`、`is_cancelled`。失败信息在 `on_failed` 和 `TaskHandle.error_message`。没有指定进度位置时，把 `StatusProgress` 放进 `window.statusBar()`。开始和取消是页面上分开的按钮。

自定义主题。字段名必须是 `Tokens` 的字段，写错会在加载时抛错。对比度不足只作为诊断，不阻止加载。

```python
from psi6 import Theme, contrast_notes

class Midnight(Theme):
    name = "midnight"
    base = "dark"
    style = "compact"
    color_primary = "#4F46E5"
    radius = 8

app = App("demo", theme=Midnight)
contrast_notes(app.tokens)
```

与主题模块同目录的 `icons/search.svg` 会覆盖同名图标，路径不看当前工作目录。

## 默认行为

默认可以同时启动多份，也不写窗口位置。单实例锁只在显式打开时存在，退出时也只在那时释放。

```python
app.run(window, tray=True, single_instance=True, restore_geometry=True)
```

配置文件损坏时使用模型默认值。窗口几何损坏时保持调用方给的尺寸，应用仍能启动。系统没有托盘时，`tray=True` 不阻止窗口关闭和进程退出。

## 稳定接口

0.4 的根包只导出这些名字，名单在 [`src/psi6/api.py`](src/psi6/api.py)：`App`、`TaskRunner`、`TaskHandle`、`TaskStatus`、`JobOutcome`、`Theme`、`Tokens`、`contrast_notes`、`DesktopWindow`、`TitleBar`、`TrayIcon`。

`DesktopWindow` 默认使用 Qt 标题栏。`frameless=True` 才自绘标题栏。`TaskRunner` 执行任务。`cancel()` 只是请求，结束看 `TaskHandle.status`。`JobOutcome` 只表示要填进表的结果。其它控件从 `psi6.ui` 导入。名字以 `_` 开头的模块是内部实现。迁移见 [`MIGRATION.md`](MIGRATION.md)，破坏性变更写在 [`CHANGELOG.md`](CHANGELOG.md)。

安装后核对示例：

```powershell
python -m psi6.examples.minimal --check
python -m psi6.examples.task_job --check
python -m psi6.examples.custom_theme --check
python -m psi6.examples.task_status --check
```

组件预览：`python -m psi6 kit`，按组件分组，可切换四种组合，另附 Mono、Obsidian、Pine 内置主题。Agent 约定：[`skills/psi6-desktop/SKILL.md`](skills/psi6-desktop/SKILL.md)。新项目复制 [`skills/psi6-desktop/template/`](skills/psi6-desktop/template/)，在该目录执行 `python app.py --check`。关窗口、点取消、应用退出是三件事。

## 开发

```powershell
uv sync --extra dev
uv run pytest
```
