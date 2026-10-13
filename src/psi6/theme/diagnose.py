"""主题诊断。结构错误在加载时抛出；这里只报告观感问题，不阻止使用。"""

from __future__ import annotations

from psi6.theme.tokens import Tokens


def contrast_notes(tokens: Tokens) -> list[str]:
    """正文与背景对比度低于 4.5 时返回说明。无法解析的颜色跳过。"""

    ratio = _contrast(tokens.color_text, tokens.color_bg)
    if ratio is None or ratio >= 4.5:
        return []
    return [f"正文与背景对比度 {ratio:.1f}，低于 4.5。这是诊断，不阻止加载主题。"]


def _contrast(foreground: str, background: str) -> float | None:
    fore = _luminance(foreground)
    back = _luminance(background)
    if fore is None or back is None:
        return None
    lighter, darker = max(fore, back), min(fore, back)
    return (lighter + 0.05) / (darker + 0.05)


def _luminance(color: str) -> float | None:
    text = color.strip()
    if not text.startswith("#") or len(text) not in {4, 7}:
        return None
    if len(text) == 4:
        text = "#" + "".join(ch * 2 for ch in text[1:])
    try:
        red = int(text[1:3], 16) / 255
        green = int(text[3:5], 16) / 255
        blue = int(text[5:7], 16) / 255
    except ValueError:
        return None
    channels = tuple(_channel(item) for item in (red, green, blue))
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def _channel(value: float) -> float:
    if value <= 0.04045:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4
