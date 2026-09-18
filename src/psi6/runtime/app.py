"""应用入口：QApplication、主题、异常钩子、任务运行器、通知与配置。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget

from psi6.runtime.config import ConfigStore
from psi6.runtime.errors import install_exception_hooks
from psi6.runtime.notifications import Notifier
from psi6.runtime.qt_env import install_app_fonts, install_qt_message_filter, prepare_qt_environment
from psi6.runtime.single_instance import SingleInstance, instance_key
from psi6.runtime.tasks import TaskRunner
from psi6.runtime.window_state import restore_window, save_window
from psi6.theme.apply import apply_theme
from psi6.theme.tokens import Tokens, resolve_tokens
from psi6.ui.desktop_window import DesktopWindow
from psi6.ui.toast import ToastHost
from psi6.ui.tray import TrayIcon

T = TypeVar("T", bound=BaseModel)


class App:
    """进程内桌面应用入口。业务代码不再手写 ``QApplication(sys.argv)``。

    ``theme`` 取 ``light`` / ``dark`` / ``auto``（跟系统），主题文件
    （``.json`` / ``.toml`` / ``.yaml``），或含 ``theme.toml`` + ``icons/`` 的目录。
    """

    def __init__(
        self,
        name: str,
        *,
        organization: str = "psi6",
        theme: str | Tokens | Path | None = None,
        tokens: Tokens | None = None,
        config_root: Path | None = None,
    ) -> None:
        self.name = name
        self.organization = organization
        self._theme_spec: str | Tokens | Path | None = theme
        self._tokens_override = tokens
        self._tokens = Tokens.light()
        self.store = ConfigStore(config_root)
        self.notifier = Notifier()
        self._qt_app: QApplication | None = None
        self._runner: TaskRunner | None = None
        self._quit_hooked = False
        self._scheme_bound = False
        self._instance: SingleInstance | None = None
        self.tray: TrayIcon | None = None
        self._window: QWidget | None = None
        self._ensure()

    def _ensure(self) -> QApplication:
        if self._qt_app is not None:
            return self._qt_app
        prepare_qt_environment()
        install_qt_message_filter()
        existing = QApplication.instance()
        if isinstance(existing, QApplication):
            self._qt_app = existing
        else:
            self._qt_app = QApplication(sys.argv)
        install_app_fonts()
        self._qt_app.setApplicationName(self.name)
        self._qt_app.setOrganizationName(self.organization)
        self._tokens = self._resolve_current()
        apply_theme(self._qt_app, self._tokens)
        self._watch_system_theme()
        if self._runner is None:
            self._runner = TaskRunner(parent=self._qt_app)
        if not self._quit_hooked:
            self._qt_app.aboutToQuit.connect(self._on_quit)
            self._quit_hooked = True
        return self._qt_app

    def _on_quit(self) -> None:
        if self._window is not None:
            save_window(self._window, self.store, self.name)
        if self._runner is not None:
            self._runner.shutdown()
        if self._instance is not None:
            self._instance.close()
        if self.tray is not None:
            self.tray.hide()

    @property
    def qt_app(self) -> QApplication:
        return self._ensure()

    @property
    def runner(self) -> TaskRunner:
        self._ensure()
        assert self._runner is not None
        return self._runner

    @property
    def tokens(self) -> Tokens:
        """当前已应用的视觉 token。"""

        return self._tokens

    def _resolve_current(self) -> Tokens:
        if self._tokens_override is not None:
            return self._tokens_override
        return resolve_tokens(self._theme_spec)

    def _watch_system_theme(self) -> None:
        if self._scheme_bound or self._qt_app is None:
            return
        self._qt_app.styleHints().colorSchemeChanged.connect(self._on_system_scheme)
        self._scheme_bound = True

    def _on_system_scheme(self, *_args: object) -> None:
        spec = self._theme_spec
        if isinstance(spec, str) and spec.lower() in {"auto", "system"}:
            self._tokens = resolve_tokens(spec)
            apply_theme(self.qt_app, self._tokens)
            self._refresh_shell()

    def set_theme(self, theme: str | Tokens | Path) -> None:
        """运行中切换浅色/深色、跟随系统、主题文件/目录或自定义 token。"""

        if isinstance(theme, Tokens):
            self._tokens_override = theme
            self._theme_spec = theme
        else:
            self._tokens_override = None
            self._theme_spec = theme
        self._tokens = self._resolve_current()
        apply_theme(self.qt_app, self._tokens)
        self._refresh_shell()

    def _refresh_shell(self) -> None:
        """主题切换后重绘托盘图标。标题栏与页内图标走 PaletteChange。"""

        if self.tray is not None:
            self.tray.refresh()

    def load_config(self, model_type: type[T]) -> T:
        """读取本应用的用户配置。"""

        return self.store.load(model_type, app_name=self.name)

    def save_config(self, model: BaseModel) -> None:
        """保存本应用的用户配置。"""

        self.store.save(model, app_name=self.name)

    def run(
        self,
        window: QWidget,
        *,
        tray: bool = False,
        single_instance: bool = True,
        restore_geometry: bool = True,
    ) -> int:
        """套用主题、安装异常钩子、绑定状态栏、显示窗口并进入事件循环。

        ``single_instance`` 默认开启：第二份进程会唤醒已有窗口然后退出。
        ``tray`` 把窗口接到系统托盘；关闭主窗口时隐藏而不是退出。
        ``restore_geometry`` 默认开启：恢复上次窗口位置与最大化状态。
        """

        app = self._ensure()
        self._window = window
        if restore_geometry:
            restore_window(window, self.store, self.name)
        if single_instance:
            lock = SingleInstance(instance_key(self.organization, self.name), parent=app)
            if not lock.try_acquire():
                lock.notify_existing()
                return 0
            lock.activated.connect(lambda: raise_window(window))
            self._instance = lock
        if tray:
            app.setQuitOnLastWindowClosed(False)
            icon = window.title_bar.icon_name if isinstance(window, DesktopWindow) else "grid"
            self.tray = TrayIcon(window, tooltip=self.name, icon=icon, parent=app)
        if isinstance(window, QMainWindow):
            self.notifier.bind_status_bar(window.statusBar())
            anchor = window.centralWidget() or window
        else:
            anchor = window
        self.notifier.bind_toast_host(ToastHost(anchor))
        install_exception_hooks(app, parent=window, notifier=self.notifier)
        window.show()
        return app.exec()


def raise_window(window: QWidget) -> None:
    """把已有窗口从托盘或最小化里拉回来。"""

    window.show()
    window.setWindowState(window.windowState() & ~Qt.WindowState.WindowMinimized)
    window.raise_()
    window.activateWindow()
