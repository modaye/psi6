"""主题诊断。结构错误在加载时抛出；这里只报告观感问题，不阻止使用。"""

from __future__ import annotations

from psi6.theme.colors import contrast_ratio
from psi6.theme.tokens import Tokens

# (标签, 前景字段, 背景字段, WCAG 阈值)。文字按正文级 4.5，焦点框按非文字 3.0。
_PAIRS: tuple[tuple[str, str, str, float], ...] = (
    ("正文与背景", "color_text", "color_bg", 4.5),
    ("正文与卡片", "color_text", "color_surface", 4.5),
    ("正文与浮层", "color_text", "color_elevated", 4.5),
    ("辅助文字与背景", "color_muted", "color_bg", 4.5),
    ("辅助文字与卡片", "color_muted", "color_surface", 4.5),
    ("主按钮文字", "color_on_primary", "color_primary", 4.5),
    ("危险按钮文字", "color_on_primary", "color_danger", 4.5),
    ("成功色文字", "color_on_primary", "color_success", 4.5),
    ("警告色文字", "color_on_primary", "color_warning", 4.5),
    ("信息色文字", "color_on_primary", "color_info", 4.5),
    ("侧栏文字", "color_sidebar_text", "color_sidebar", 4.5),
    ("用户气泡文字", "color_user_on_bubble", "color_user_bubble", 4.5),
    ("焦点框与背景", "color_focus", "color_bg", 3.0),
    ("焦点框与卡片", "color_focus", "color_surface", 3.0),
    ("错误色与背景", "color_danger", "color_bg", 4.5),
    ("错误色与卡片", "color_danger", "color_surface", 4.5),
)


def contrast_notes(tokens: Tokens) -> list[str]:
    """逐对检查语义文字、焦点框与底色。低于阈值时返回说明；无法解析的颜色跳过。"""

    notes: list[str] = []
    for label, foreground, background, threshold in _PAIRS:
        ratio = contrast_ratio(getattr(tokens, foreground), getattr(tokens, background))
        if ratio is None or ratio >= threshold:
            continue
        notes.append(f"{label}对比度 {ratio:.1f}，低于 {threshold:g}。这是诊断，不阻止加载主题。")
    return notes
