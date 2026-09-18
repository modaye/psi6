"""读取操作系统浅色/深色偏好。须在 ``QGuiApplication`` 创建之后调用。"""

from __future__ import annotations


def system_prefers_dark() -> bool:
    """当前系统颜色方案是否为深色。没有 GUI 应用时视为浅色。"""

    from PySide6.QtCore import Qt
    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication.instance()
    if app is None:
        return False
    return app.styleHints().colorScheme() == Qt.ColorScheme.Dark
