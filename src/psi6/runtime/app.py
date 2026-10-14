"""应用入口：QApplication、主题、异常钩子、任务运行器、通知与配置。"""

from __future__ import annotations

import sys
import threading
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
from psi6.theme.theme import Theme
from psi6.theme.tokens import Tokens, resolve_tokens
from psi6.ui.desktop_window import DesktopWindow
from psi6.ui.toast import ToastHost
from psi6.ui.tray import TrayIcon

T = TypeVar("T", bound=BaseModel)


class App:
    """进程内桌面应用入口。业务代码不再手写 ``QApplication(sys.argv)``。

    ``theme`` 取 ``light`` / ``dark`` / ``auto``，或一个 ``Theme`` 子类 / 实例 / ``Tokens``。
    默认允许多开。单实例、记住窗口位置都要显式传给 ``run``。
    """

    def __init__(
        self,
        name: str,
        *,
        organization: str = "psi6",
        theme: str | Tokens | Theme | type[Theme] | None = None,
        tokens: Tokens | None = None,
        config_root: Path | None = None,
    ) -> None:
        self.name = name
        self.organization = organization
        self._theme_spec: str | Tokens | Theme | type[Theme] | None = theme
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
        self._restore_geometry = False
        self._executing = False
        self._ensure()

    def _ensure(self) -> QApplication:
        if threading.current_thread() is not threading.main_thread():
            raise RuntimeError("App 只能在主线程创建，并在主线程调用 run")
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
        if self._restore_geometry and self._window is not None:
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

    def set_theme(self, theme: str | Tokens | Theme | type[Theme]) -> None:
        """运行中切换 ``light`` / ``dark`` / ``auto``，或一个 ``Theme`` / ``Tokens``。"""

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
        single_instance: bool = False,
        restore_geometry: bool = False,
    ) -> int:
        """套用主题、安装异常钩子、绑定状态栏、显示窗口并进入事件循环。

        默认允许多个进程同时运行，也不写窗口位置。
        ``single_instance=True`` 时，第二份进程唤醒已有窗口后退出。
        ``restore_geometry=True`` 时，启动恢复上次位置与最大化，退出时写回 ``window.json``。
        ``tray=True`` 且系统有托盘时，关闭主窗口隐藏而不是退出。
        没有托盘时关闭仍结束进程。关闭窗口不取消任务；退出时才按
        几何、任务、单实例锁、托盘的顺序收尾。

        必须在主线程调用。事件循环未退出时不能再次 ``run``。
        已有 ``QApplication`` 时复用，不新建第二个。
        """

        if self._executing:
            raise RuntimeError("App.run 不能在事件循环里再次调用")
        app = self._ensure()
        if not self._open(
            window,
            tray=tray,
            single_instance=single_instance,
            restore_geometry=restore_geometry,
        ):
            return 0
        self._executing = True
        try:
            window.show()
            return app.exec()
        finally:
            self._executing = False

    def _open(
        self,
        window: QWidget,
        *,
        tray: bool,
        single_instance: bool,
        restore_geometry: bool,
    ) -> bool:
        """绑定单实例、几何、托盘和通知。第二实例返回 False，此时不显示窗口。

        系统没有托盘时仍创建 ``TrayIcon``，但它是空操作：不把关闭改成隐藏，
        也不关掉「最后一个窗口关闭即退出」。
        """

        app = self._ensure()
        self._restore_geometry = False
        if single_instance:
            lock = SingleInstance(instance_key(self.organization, self.name), parent=app)
            if not lock.try_acquire():
                lock.notify_existing()
                return False
            lock.activated.connect(lambda: raise_window(window))
            self._instance = lock
        if restore_geometry:
            restore_window(window, self.store, self.name)
            self._restore_geometry = True
        self._window = window
        if tray:
            icon = window.title_bar.icon_name if isinstance(window, DesktopWindow) else "grid"
            self.tray = TrayIcon(window, tooltip=self.name, icon=icon, parent=app)
            if self.tray.available:
                app.setQuitOnLastWindowClosed(False)
        if isinstance(window, QMainWindow):
            self.notifier.bind_status_bar(window.statusBar())
            anchor = window.centralWidget() or window
        else:
            anchor = window
        self.notifier.bind_toast_host(ToastHost(anchor))
        install_exception_hooks(app, parent=window, notifier=self.notifier)
        return True


def raise_window(window: QWidget) -> None:
    """把已有窗口从托盘或最小化里拉回来。"""

    window.show()
    window.setWindowState(window.windowState() & ~Qt.WindowState.WindowMinimized)
    window.raise_()
    window.activateWindow()
