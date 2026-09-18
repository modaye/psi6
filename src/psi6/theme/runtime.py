"""运行时读当前主题。自定义控件从此取色、尺寸和时长，不要写十六进制 QSS。"""

from __future__ import annotations

from dataclasses import fields

from PySide6.QtWidgets import QApplication

from psi6.theme.tokens import DEFAULT_TOKENS, Tokens


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


def token_ms(speed: str = "fast") -> int:
    """动画时长（毫秒）。``reduced_motion`` 或时长 ``0`` 表示关掉动画。"""

    if token_int("reduced_motion") > 0:
        return 0
    field = "motion_fast_ms" if speed == "fast" else "motion_ms"
    return max(0, token_int(field))
