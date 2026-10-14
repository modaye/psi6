"""0.3 冻结的稳定公共接口。

这些名字的职责在 0.x 内保持不变。新增参数必须带默认值。
根包只导出本名单。控件在 ``psi6.ui``，可选批处理窗在 ``psi6.templates``。
模块名以 ``_`` 开头的是内部实现。

批处理只有一条执行路径：

- ``TaskRunner`` 提交、请求取消、等待线程池。它不导入 UI。
- ``TaskHandle.cancel_requested`` 表示已请求取消。``TaskHandle.status`` 要等工作函数结束后才变化。
- ``JobOutcome`` 只是成功后要填进表的数据，不是第二套状态。
- ``BatchToolWindow`` 调用 ``App.runner``，不自己调度。
"""

from __future__ import annotations

STABLE: tuple[tuple[str, str], ...] = (
    ("psi6", "App"),
    ("psi6", "TaskRunner"),
    ("psi6", "TaskHandle"),
    ("psi6", "TaskStatus"),
    ("psi6", "JobOutcome"),
    ("psi6", "Theme"),
    ("psi6", "Tokens"),
    ("psi6", "contrast_notes"),
    ("psi6", "DesktopWindow"),
    ("psi6", "TitleBar"),
    ("psi6", "TrayIcon"),
)

OPTIONAL_UI: tuple[tuple[str, str], ...] = (("psi6.templates", "BatchToolWindow"),)
