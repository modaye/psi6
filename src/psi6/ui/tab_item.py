"""文档标签的数据，以及宽度、关闭按钮、修改点的纯规则。

``TabView`` 持有这些数据。绘制层只问规则，不自己决定什么时候该画叉。
"""

from __future__ import annotations

from dataclasses import dataclass

MIN_TAB_WIDTH = 112
PREFERRED_TAB_WIDTH = 180
MAX_TAB_WIDTH = 240


@dataclass
class TabItem:
    """一份打开的文档在标签条上的样子。控件本身不放在这里。"""

    key: str
    title: str
    icon: str = ""
    path: str = ""
    modified: bool = False
    pinned: bool = False


def tab_width(text_px: int, *, has_icon: bool) -> int:
    """标签逻辑宽度。短标题用 180，长标题放到 240 为止，再长就省略。"""

    chrome = 44 + (20 if has_icon else 0)
    natural = chrome + max(0, int(text_px))
    return max(MIN_TAB_WIDTH, min(MAX_TAB_WIDTH, max(PREFERRED_TAB_WIDTH, natural)))


def close_visible(
    *,
    closable: bool,
    pinned: bool,
    selected: bool,
    hovered: bool,
    modified: bool,
) -> bool:
    """关闭按钮何时出现。固定标签不在条上画叉，仍可由菜单关闭。"""

    if not closable or pinned:
        return False
    if hovered:
        return True
    return selected and not modified


def modified_dot_visible(*, modified: bool, showing_close: bool) -> bool:
    """修改点和关闭按钮共用右侧位置。悬停出叉时，点让开。"""

    return modified and not showing_close
