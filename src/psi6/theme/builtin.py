"""随包提供的 Python 主题。业务皮肤应在应用仓库里子类化 ``Theme``。"""

from __future__ import annotations

from psi6.theme.theme import Theme


class ModernDark(Theme):
    """现代度量配默认深色。"""

    name = "modern-dark"
    base = "dark"
    style = "modern"


class CompactDark(Theme):
    """紧凑度量配默认深色。"""

    name = "compact-dark"
    base = "dark"
    style = "compact"


class Mono(Theme):
    """黑白极简：锌灰中性色，主按钮近黑。适合内容为主的窗口。"""

    name = "mono"
    base = "light"
    color_surface = "#fafafa"
    color_sunken = "#f4f4f5"
    color_hover = "#eaeaed"
    color_text = "#19191d"
    color_muted = "#66666f"
    color_border = "#dedee2"
    color_border_subtle = "#ececef"
    color_disabled = "#a3a3ab"
    color_primary = "#1a1a1e"
    color_on_primary = "#fafafa"
    color_focus = "#6b6b76"
    color_info = "#2f6f9f"
    color_overlay = "rgba(240, 240, 242, 215)"
    color_sidebar = "#f5f5f6"
    color_sidebar_text = "#4a4a52"
    color_user_bubble = "#1a1a1e"
    color_user_on_bubble = "#fafafa"


class Obsidian(Theme):
    """深黑底 + 靛紫主色。适合夜间使用的多面板工作台。"""

    name = "obsidian"
    base = "dark"
    color_bg = "#0d0e14"
    color_surface = "#151722"
    color_elevated = "#1c1f2e"
    color_sunken = "#08090e"
    color_hover = "#242838"
    color_text = "#e9eaf4"
    color_muted = "#969cb4"
    color_border = "#2b3045"
    color_border_subtle = "#20242f"
    color_disabled = "#5f6579"
    color_primary = "#7c74f0"
    color_on_primary = "#0e0f1a"
    color_danger = "#e5696f"
    color_success = "#4fb583"
    color_warning = "#d9a24f"
    color_info = "#6fa3d8"
    color_focus = "#938df5"
    color_overlay = "rgba(13, 14, 20, 220)"
    color_sidebar = "#0a0b10"
    color_sidebar_text = "#a2a8c0"
    color_user_bubble = "#403a80"
    color_user_on_bubble = "#eceafc"


class Pine(Theme):
    """墨绿底 + 青绿主色。安静的深色工具配色。"""

    name = "pine"
    base = "dark"
    color_bg = "#0e1310"
    color_surface = "#141b17"
    color_elevated = "#1a231e"
    color_sunken = "#090d0a"
    color_hover = "#212c25"
    color_text = "#e6efe8"
    color_muted = "#93a89b"
    color_border = "#2a3a30"
    color_border_subtle = "#1f2a24"
    color_disabled = "#5f7367"
    color_primary = "#62b58e"
    color_on_primary = "#0c130e"
    color_danger = "#e26d66"
    color_warning = "#d3a557"
    color_info = "#6aa8cf"
    color_focus = "#7cc7a2"
    color_overlay = "rgba(14, 19, 16, 220)"
    color_sidebar = "#0b0f0c"
    color_sidebar_text = "#9fb3a6"
    color_user_bubble = "#2c523f"
    color_user_on_bubble = "#e8f4ec"


class Brass(Theme):
    """黄铜工作台，供组件预览切换。"""

    name = "brass"
    base = "light"
    color_bg = "#f3efe6"
    color_surface = "#fbf7ee"
    color_sunken = "#fffdf8"
    color_hover = "#e7dfd0"
    color_text = "#2a241c"
    color_muted = "#6f6558"
    color_border = "#d4cbb8"
    color_primary = "#6b542e"
    color_on_primary = "#fbf7ee"
    color_focus = "#6b542e"
    color_sidebar = "#e9e1d2"
    color_sidebar_text = "#5a5144"
    color_user_bubble = "#6b542e"
    color_info = "#4d5f6e"


class Compact(Theme):
    """紧凑度量。只改尺寸，配色仍跟 ``base``。"""

    name = "compact"
    base = "light"
    style = "compact"
