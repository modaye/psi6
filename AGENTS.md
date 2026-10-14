# psi6

psi6 是给编码 Agent 用的 PySide6 桌面框架。根包只导出 `psi6.api.STABLE`：`App`、`TaskRunner`、`TaskHandle`、`TaskStatus`、`JobOutcome`、`Theme`、`Tokens`、`contrast_notes`、`DesktopWindow`、`TitleBar`、`TrayIcon`。控件从 `psi6.ui` 导入。`BatchToolWindow` 在 `psi6.templates`，调度仍走 `TaskRunner`。`cancel()` 只是请求，结束看 `TaskHandle.status`。默认多开；`single_instance=True` 才加锁。关闭窗口不取消任务，应用退出才收尾。没有托盘时关闭仍退出。主题用 `Theme` 子类；结构错误抛错，对比度用 `contrast_notes`。`App` 只在主线程使用。写或改桌面工具时先读 `skills/psi6-desktop/SKILL.md`。迁到 0.3 见 `MIGRATION.md`。

核心：`App` 运行时（主题 `light`/`dark`/`auto` 或 `Theme` 子类；`run(..., tray=True)` 托盘；多开为默认，`single_instance=True` / `restore_geometry=True` 才加锁或记位置）；`TaskRunner` 执行任务（`exclusive=` / `is_busy` / `TaskHandle`）；`JobOutcome` 只是批处理表格结果；`BatchToolWindow` 使用同一个 runner；窗壳 `DesktopWindow` + `TitleBar` + `TrayIcon.refresh`；主题 token 用 Python 类声明，图标放主题模块旁 `icons/`。子控件靠布局挂父，不进布局的才写 parent；初始化可以 `hide()`，不要主动 `show()`。表单 `pydantic_form` / `pydantic_settings`。改控件用构造参数或子类钩子，不要改 `_` 私有成员。本仓库不提供业务模板，不为某个产品堆叠首页主键。

`file_index` 只示范 `run_job` 签名，不是要复制的行业模板。
