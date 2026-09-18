# psi6

面向 AI Coding Agent 的 PySide6 基建：**运行时、批处理、主题、窗壳**（自定义标题栏、托盘、防多开）。
**不包含 Excel/PDF 等业务模板，也不为某个产品堆叠首页主键。** 行业逻辑写在你的应用里。

## 安装

运行或依赖这个库：

```powershell
pip install psi6
# 或
uv add psi6
```

YAML 主题额外需要：`pip install psi6[yaml]`。

`pip` **不会**安装 Cursor / Claude skill。skill 只在 Git 仓库的 `.cursor/skills/psi6-desktop/`。用 AI 写 psi6 应用时，clone 本仓库，或把该目录拷进你的项目。

## 使用路线

1. **运行时**：`App` + `DesktopWindow`。`app.run(window, tray=True)` 托盘；默认防多开、记住位置。参数用 Pydantic + `pydantic_form`。
2. **批处理**：耗时工作进 `TaskRunner`（`exclusive=` / `is_busy`），或可继承的 `BatchToolWindow(..., icon=..., exclusive=...)`。
3. **主题**：`App(..., theme="dark"|"auto"|Path)`；JSON / TOML / YAML 覆盖 token。图标放主题旁 `icons/search.svg`。不要写 QSS。
4. **窗壳**：`TitleBar` 拖动 / 最大化 / 从最大化拖出；`TrayIcon` 随主题换色；圆角窗最大化时取消圆角。
5. **改控件**：先构造参数；不够则子类覆盖公开钩子（如 `BatchToolWindow.present_outcome`、`DataTable.display_text`）。自绘用 `create_painter` / `token_color`。不要碰 `_` 私有实现。

```python
from psi6 import App
from psi6.ui.desktop_window import DesktopWindow

app = App("demo")
window = DesktopWindow(title="Demo")
raise SystemExit(app.run(window, tray=True))
```

文件索引只是 `run_job` 合同示例（扫盘、取消、失败可读），不是要复制的产品。

```powershell
uv run python -m psi6 kit
uv run python -m psi6 shot
```

规则在 `.cursor/skills/psi6-desktop/SKILL.md`。

## 从源码开发

```powershell
uv sync --extra dev
uv run psi6
uv run pytest
```

## 发布

1. 在 GitHub 建公开仓库（默认按 `modaye/psi6` 写进了元数据；用户名不同就改 `pyproject.toml` 的 `[project.urls]`）。
2. 在 PyPI 打开 Trusted Publishing，pending publisher 填：owner、仓库名、工作流 `publish.yml`、环境 `pypi`。
3. GitHub 仓库 Settings → Environments 新建 `pypi`。
4. 打与 `pyproject.toml` 相同的版本标签，例如 `git tag v0.1.0 && git push origin v0.1.0`，Actions 会 `uv build` 并 `uv publish`。

本地试发 TestPyPI：`uv build` 然后 `uv publish --index testpypi`。

## 测试

```powershell
uv run pytest
```
