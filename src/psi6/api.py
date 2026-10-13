"""0.2 冻结的稳定公共接口。

``STABLE`` 中的名字在 0.x 内保持职责不变。新增参数必须带默认值。
``psi6`` 顶层还导出其它控件，可以直接用，但不在这份冻结名单里。
模块名以 ``_`` 开头的是内部实现。

批处理只有一条执行路径：

- ``TaskRunner`` 提交、取消、等待线程池。
- ``TaskHandle`` 与 ``TaskStatus`` 表示这一次执行的状态。
- ``JobOutcome`` 只是成功后要填进表的数据，不是第二套状态。
- ``BatchToolWindow`` 是可选界面。它调用 ``App.runner``，不自己调度。
"""

from __future__ import annotations

STABLE: tuple[tuple[str, str], ...] = (
    ("psi6", "App"),
    ("psi6", "TaskRunner"),
    ("psi6", "TaskHandle"),
    ("psi6", "TaskStatus"),
    ("psi6", "JobOutcome"),
    ("psi6.theme", "Theme"),
    ("psi6.theme", "Tokens"),
    ("psi6.theme", "contrast_notes"),
    ("psi6", "DesktopWindow"),
    ("psi6", "TitleBar"),
    ("psi6", "TrayIcon"),
)

OPTIONAL_UI: tuple[str, ...] = ("BatchToolWindow",)
