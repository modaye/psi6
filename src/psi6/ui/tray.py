"""系统托盘：显示 / 隐藏主窗口。退出必须结束进程，不能只关窗口。"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon, QWidget

from psi6.icons.render import icon_for
from psi6.theme.runtime import token_int
from psi6.ui.desktop_window import DesktopWindow
from psi6.ui.icon import token_color


class TrayIcon(QObject):
    """把主窗口接到托盘。系统没有托盘时构造为空操作。

    菜单不能挂在主窗口上：窗口 hide 之后，原生托盘菜单点「退出」会丢槽。
    「退出」用队列连接，避免在菜单回调里拆掉自己。
    换主题后调用 ``refresh`` 重绘图标；窗体 PaletteChange 也会自动刷新。
    """

    def __init__(
        self,
        window: QWidget,
        *,
        tooltip: str,
        icon: str = "grid",
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._window = window
        self._icon_name = icon
        self._tooltip = tooltip
        self._tray: QSystemTrayIcon | None = None
        self._menu: QMenu | None = None
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        tray = QSystemTrayIcon(self._make_icon(), self)
        tray.setToolTip(tooltip)
        menu = QMenu()
        show_action = QAction("显示窗口", menu)
        show_action.triggered.connect(self.show_window)
        hide_action = QAction("隐藏窗口", menu)
        hide_action.triggered.connect(window.hide)
        quit_action = QAction("退出", menu)
        quit_action.triggered.connect(self.quit, Qt.ConnectionType.QueuedConnection)
        menu.addAction(show_action)
        menu.addAction(hide_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        tray.setContextMenu(menu)
        tray.activated.connect(self._on_activated)
        tray.show()
        self._tray = tray
        self._menu = menu
        window.installEventFilter(self)
        if isinstance(window, DesktopWindow):
            window.close_to_tray = True

    @property
    def available(self) -> bool:
        return self._tray is not None

    @property
    def icon_name(self) -> str:
        return self._icon_name

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # type: ignore[override]
        if watched is self._window and event.type() in {
            QEvent.Type.PaletteChange,
            QEvent.Type.StyleChange,
        }:
            self.refresh()
        return super().eventFilter(watched, event)

    def _make_icon(self) -> QIcon:
        color = token_color(self._window)
        return icon_for(self._icon_name, color=color, size=token_int("icon_size", 16))

    def refresh(self) -> None:
        """按当前 token 重绘托盘图标。无托盘时为空操作。"""

        if self._tray is not None:
            self._tray.setIcon(self._make_icon())

    def set_icon(self, name: str) -> None:
        self._icon_name = name
        self.refresh()

    def set_tooltip(self, tooltip: str) -> None:
        self._tooltip = tooltip
        if self._tray is not None:
            self._tray.setToolTip(tooltip)

    def show_window(self) -> None:
        window = self._window
        window.show()
        window.setWindowState(window.windowState() & ~Qt.WindowState.WindowMinimized)
        window.raise_()
        window.activateWindow()

    def quit(self) -> None:
        """隐藏托盘并结束事件循环。标题栏关闭只是 hide，不会走到这里。"""

        if self._tray is not None:
            self._tray.hide()
            self._tray.setContextMenu(None)
        window = self._window
        if isinstance(window, DesktopWindow):
            window.request_quit()
        elif window is not None:
            window.close()
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def show_message(self, title: str, body: str) -> None:
        if self._tray is not None:
            self._tray.showMessage(title, body, QIcon(), 2500)

    def hide(self) -> None:
        if self._tray is not None:
            self._tray.hide()

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in {
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        }:
            if self._window.isVisible():
                self._window.hide()
            else:
                self.show_window()
