"""应用自己的主题。字段名必须是 Tokens 的字段。"""

from psi6 import Theme


class Desk(Theme):
    """深色底，只改强调色。"""

    name = "desk"
    base = "dark"
    color_primary = "#4d7c5a"
