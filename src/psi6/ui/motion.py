"""属性和数值动画的唯一入口。

自绘控件需要「悬停颜色过渡」「按下反馈」「开关滑块滑动」这类短动画时走这里，
不要各自 ``QPropertyAnimation``。统一入口解决四件事：

1. **减少动效**：``Tokens.reduced_motion`` 打开或时长为 0 时直接置终值，不建动画对象。
2. **不叠加**：同一对象同一属性的旧动画先停，快速进出悬停不会抖。
3. **不被回收**：运行中的动画登记在模块级列表，``finished`` 后自动出队。
4. **时长来自 token**：``speed`` 只接受 ``fast`` / ``normal``，具体毫秒由主题决定。

数值动画（``animate_value``）覆盖「不是 Qt 属性、但需要逐帧回调」的场景，
例如 Toast 的展开高度；它用 ``QVariantAnimation``，同样尊重减少动效。
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager

from PySide6.QtCore import (
    QEasingCurve,
    QObject,
    QPropertyAnimation,
    QVariantAnimation,
)

from psi6.theme.runtime import token_ms

__all__ = [
    "animate",
    "animate_value",
    "easing",
    "motion_enabled",
    "stop",
    "stop_all",
]

# 运行中的动画。持有引用是必要的：Qt 只保存裸指针，Python 侧对象被回收时
# 动画会在下一帧崩掉。``finished`` 后从列表移除。
_RUNNING: list[QPropertyAnimation] = []
_RUNNING_VALUE: list[QVariantAnimation] = []

# 常用缓动。Qt 样式表没有 transition，短交互统一用「进入减速」。
_EASING = {
    "standard": QEasingCurve.Type.OutCubic,
    "enter": QEasingCurve.Type.OutCubic,
    "exit": QEasingCurve.Type.InCubic,
    "emphasized": QEasingCurve.Type.OutQuint,
    "in_out": QEasingCurve.Type.InOutCubic,
    "linear": QEasingCurve.Type.Linear,
}


def easing(name: str = "standard") -> QEasingCurve.Type:
    """缓动曲线。未知名称回落到 ``standard``（OutCubic）。"""

    return _EASING.get(str(name).strip().lower(), QEasingCurve.Type.OutCubic)


def motion_enabled() -> bool:
    """当前主题是否允许动画。``reduced_motion`` 为真或时长为 0 时为假。"""

    return token_ms("fast") > 0


def animate(
    obj: QObject,
    prop: str | bytes,
    start: float | int,
    end: float | int,
    *,
    speed: str = "fast",
    curve: str = "standard",
    duration: int | None = None,
    loop: int = 1,
    delay_ms: int = 0,
    on_finish: Callable[[], None] | None = None,
) -> QPropertyAnimation | None:
    """给 ``obj`` 的 Qt 属性做动画。

    ``speed`` 取 ``fast``（悬停、按下）或 ``normal``（位移、显隐），毫秒来自
    当前主题。``duration`` 给定时覆盖 ``speed``。减少动效或时长为 0 时直接把
    属性设成 ``end`` 并立即回调，返回 ``None``。

    ``delay_ms`` 大于 0 时先把属性设成 ``start``，到点再开始动画。
    ``loop`` 为负表示无限循环；循环动画请只在控件可见时启动。
    """

    name = prop.decode() if isinstance(prop, bytes) else prop
    key = name.encode()
    total = _duration(duration, speed)

    if total <= 0:
        stop(obj, name)
        obj.setProperty(name, end)
        if on_finish is not None:
            on_finish()
        return None

    stop(obj, name)
    animation = QPropertyAnimation(obj, key)
    animation.setDuration(total)
    animation.setStartValue(start)
    animation.setEndValue(end)
    animation.setEasingCurve(easing(curve))
    animation.setLoopCount(-1 if loop < 0 else max(1, loop))

    def _finished() -> None:
        if animation in _RUNNING:
            _RUNNING.remove(animation)
        if on_finish is not None:
            on_finish()

    animation.finished.connect(_finished)
    _RUNNING.append(animation)
    if delay_ms > 0:
        obj.setProperty(name, start)
        from PySide6.QtCore import QTimer

        QTimer.singleShot(delay_ms, animation.start)
    else:
        animation.start()
    return animation


def animate_value(
    parent: QObject,
    start: float,
    end: float,
    *,
    speed: str = "fast",
    curve: str = "standard",
    duration: int | None = None,
    on_value: Callable[[float], None],
    on_finish: Callable[[], None] | None = None,
) -> QVariantAnimation | None:
    """逐帧把一个浮点值交给回调。用于不是 Qt 属性的量（例如展开高度）。

    减少动效时只回调一次终值，不建动画。
    """

    total = _duration(duration, speed)
    if total <= 0:
        on_value(end)
        if on_finish is not None:
            on_finish()
        return None

    animation = QVariantAnimation(parent)
    animation.setDuration(total)
    animation.setStartValue(float(start))
    animation.setEndValue(float(end))
    animation.setEasingCurve(easing(curve))
    animation.valueChanged.connect(lambda value: on_value(float(value)))

    def _finished() -> None:
        if animation in _RUNNING_VALUE:
            _RUNNING_VALUE.remove(animation)
        if on_finish is not None:
            on_finish()

    animation.finished.connect(_finished)
    _RUNNING_VALUE.append(animation)
    animation.start()
    return animation


def stop(obj: QObject, prop: str | bytes | None = None) -> None:
    """停掉某对象上的动画。``prop`` 为空时停掉它的全部属性动画。"""

    key = None
    if prop is not None:
        key = prop.encode() if isinstance(prop, str) else prop
    for animation in list(_RUNNING):
        if animation.targetObject() is not obj:
            continue
        if key is not None and animation.propertyName() != key:
            continue
        animation.stop()
        if animation in _RUNNING:
            _RUNNING.remove(animation)


def stop_all() -> None:
    """停掉所有动画。主题切换或窗口关闭时用，避免动画指着已释放的控件。"""

    for animation in list(_RUNNING):
        animation.stop()
    _RUNNING.clear()
    for value_animation in list(_RUNNING_VALUE):
        value_animation.stop()
    _RUNNING_VALUE.clear()


@contextmanager
def paused(obj: QObject) -> Iterator[None]:
    """在这个块里停掉 ``obj`` 的动画，退出时不影响之后新建的动画。

    用于「先量尺寸再动画」这类需要中间帧稳定的场景。
    """

    stop(obj)
    yield


def _duration(duration: int | None, speed: str) -> int:
    """解析时长。显式 ``duration`` 优先，否则按 ``speed`` 取主题 token。"""

    if duration is not None:
        return max(0, int(duration))
    name = str(speed).strip().lower()
    return token_ms("fast" if name in {"fast", "instant", "quick"} else "normal")
