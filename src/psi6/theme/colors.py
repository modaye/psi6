"""颜色解析、混合与对比度。纯 Python，不依赖 Qt；token 推导和诊断共用。"""

from __future__ import annotations

import re

_HEX_RE = re.compile(r"^#([0-9A-Fa-f]+)$")
_FUNC_RE = re.compile(r"^rgba?\(([^)]*)\)$", re.IGNORECASE)
_RGBA = tuple[int, int, int, int]


def parse_color(value: str) -> _RGBA | None:
    """``#rgb`` / ``#rrggbb`` / ``#aarrggbb`` 或 ``rgb()`` / ``rgba()``。

    8 位 hex 按 Qt 的 ``#aarrggbb`` 顺序，不是 CSS 的 ``#rrggbbaa``。
    解析失败返回 ``None``。``rgba()`` 的 alpha 与 Qt 一致：整数按 0..255，
    带小数点的按 0..1。
    """

    if not isinstance(value, str):
        return None
    text = value.strip()
    hex_match = _HEX_RE.match(text)
    if hex_match is not None:
        digits = hex_match.group(1)
        if len(digits) == 3:
            digits = "ff" + "".join(ch * 2 for ch in digits)
        elif len(digits) == 6:
            digits = "ff" + digits
        elif len(digits) != 8:
            return None
        return (
            int(digits[2:4], 16),
            int(digits[4:6], 16),
            int(digits[6:8], 16),
            int(digits[0:2], 16),
        )
    func_match = _FUNC_RE.match(text)
    if func_match is None:
        return None
    parts = [item.strip() for item in func_match.group(1).split(",")]
    if len(parts) == 3:
        parts.append("255")
    if len(parts) != 4 or not all(parts):
        return None
    try:
        red = _channel(parts[0])
        green = _channel(parts[1])
        blue = _channel(parts[2])
        alpha = _alpha(parts[3])
    except ValueError:
        return None
    return (red, green, blue, alpha)


def is_color(value: str) -> bool:
    """``value`` 是否是主题能接受的色值。"""

    return parse_color(value) is not None


def mix_hex(start: str, end: str, amount: float) -> str:
    """线性混合两个颜色，返回小写 hex。``amount`` 为 0 时用 ``start``。"""

    first = parse_color(start)
    second = parse_color(end)
    if first is None or second is None:
        raise ValueError(f"无法混合颜色：{start!r} / {end!r}")
    t = max(0.0, min(1.0, amount))
    values = [int(a + (b - a) * t) for a, b in zip(first, second, strict=True)]
    return _to_hex((values[0], values[1], values[2], values[3]))


def contrast_ratio(foreground: str, background: str) -> float | None:
    """WCAG 对比度。半透明前景先叠到背景上，背景再叠到白底上。解析失败返回 ``None``。"""

    fore = parse_color(foreground)
    back = parse_color(background)
    if fore is None or back is None:
        return None
    base = _over(back, (255, 255, 255, 255))
    front = _over(fore, base)
    lighter, darker = sorted((_luminance(front), _luminance(base)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def _channel(text: str) -> int:
    if text.endswith("%"):
        return _clamp(round(float(text[:-1]) * 255 / 100))
    return _clamp(round(float(text)))


def _alpha(text: str) -> int:
    if text.endswith("%"):
        return _clamp(round(float(text[:-1]) * 255 / 100))
    if "." in text:
        value = float(text)
        if 0.0 <= value <= 1.0:
            return _clamp(round(value * 255))
        return _clamp(round(value))
    return _clamp(round(float(text)))


def _clamp(value: int) -> int:
    return max(0, min(255, value))


def _to_hex(color: _RGBA) -> str:
    red, green, blue, alpha = color
    if alpha >= 255:
        return f"#{red:02x}{green:02x}{blue:02x}"
    return f"#{alpha:02x}{red:02x}{green:02x}{blue:02x}"


def _over(top: _RGBA, bottom: _RGBA) -> _RGBA:
    top_alpha = top[3] / 255
    bottom_alpha = bottom[3] / 255
    alpha = top_alpha + bottom_alpha * (1 - top_alpha)
    if alpha <= 0:
        return (0, 0, 0, 0)
    channels = [
        round((top[index] * top_alpha + bottom[index] * bottom_alpha * (1 - top_alpha)) / alpha)
        for index in range(3)
    ]
    return (_clamp(channels[0]), _clamp(channels[1]), _clamp(channels[2]), round(alpha * 255))


def _luminance(color: _RGBA) -> float:
    red, green, blue, _ = color

    def linear(value: int) -> float:
        channel = value / 255
        if channel <= 0.04045:
            return channel / 12.92
        return ((channel + 0.055) / 1.055) ** 2.4

    return 0.2126 * linear(red) + 0.7152 * linear(green) + 0.0722 * linear(blue)
