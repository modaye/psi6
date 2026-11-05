"""主题视觉回归：每套内置配色下，关键组件必须真的套上对应 token。

不依赖像素级基线（跨平台易碎），改为断言**不变量**：主按钮填充 ≈ ``color_primary``、
危险按钮填充 ≈ ``color_danger``。这类断言能抓住本次发现过的那类回归——切到深色主题后
主题化按钮仍停在浅色主题的配色（例如主按钮本该是 ``#6e9ff2`` 却仍是 ``#2b5cd7``）。
场景里还放了 ``QLineEdit`` / ``DataTable`` / ``TreeView``，作为换肤的冒烟覆盖（这些组件
也走按控件套样式表，同样可能被那类回归波及），但当前断言只聚焦最易出错的按钮。

运行：``uv run pytest tests/test_visual_regression.py``（已并入全量套件，CI 自动把关）。
"""

from __future__ import annotations

import os

# 仅声明 offscreen（conftest 已设，这里补 setdefault 是为了文件可单独收集）；
# 不要在这里设 QT_SCALE_FACTOR——模块在收集阶段被导入，会污染整个会话的
# 像素/几何断言测试（例如 test_theme 的箭头像素比对、test_app_runtime 的窗口几何）。
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QPoint
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLineEdit, QVBoxLayout, QWidget

from psi6.theme.apply import apply_theme
from psi6.theme.builtin import builtin_themes
from psi6.theme.tokens import Tokens
from psi6.ui.buttons import danger_button, primary_button
from psi6.ui.data_table import DataTable, TableColumn
from psi6.ui.tree_view import TreeColumn, TreeNode, TreeView

# 覆盖 light + 全部深色/特殊配色
THEMES = [
    "light",
    "modern-dark",
    "compact-dark",
    "obsidian",
    "pine",
    "brass",
    "mono",
    "compact",
]


def _resolve(name: str) -> tuple[Tokens, bool]:
    """返回 (tokens, is_dark)。``Tokens`` 本身没有 ``base`` 字段，是否深色要回到 ``Theme`` 取。"""

    if name == "light":
        return Tokens.light(), False
    if name == "dark":
        return Tokens.dark(), True
    for cls in builtin_themes():
        if cls.name == name:
            return cls().tokens(), cls.base == "dark"
    raise KeyError(name)


def _dist(a: QColor, b: str) -> float:
    other = QColor(b)
    return (
        (a.red() - other.red()) ** 2
        + (a.green() - other.green()) ** 2
        + (a.blue() - other.blue()) ** 2
    ) ** 0.5


def _sample(scene: QWidget, child: QWidget, img, dpr: float, fx: float = 0.5) -> QColor:
    top_left = child.mapTo(scene, QPoint(0, 0))
    x = int((top_left.x() + child.width() * fx) * dpr)
    y = int((top_left.y() + child.height() * 0.5) * dpr)
    return img.pixelColor(x, y)


def _build_scene() -> QWidget:
    scene = QWidget()
    layout = QVBoxLayout(scene)
    row = QHBoxLayout()
    row.addWidget(primary_button("Primary"))
    row.addWidget(danger_button("Danger"))
    layout.addLayout(row)
    layout.addWidget(QLineEdit("sample input"))
    table = DataTable([TableColumn("name"), TableColumn("size")])
    table.set_rows([{"name": "a.txt", "size": 3}, {"name": "b.txt", "size": 8}])
    layout.addWidget(table)
    tree = TreeView([TreeColumn("name")])
    tree.set_nodes(
        [
            TreeNode(
                id="r",
                data={"name": "root"},
                children=[TreeNode(id="c", data={"name": "child"})],
            )
        ]
    )
    tree.expand_all()
    layout.addWidget(tree)
    return scene


@pytest.mark.parametrize("theme", THEMES)
def test_theme_tokens_are_applied_to_components(qapp: QApplication, qtbot, theme: str) -> None:
    tokens, is_dark = _resolve(theme)
    apply_theme(qapp, tokens)
    qtbot.wait(0)  # 冲掉主题应用产生的重绘事件（不用 processEvents，避免 PSI006）

    scene = _build_scene()
    qtbot.addWidget(scene)
    scene.show()
    qtbot.wait(0)  # 冲掉首帧绘制事件，grab 才能抓到已上色的控件

    img = scene.grab(scene.rect()).toImage()
    dpr = img.devicePixelRatio()

    buttons = scene.findChildren(QWidget)
    primary = next(b for b in buttons if b.objectName() == "psi6Primary")
    danger = next(b for b in buttons if b.objectName() == "psi6Danger")
    # 偏左取样，避开居中文字
    primary_color = _sample(scene, primary, img, dpr, fx=0.18)
    danger_color = _sample(scene, danger, img, dpr, fx=0.18)

    assert _dist(primary_color, tokens.color_primary) < 24, (
        f"[{theme}] 主按钮填充 {primary_color.name()} 偏离 color_primary {tokens.color_primary}"
    )
    assert _dist(danger_color, tokens.color_danger) < 24, (
        f"[{theme}] 危险按钮填充 {danger_color.name()} 偏离 color_danger {tokens.color_danger}"
    )

    # 深色基调下，主按钮不得还是浅色基调的蓝
    if is_dark:
        assert primary_color.name() != "#2b5cd7", (
            f"[{theme}] 深色主题主按钮仍是浅色基调的 #2b5cd7，主题未生效"
        )
