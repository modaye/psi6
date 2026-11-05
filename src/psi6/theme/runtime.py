"""运行时读当前主题。自定义控件从此取色、尺寸和时长，不要写十六进制 QSS。"""

from __future__ import annotations

from dataclasses import fields

from PySide6.QtWidgets import QApplication

from psi6.theme.tokens import DEFAULT_TOKENS, Tokens, style_metrics


def property_name(field: str) -> str:
    """``color_text`` → ``psi6ColorText``。"""

    return "psi6" + "".join(part.capitalize() for part in field.split("_"))


def publish_tokens(app: QApplication, tokens: Tokens) -> None:
    """把全部 token 写到 ``QApplication`` 属性，供自绘控件读取。"""

    for item in fields(tokens):
        if item.name == "icons":
            continue
        app.setProperty(property_name(item.name), getattr(tokens, item.name))


def token_color(name: str) -> str:
    """当前主题色。``name`` 为 ``primary`` / ``color_primary`` / ``border`` 等。"""

    field = name if name.startswith("color_") else f"color_{name}"
    default = getattr(DEFAULT_TOKENS, field, "")
    if not isinstance(default, str):
        return ""
    app = QApplication.instance()
    if app is None:
        return default
    value = app.property(property_name(field))
    return value if isinstance(value, str) and value else default


def token_int(name: str, default: int | None = None) -> int:
    """当前主题整数度量。``name`` 为 ``control_height`` / ``icon_size`` 等。"""

    fallback = default if default is not None else getattr(DEFAULT_TOKENS, name, 0)
    if not isinstance(fallback, int):
        fallback = 0
    app = QApplication.instance()
    if app is None:
        return fallback
    value = app.property(property_name(name))
    if isinstance(value, int):
        return value
    return fallback


def metrics_scale() -> float:
    """当前控件高度相对 ``modern`` 预设的比例，用来缩放没有对应 token 的尺寸。

    ``modern`` 为 ``1.0``，``compact`` 约 ``0.83``；自定义组件里那些写死的
    留白、图标边长可以按这个比例缩放，切密度时不必再逐个定义新 token。
    比例钳在 ``0.5`` ~ ``2.0``，异常主题不会把布局压塌或撑爆。
    """

    modern = style_metrics("modern")["control_height"]
    return max(0.5, min(2.0, token_int("control_height", modern) / max(1, modern)))


def token_ms(speed: str = "fast") -> int:
    """动画时长（毫秒）。``reduced_motion`` 或时长 ``0`` 表示关掉动画。"""

    if token_int("reduced_motion") > 0:
        return 0
    field = "motion_fast_ms" if speed == "fast" else "motion_ms"
    return max(0, token_int(field))
