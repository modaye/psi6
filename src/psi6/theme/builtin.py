"""随包提供的 Python 主题。业务皮肤应在应用仓库里子类化 ``Theme``。"""

from __future__ import annotations

from psi6.theme.theme import Theme


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
