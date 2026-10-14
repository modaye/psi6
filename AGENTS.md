# psi6

psi6 是给编码 Agent 用的 PySide6 桌面框架。根包只导出 `psi6.api.STABLE`：`App`、`TaskRunner`、`TaskHandle`、`TaskStatus`、`JobOutcome`、`Theme`、`Tokens`、`contrast_notes`、`DesktopWindow`、`TitleBar`、`TrayIcon`。控件从 `psi6.ui` 导入。不提供整页批处理窗，也不提供把开始、取消和进度排成一行的任务条。`DesktopWindow` 默认用 Qt 标题栏，`frameless=True` 才自绘。进度没有指定位置时用 `StatusProgress(window.statusBar())`。`cancel()` 只是请求，结束看 `TaskHandle.status`。默认多开；`single_instance=True` 才加锁。关闭窗口不取消任务，应用退出才收尾。没有托盘时关闭仍退出。浅色主题背景是纯白。主题用 `Theme` 子类；`base` 选配色，`style` 选 `modern` 或 `compact`。结构错误抛错，对比度用 `contrast_notes`。`App` 只在主线程使用。写或改桌面工具时先读 `skills/psi6-desktop/SKILL.md`。迁移见 `MIGRATION.md`。

核心：`App` 运行时（主题 `light`/`dark`/`auto` 或 `Theme` 子类；`run(..., tray=True)` 托盘；多开为默认，`single_instance=True` / `restore_geometry=True` 才加锁或记位置）；`TaskRunner` 执行任务（`exclusive=` / `is_busy` / `TaskHandle`）；`JobOutcome` 只是批处理表格结果；窗壳默认 `DesktopWindow`，自绘标题栏要 `frameless=True`；`TrayIcon.refresh`；主题 token 用 Python 类声明，图标放主题模块旁 `icons/`。子控件靠布局挂父，不进布局的才写 parent；初始化可以 `hide()`，不要主动 `show()`。表单 `pydantic_form` / `pydantic_settings`。改控件用构造参数或子类钩子，不要改 `_` 私有成员。本仓库不提供业务模板，不为某个产品堆叠首页主键。

`file_index` 只示范 `run_job` 签名和整页组合，不是要复制的行业模板。新项目复制 `skills/psi6-desktop/template/`，业务写在 `job.py`，在该目录执行 `python app.py --check`。关窗口不取消任务；取消按钮只发请求；应用退出才 `shutdown`。没有托盘时，关最后一个窗口会退出进程。
