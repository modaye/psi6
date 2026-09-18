# psi6

面向 AI Coding Agent 的 PySide6 桌面基建。

写或改这个仓库里的桌面工具时，先读 `skills/psi6-desktop/SKILL.md`。

核心：`App` 运行时（主题 `light`/`dark`/`auto`/文件或目录、`run(..., tray=True)` 托盘、默认防多开、记住窗口位置与最大化）；`TaskRunner`（`exclusive=` 单飞、`is_busy`）；`BatchToolWindow`（`icon=` / `exclusive=` / `present_outcome`）；窗壳 `DesktopWindow` + `TitleBar` + `TrayIcon.refresh`；主题 token + `icons/` 同名 svg。子控件靠布局挂父，不进布局的才写 parent；初始化可以 `hide()`，不要主动 `show()`。表单 `pydantic_form` / `pydantic_settings`。改控件用构造参数或子类钩子，不要改 `_` 私有成员。本仓库不提供业务模板，不为某个产品堆叠首页主键。

`file_index` 只示范 `run_job` 签名，不是要复制的行业模板。
