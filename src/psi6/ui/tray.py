"""系统托盘：显示 / 隐藏主窗口。退出必须结束进程，不能只关窗口。"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon, QWidget

from psi6.icons.render import device_ratio, icon_for
from psi6.theme.runtime import token_int
from psi6.ui.desktop_window import DesktopWindow
from psi6.ui.icon import token_color
from psi6.ui.window_presence import (
    present_window,
    quit_application,
    toggle_window,
    window_is_presented,
)

# 气泡是系统通知，不是界面动画，不占用 motion token。
_BALLOON_MS = 2500


class TrayIcon(QObject):
    """把主窗口接到托盘。系统没有托盘时构造为空操作。

    菜单不能挂在主窗口上：窗口 hide 之后，原生托盘菜单点「退出」会丢槽。
    「退出」和追加的菜单项用队列连接，避免在菜单回调里拆掉自己。
    左键只认单击。Windows 上双击会先发单击再发双击，两处都切换会立刻弹回。
    最小化时 ``isVisible()`` 仍为真，单击改为展开，而不是再藏一次。
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
        self._status = ""
        self._tray: QSystemTrayIcon | None = None
        self._menu: QMenu | None = None
        self._show_action: QAction | None = None
        self._hide_action: QAction | None = None
        self._quit_action: QAction | None = None
        self._extra_anchor: QAction | None = None
        self._icon_actions: list[tuple[QAction, str, str]] = []
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        tray = QSystemTrayIcon(self._make_icon(), self)
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
        menu.aboutToShow.connect(self._sync_menu)
        tray.setContextMenu(menu)
        tray.activated.connect(self._on_activated)
        tray.show()
        self._tray = tray
        self._menu = menu
        self._show_action = show_action
        self._hide_action = hide_action
        self._quit_action = quit_action
        self._remember_icon(show_action, "monitor", "neutral")
        self._remember_icon(hide_action, "win-min", "neutral")
        self._remember_icon(quit_action, "win-close", "error")
        self._apply_tooltip()
        window.installEventFilter(self)
        if isinstance(window, DesktopWindow):
            window.close_to_tray = True

    @property
    def available(self) -> bool:
        return self._tray is not None

    @property
    def icon_name(self) -> str:
        return self._icon_name

    @property
    def status(self) -> str:
        return self._status

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # type: ignore[override]
        if watched is self._window and event.type() in {
            QEvent.Type.PaletteChange,
            QEvent.Type.StyleChange,
        }:
            self.refresh()
        return super().eventFilter(watched, event)

    def _make_icon(self) -> QIcon:
        color = token_color(self._window)
        return icon_for(
            self._icon_name, color=color, size=token_int("icon_size", 16), ratio=device_ratio()
        )

    def refresh(self) -> None:
        """按当前 token 重绘托盘图标和菜单图标。无托盘时为空操作。"""

        if self._tray is not None:
            self._tray.setIcon(self._make_icon())
        for action, icon, tone in self._icon_actions:
            self._paint_action(action, icon, tone)

    def set_icon(self, name: str) -> None:
        self._icon_name = name
        self.refresh()

    def set_tooltip(self, tooltip: str) -> None:
        self._tooltip = tooltip
        self._apply_tooltip()

    def set_status(self, text: str) -> None:
        """在提示里附上短状态，例如任务进行中。空字符串回到原来的提示。"""

        self._status = text.strip()
        self._apply_tooltip()

    def add_action(self, label: str, callback: Callable[[], Any], *, icon: str = "") -> None:
        """在「退出」前追加一项。系统没有托盘时忽略。

        回调用队列连接：菜单还开着时不要拆托盘。回调不要接收参数。
        """

        menu = self._menu
        quit_action = self._quit_action
        if menu is None or quit_action is None:
            return
        if self._extra_anchor is None:
            self._extra_anchor = menu.insertSeparator(quit_action)
        action = QAction(label, menu)
        action.triggered.connect(
            lambda checked=False, fn=callback: fn(),
            Qt.ConnectionType.QueuedConnection,
        )
        menu.insertAction(self._extra_anchor, action)
        if icon:
            self._remember_icon(action, icon, "neutral")

    def show_window(self) -> None:
        present_window(self._window)

    def quit(self) -> None:
        """隐藏托盘并结束事件循环。标题栏关闭只是 hide，不会走到这里。"""

        if self._tray is not None:
            self._tray.hide()
            self._tray.setContextMenu(None)  # type: ignore[arg-type]
        quit_application(self._window)

    def show_message(self, title: str, body: str) -> None:
        """弹出系统气泡。图标用当前主题色，时长交给系统通知，不跟界面动画走。"""

        if self._tray is not None:
            self._tray.showMessage(title, body, self._make_icon(), _BALLOON_MS)

    def hide(self) -> None:
        if self._tray is not None:
            self._tray.hide()

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            toggle_window(self._window)

    def _sync_menu(self) -> None:
        presented = window_is_presented(self._window)
        if self._show_action is not None:
            self._show_action.setEnabled(not presented)
        if self._hide_action is not None:
            self._hide_action.setEnabled(presented)

    def _apply_tooltip(self) -> None:
        if self._tray is None:
            return
        tip = self._tooltip if not self._status else f"{self._tooltip}\n{self._status}"
        self._tray.setToolTip(tip)

    def _remember_icon(self, action: QAction, icon: str, tone: str) -> None:
        self._icon_actions.append((action, icon, tone))
        self._paint_action(action, icon, tone)

    def _paint_action(self, action: QAction, icon: str, tone: str) -> None:
        action.setIcon(
            icon_for(
                icon,
                color=token_color(self._window, tone=tone),
                size=token_int("icon_size", 16),
                ratio=device_ratio(),
            )
        )
