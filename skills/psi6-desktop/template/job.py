"""应用自己的后台工作。复制模板后只改这个文件里的任务逻辑。

调度仍走 ``App.runner``。不要在这里创建窗口，也不要手写 ``QThread``。
"""

from __future__ import annotations

from psi6.runtime.logs import LogLevel, LogRecord


def run_job(*, on_progress, on_log, is_cancelled) -> str:
    """报告一步进度后返回。已请求取消时抛出 ``InterruptedError``。

    ``on_progress``、``on_log``、``is_cancelled`` 由 ``TaskRunner`` 注入。
    把行业逻辑放进这个函数；返回值交给页面的成功回调。
    """

    on_log(LogRecord(LogLevel.INFO, "开始"))
    on_progress(1, 1, "完成")
    if is_cancelled():
        raise InterruptedError
    return "完成"
