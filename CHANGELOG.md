# 变更

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
