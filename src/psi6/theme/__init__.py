"""主题：token 与应用入口。"""

from psi6.theme.apply import apply_theme, build_font, build_stylesheet, font_families
from psi6.theme.builtin import (
    Brass,
    Compact,
    CompactDark,
    ModernDark,
    Mono,
    Obsidian,
    Pine,
    builtin_themes,
)
from psi6.theme.diagnose import contrast_notes
from psi6.theme.paint import as_color, color_alpha, create_painter, mix_color, rounded_rect_path
from psi6.theme.runtime import token_color, token_int, token_ms
from psi6.theme.theme import Theme, follows_system, theme_key
from psi6.theme.tokens import DEFAULT_TOKENS, Tokens, resolve_tokens, style_metrics

__all__ = [
    "DEFAULT_TOKENS",
    "Brass",
    "Compact",
    "CompactDark",
    "ModernDark",
    "Mono",
    "Obsidian",
    "Pine",
    "Theme",
    "Tokens",
    "apply_theme",
    "as_color",
    "build_font",
    "build_stylesheet",
    "builtin_themes",
    "color_alpha",
    "contrast_notes",
    "create_painter",
    "follows_system",
    "font_families",
    "mix_color",
    "resolve_tokens",
    "rounded_rect_path",
    "style_metrics",
    "theme_key",
    "token_color",
    "token_int",
    "token_ms",
]
