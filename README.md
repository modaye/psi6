# psi6

PySide6 桌面 SDK：应用运行时、后台批处理、主题 token、自定义标题栏与系统托盘。

不提供 Excel/PDF 等业务模板，也不为某个产品堆叠首页主键。业务写在应用仓库。

## 安装

```powershell
pip install psi6
```

YAML 主题：`pip install psi6[yaml]`。

## 示例

```python
from psi6 import App
from psi6.ui.desktop_window import DesktopWindow

app = App("demo")
window = DesktopWindow(title="Demo")
raise SystemExit(app.run(window, tray=True))
```

## 能力

- **运行时** `App`：主题 `light` / `dark` / `auto` / 文件或目录；`run(..., tray=True)` 托盘；默认防多开、记住窗口位置
- **批处理** `TaskRunner` / `BatchToolWindow`：`exclusive` 单飞、`is_busy`、`JobOutcome`
- **主题** token 覆盖色与尺寸；图标用主题旁同名 `icons/*.svg`
- **窗壳** `DesktopWindow`、`TitleBar`、`TrayIcon`

组件预览：`python -m psi6 kit`。Agent 约定见 [`AGENTS.md`](AGENTS.md) 与 [`skills/psi6-desktop/SKILL.md`](skills/psi6-desktop/SKILL.md)。

## 开发

```powershell
uv sync --extra dev
uv run pytest
```
