"""判断 Qt 对象是否还能调用。窗口销毁后的回调用它跳过界面更新。"""

from __future__ import annotations


def qt_alive(obj: object) -> bool:
    """C++ 对象已销毁时返回 False。非 Qt 对象视为可用。"""

    try:
        from shiboken6 import isValid
    except ImportError:
        return True
    try:
        return bool(isValid(obj))
    except (TypeError, RuntimeError):
        return True
