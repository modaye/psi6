"""主窗口的展开、隐藏和退出。托盘与悬浮球共用，避免两套点击语义。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget

from psi6.ui.desktop_window import DesktopWindow


def window_is_presented(window: QWidget) -> bool:
    """窗口正在前台展开。

    最小化时 ``isVisible()`` 仍为真。若把最小化当成已经打开，左键会把它藏起来，
    而不是拉回前台。
    """

    return window.isVisible() and not window.isMinimized()


def present_window(window: QWidget) -> None:
    """显示窗口、取消最小化，并把它带到前面。"""

    window.show()
    window.setWindowState(window.windowState() & ~Qt.WindowState.WindowMinimized)
    window.raise_()
    window.activateWindow()


def toggle_window(window: QWidget) -> None:
    """已展开则隐藏；不可见或最小化则拉回前台。"""

    if window_is_presented(window):
        window.hide()
    else:
        present_window(window)


def quit_application(window: QWidget) -> None:
    """关闭主窗口并结束进程。托盘和悬浮球的「退出」走这里。"""

    if isinstance(window, DesktopWindow):
        window.request_quit()
    else:
        window.close()
    app = QApplication.instance()
    if isinstance(app, QApplication):
        app.quit()
