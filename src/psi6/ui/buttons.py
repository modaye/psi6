"""主按钮、危险、幽灵描边、文字链。业务不要再写 objectName。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton, QWidget


def primary_button(text: str, parent: QWidget | None = None) -> QPushButton:
    """主题中的主按钮。"""

    button = QPushButton(text, parent)
    button.setObjectName("psi6Primary")
    return button


def danger_button(text: str, parent: QWidget | None = None) -> QPushButton:
    """主题中的危险/取消按钮。"""

    button = QPushButton(text, parent)
    button.setObjectName("psi6Danger")
    return button


def ghost_button(text: str, parent: QWidget | None = None) -> QPushButton:
    """描边浅底：返回、停止、选择图标、查看详情。"""

    button = QPushButton(text, parent)
    button.setObjectName("psi6Ghost")
    return button


def text_button(text: str, parent: QWidget | None = None) -> QPushButton:
    """无框文字链：粘贴代码、打开上次、打开位置。"""

    button = QPushButton(text, parent)
    button.setObjectName("psi6Link")
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setFlat(True)
    return button


link_button = text_button
