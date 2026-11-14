"""应用入口：QApplication、主题、异常钩子、任务运行器、通知与配置。"""

from __future__ import annotations

import contextlib
import logging
import sys
import threading
import traceback
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel
from PySide6.QtCore import QEvent, QObject, QSettings, QTimer, Signal
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget

from psi6.runtime.config import ConfigStore
from psi6.runtime.errors import install_exception_hooks, uninstall_exception_hooks
from psi6.runtime.notifications import Notifier
from psi6.runtime.qt_env import install_app_fonts, install_qt_message_filter, prepare_qt_environment
from psi6.runtime.single_instance import SingleInstance, instance_key
from psi6.runtime.tasks import TaskRunner
from psi6.runtime.window_state import restore_window, save_window
from psi6.theme.apply import apply_theme
from psi6.theme.builtin import builtin_themes
from psi6.theme.theme import Theme, follows_system, theme_key
from psi6.theme.tokens import Tokens, resolve_tokens, style_metrics
from psi6.ui.desktop_window import DesktopWindow
from psi6.ui.float_ball import FloatBall
from psi6.ui.toast import ToastHost
from psi6.ui.tray import TrayIcon
from psi6.ui.window_presence import present_window

T = TypeVar("T", bound=BaseModel)

_SCHEMES = {"light", "dark", "auto", "system"}
_THEME_FILE = "theme.json"
_logger = logging.getLogger("psi6.runtime.app")

# 响应式密度：窗口可用空间不足时把 compact 尺寸预设压到当前主题上。
_DENSITY_MODES = {"auto", "modern", "compact"}
_DENSITY_DEBOUNCE_MS = 120
_COMPACT_MAX_WIDTH = 760
_COMPACT_MAX_HEIGHT = 540
_HIGH_DPI_SCALE = 1.25  # 高 DPI 屏物理尺寸通常更小，阈值放宽一档，更容易收紧


def _normalize_density(mode: str) -> str:
    """校验密度模式，返回小写名。"""

    name = str(mode).strip().lower()
    if name not in _DENSITY_MODES:
        raise ValueError(f"density 只能是 auto、modern 或 compact，收到 {mode!r}")
    return name


class _AppSignals(QObject):
    """``App`` 不是 ``QObject``，密度信号挂在这个内部对象上。"""

    density_changed = Signal(str)


class _WindowResizeWatcher(QObject):
    """监听主窗口 ``Resize``，交给 ``App`` 去抖后重新评估密度。

    事件过滤器里抛异常会污染 Qt 的事件派发（参见 Toast 段错误复盘），这里把回调包起来。
    """

    def __init__(self, on_resize: Callable[[], None], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._on_resize = on_resize

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        with contextlib.suppress(Exception):
            if event.type() == QEvent.Type.Resize:
                self._on_resize()
        return False


class App:
    """进程内桌面应用入口。业务代码不再手写 ``QApplication(sys.argv)``。

    ``theme`` 取 ``light`` / ``dark`` / ``auto``，注册过的主题名，或一个 ``Theme`` 子类 / 实例 / ``Tokens``。
    默认允许多开。单实例、记住窗口位置都要显式传给 ``run``。
    ``remember_theme=True`` 时，``set_theme`` 把选择写进 ``theme.json``，下次启动覆盖 ``theme`` 参数；
    只有注册过的主题（内置主题、``theme_choices``、``theme`` 与 ``set_theme`` 用过的 ``Theme``）才会被记住。

    ``density`` 是独立于配色的尺寸策略：``auto``（默认）在主窗口变小或高 DPI 时自动把
    ``compact`` 尺寸预设压到当前主题上，空间充足时沿用主题自带尺寸；``modern`` / ``compact``
    为手动固定。运行中可用 :meth:`set_density_mode` 切换，用 :attr:`density_changed` 订阅
    手动切换与窗口尺寸触发的自动翻转。

    ``focus_ring`` 默认 ``False``：不画焦点环，只抑制 Qt 的虚线框。
    需要对照键盘焦点时传 ``True`` 或调用 :meth:`set_focus_ring`。有的控件上环会显得脏。
    """

    def __init__(
        self,
        name: str,
        *,
        organization: str = "psi6",
        theme: str | Tokens | Theme | type[Theme] | None = None,
        tokens: Tokens | None = None,
        config_root: Path | None = None,
        remember_theme: bool = False,
        theme_choices: Sequence[type[Theme]] = (),
        density: str = "auto",
        compact_max_width: int = _COMPACT_MAX_WIDTH,
        compact_max_height: int = _COMPACT_MAX_HEIGHT,
        focus_ring: bool = False,
        reduced_motion: bool = False,
    ) -> None:
        self.name = name
        self.organization = organization
        self._theme_spec: str | Tokens | Theme | type[Theme] | None = theme
        self._tokens_override = tokens
        self._tokens = Tokens.light().resolve_states()
        self._remember_theme = remember_theme
        self._theme_registry: dict[str, type[Theme]] = {}
        for choice in (*builtin_themes(), *theme_choices):
            self._register_theme(choice)
        self._register_theme(theme)
        self.store = ConfigStore(config_root)
        self.notifier = Notifier()
        self._qt_app: QApplication | None = None
        self._runner: TaskRunner | None = None
        self._quit_hooked = False
        self._scheme_bound = False
        self._instance: SingleInstance | None = None
        self.tray: TrayIcon | None = None
        self.float_ball: FloatBall | None = None
        self._window: QWidget | None = None
        self._restore_geometry = False
        self._executing = False
        self._previous_quit_on_last_window_closed: bool | None = None
        self._density_mode = _normalize_density(density)
        self._focus_ring = bool(focus_ring)
        self._reduced_motion = bool(reduced_motion)
        self._compact_max_width = max(1, int(compact_max_width))
        self._compact_max_height = max(1, int(compact_max_height))
        self._applied_style: str | None = None
        self._geo_watcher: _WindowResizeWatcher | None = None
        self._density_timer: QTimer | None = None
        self._density_bound = False
        self._signals: _AppSignals | None = None
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
        if self._signals is None:
            self._signals = _AppSignals(self._qt_app)
        self._restore_theme()
        self._applied_style = self._effective_style()
        self._apply_tokens()
        self._watch_system_theme()
        if self._runner is None:
            self._runner = TaskRunner(parent=self._qt_app)
        if not self._quit_hooked:
            self._qt_app.aboutToQuit.connect(self._on_quit)
            self._quit_hooked = True
        return self._qt_app

    def _on_quit(self) -> None:
        """退出收尾。某一步失败或任务超时，后面的锁、托盘和悬浮球仍然释放。"""

        if self._restore_geometry and self._window is not None:
            try:
                save_window(self._window, self.store, self.name)
            except Exception:
                traceback.print_exc()
        if self._runner is not None:
            try:
                if not self._runner.shutdown():
                    sys.stderr.write("psi6: 退出时仍有任务未在时限内结束\n")
            except Exception:
                traceback.print_exc()
        if self._instance is not None:
            try:
                self._instance.close()
            except Exception:
                traceback.print_exc()
        if self.tray is not None:
            try:
                self.tray.hide()
            except Exception:
                traceback.print_exc()
        if self.float_ball is not None:
            try:
                self.float_ball.hide()
            except Exception:
                traceback.print_exc()
        if self._previous_quit_on_last_window_closed is not None and self._qt_app is not None:
            try:
                self._qt_app.setQuitOnLastWindowClosed(self._previous_quit_on_last_window_closed)
            except Exception:
                traceback.print_exc()
            self._previous_quit_on_last_window_closed = None
        try:
            uninstall_exception_hooks(self)
        except Exception:
            traceback.print_exc()

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

    @property
    def focus_ring(self) -> bool:
        """当前是否绘制键盘焦点环，默认 ``False``。"""

        return self._focus_ring

    def set_focus_ring(self, enabled: bool) -> None:
        """运行时开关焦点环：``True`` 恢复品牌色焦点环，``False`` 只抑制原生焦点框。

        切换会立即重套当前主题，因此全局样式表和逐控件样式化的按钮会同步更新。
        需要键盘可见性的场景（纯键盘操作、无障碍需求）显式打开即可。
        """

        self._focus_ring = bool(enabled)
        self._apply_tokens()

    @property
    def reduced_motion(self) -> bool:
        """当前是否关闭动画。``True`` 时所有 ``motion`` 动画直达终值。"""

        return self._reduced_motion

    def set_reduced_motion(self, enabled: bool) -> None:
        """运行时可关掉全部动画（无障碍、低性能设备、远程桌面）。

        实现方式是把 ``Tokens.reduced_motion`` 置 1 后重套主题：``motion_fast_ms``
        与 ``motion_ms`` 归零，``psi6.ui.motion`` 因此直接置终值。已画好的控件
        不需要逐个通知——它们下一次交互读到的是 0。
        """

        changed = bool(enabled) != self._reduced_motion
        self._reduced_motion = bool(enabled)
        if changed:
            self._apply_tokens()

    def _resolve_current(self) -> Tokens:
        if self._tokens_override is not None:
            tokens = self._tokens_override.resolve_states()
        else:
            spec = self._theme_spec
            tokens = Tokens.light() if spec is None else resolve_tokens(self._theme_class(spec))
        tokens = tokens.resolve_states()
        if self._reduced_motion and not tokens.reduced_motion:
            tokens = tokens.overlay({"reduced_motion": 1})
        return self._apply_density(tokens)

    def _apply_tokens(self, *, density_event: bool = False) -> None:
        """重解析 token、重套主题与尺寸、刷新托盘，必要时广播密度变化。

        所有会改变视觉 token 的路径（初始化、换主题、跟随系统、手动切密度、
        Resize 自动翻转）都走这里，避免某条路径漏掉 ``apply_metrics`` 刷新。
        """

        app = self._ensure()
        self._tokens = self._resolve_current()
        apply_theme(app, self._tokens, focus_ring=self._focus_ring)
        self._refresh_shell()
        if density_event and self._signals is not None:
            # 参数是「生效的尺寸风格」：auto 且空间充足时沿用主题自带尺寸，记为 theme。
            self._signals.density_changed.emit(self._effective_style() or "theme")

    # ------------------------------------------------------------------
    # 响应式密度：让 style（modern / compact）随窗口空间自动切换
    # ------------------------------------------------------------------
    @property
    def density_changed(self) -> Any:
        """密度变化信号，可 ``connect``。

        参数是当前生效的尺寸风格：``compact`` / ``modern``，或 ``theme``
        （``auto`` 且空间充足，沿用主题自带尺寸）。手动切换与窗口尺寸触发的
        自动翻转都会发；换主题、跟随系统深浅色不发。
        """

        self._ensure()
        assert self._signals is not None
        return self._signals.density_changed

    @property
    def density_mode(self) -> str:
        """当前密度模式：``auto`` / ``modern`` / ``compact``。"""

        return self._density_mode

    def set_density_mode(self, mode: str) -> None:
        """运行中切换密度。``auto`` 按窗口尺寸自动收紧，``modern`` / ``compact`` 固定。

        切换后立刻重套当前主题，无视上一次的评估结果，因此从 ``compact`` 切回 ``auto``
        也能把收紧的尺寸还原回主题自带值。
        """

        self._density_mode = _normalize_density(mode)
        self._applied_style = self._effective_style()
        self._apply_tokens(density_event=True)

    def _apply_density(self, tokens: Tokens) -> Tokens:
        """把当前密度策略的尺寸预设压到已解析的 token 上；配色与主题显式覆盖不动。"""

        style = self._effective_style()
        if style is None:
            return tokens
        return tokens.overlay(style_metrics(style))

    def _effective_style(self) -> str | None:
        """真正要强制套用的 style；``None`` 表示沿用主题自带尺寸，不覆盖。

        ``auto`` 只在空间不足时收紧（``compact``），空间充足时不去放宽主题自己的选择，
        这样显式选了紧凑主题或写了自定义度量的主题不会被悄悄改掉。
        """

        target = self._target_density()
        if target is None:
            return None
        if self._density_mode == "auto" and target == "modern":
            return None
        return target

    def _target_density(self) -> str | None:
        """当前应采用的 style。手动模式固定；``auto`` 按窗口逻辑尺寸与 DPI 判定；无窗口返回 ``None``。"""

        if self._density_mode != "auto":
            return self._density_mode
        window = self._window
        if not isinstance(window, QWidget) or window.width() <= 0 or window.height() <= 0:
            return None
        width, height = window.width(), window.height()
        scale = _HIGH_DPI_SCALE if self._window_dpr() >= 2 else 1.0
        if width < self._compact_max_width * scale or height < self._compact_max_height * scale:
            return "compact"
        return "modern"

    def _window_dpr(self) -> float:
        """主窗口的像素比；拿不到或出错时回落到 ``1.0``，不让几何判断抛异常。"""

        window = self._window
        if window is None:
            return 1.0
        with contextlib.suppress(Exception):
            return float(window.devicePixelRatio() or 1.0)
        return 1.0

    def _bind_density(self) -> None:
        """给主窗口装 ``Resize`` 事件过滤器，使 ``auto`` 能随窗口尺寸变化重算。"""

        if self._density_bound or self._window is None or self._qt_app is None:
            return
        self._geo_watcher = _WindowResizeWatcher(self._on_window_resized, parent=self._qt_app)
        self._window.installEventFilter(self._geo_watcher)
        self._density_bound = True

    def _on_window_resized(self) -> None:
        """窗口尺寸变化后去抖重算，避免拖动过程中反复重套整张样式表。"""

        if self._density_mode != "auto" or self._qt_app is None:
            return
        if self._density_timer is None:
            self._density_timer = QTimer(self._qt_app)
            self._density_timer.setSingleShot(True)
            self._density_timer.timeout.connect(self._recompute_density)
        self._density_timer.start(_DENSITY_DEBOUNCE_MS)

    def _recompute_density(self) -> None:
        """密度真正翻转时才重套主题；同尺寸反复 resize 不会触发任何重绘。"""

        style = self._effective_style()
        if style == self._applied_style:
            return
        self._applied_style = style
        self._apply_tokens(density_event=True)

    def _register_theme(self, theme: str | Tokens | Theme | type[Theme] | None) -> None:
        """把 ``Theme`` 类按 ``name`` 记进注册表，配置里只存这个名字。"""

        if not isinstance(theme, type) or not issubclass(theme, Theme):
            return
        key = theme_key(theme)
        if key:
            self._theme_registry.setdefault(key, theme)

    def _theme_class(
        self, spec: str | Tokens | Theme | type[Theme]
    ) -> str | Tokens | Theme | type[Theme]:
        """注册过的主题名换成主题类。方案字符串和其它对象原样返回。"""

        if not isinstance(spec, str):
            return spec
        key = spec.strip().lower()
        if key in _SCHEMES:
            return key
        found = self._theme_registry.get(key)
        if found is None:
            known = ", ".join(sorted(self._theme_registry)) or "（没有）"
            raise ValueError(f"未注册的主题：{spec}。可以用 {known}")
        return found

    def _restore_theme(self) -> None:
        """读出上次选的主题。没记住或认不出来时保留 ``theme`` 参数给的默认值。"""

        if not self._remember_theme:
            return
        data = self.store.load_data(self.name, _THEME_FILE) or {}
        key = data.get("theme")
        if not isinstance(key, str) or not key.strip():
            return
        try:
            spec = self._theme_class(key)
        except ValueError:
            _logger.warning("配置里的主题 %s 没有注册，改用默认主题", key)
            return
        self._theme_spec = spec
        self._tokens_override = None

    def _remember_current_theme(self) -> None:
        """把当前选择写进配置文件。``Tokens`` 没有名字，不写。"""

        if not self._remember_theme or self._theme_spec is None:
            return
        key = theme_key(self._theme_spec)
        if key is None:
            return
        try:
            self.store.save_data(self.name, _THEME_FILE, {"theme": key})
        except OSError:
            _logger.warning("写入主题配置失败", exc_info=True)

    def _watch_system_theme(self) -> None:
        if self._scheme_bound or self._qt_app is None:
            return
        self._qt_app.styleHints().colorSchemeChanged.connect(self._on_system_scheme)
        self._scheme_bound = True

    def _on_system_scheme(self, *_args: object) -> None:
        """系统换浅色/深色时，只有跟随主题（``auto`` 或 ``base = "auto"``）才重套。"""

        spec = self._theme_spec
        if spec is None or isinstance(spec, Tokens) or not follows_system(spec):
            return
        self._apply_tokens()

    @property
    def theme_name(self) -> str:
        """当前主题标识：``light`` / ``dark`` / ``auto`` 或注册过的主题 ``name``。"""

        spec = self._theme_spec
        return "light" if spec is None else (theme_key(spec) or "custom")

    def set_theme(self, theme: str | Tokens | Theme | type[Theme]) -> None:
        """运行中切换主题：``light`` / ``dark`` / ``auto``、注册过的主题名，或一个 ``Theme`` / ``Tokens``。

        ``Theme`` 会自动登记名字，``remember_theme=True`` 时把这次选择写进配置文件。
        """

        spec = self._theme_class(theme)
        self._register_theme(spec)
        if isinstance(spec, Tokens):
            self._tokens_override = spec
            self._theme_spec = spec
        else:
            self._tokens_override = None
            self._theme_spec = spec
        self._apply_tokens()
        self._remember_current_theme()

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

    def remember_path(self, key: str, path: str | Path) -> None:
        """把界面用到的路径写进 ``QSettings``，例如上次选择的目录。

        程序参数仍走 ``load_config`` / ``save_config``；这里只记界面状态。
        """

        settings = QSettings(self.organization, self.name)
        settings.setValue(f"ui/paths/{key}", str(Path(path)))
        settings.sync()

    def recalled_path(self, key: str, *, must_exist: bool = True) -> Path | None:
        """读出 ``remember_path`` 记住的路径。

        ``must_exist`` 为真时，路径已经不存在就清掉这一项并返回 ``None``。
        """

        settings = QSettings(self.organization, self.name)
        raw = settings.value(f"ui/paths/{key}", "", type=str)
        if not isinstance(raw, str) or not raw:
            return None
        path = Path(raw)
        if must_exist and not path.exists():
            settings.remove(f"ui/paths/{key}")
            settings.sync()
            return None
        return path

    def run(
        self,
        window: QWidget,
        *,
        tray: bool = False,
        single_instance: bool = False,
        restore_geometry: bool = False,
        float_ball: bool = False,
    ) -> int:
        """套用主题、安装异常钩子、绑定状态栏、显示窗口并进入事件循环。

        默认允许多个进程同时运行，也不写窗口位置。
        ``single_instance=True`` 时，第二份进程唤醒已有窗口后退出。
        ``restore_geometry=True`` 时，启动恢复上次位置与最大化，退出时写回 ``window.json``。
        ``tray=True`` 且系统有托盘时，关闭主窗口隐藏而不是退出。
        ``float_ball=True`` 在屏幕上留一个可拖动的圆标，关闭主窗口同样改为隐藏，
        不依赖系统有没有托盘。两者都没有时，关闭仍结束进程。
        关闭窗口不取消任务；退出时才按几何、任务、单实例锁、托盘、悬浮球的顺序收尾。

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
            float_ball=float_ball,
        ):
            return 0
        self._executing = True
        try:
            window.show()
            self._recompute_density()  # 启动即按首次真实窗口尺寸定密度
            if self.float_ball is not None:
                self.float_ball.place_default()
                self.float_ball.show()
            return app.exec()
        finally:
            self._executing = False

    def _hold_quit(self) -> None:
        """有可用托盘或悬浮球时，关掉最后一个窗口不再结束进程。"""

        app = self._ensure()
        if self._previous_quit_on_last_window_closed is None:
            self._previous_quit_on_last_window_closed = app.quitOnLastWindowClosed()
        app.setQuitOnLastWindowClosed(False)

    def _open(
        self,
        window: QWidget,
        *,
        tray: bool,
        single_instance: bool,
        restore_geometry: bool,
        float_ball: bool = False,
    ) -> bool:
        """绑定单实例、几何、托盘、悬浮球和通知。第二实例返回 False，此时不显示窗口。

        系统没有托盘时仍创建 ``TrayIcon``，但它是空操作：不把关闭改成隐藏，
        也不关掉「最后一个窗口关闭即退出」。悬浮球不依赖托盘，
        ``float_ball=True`` 时关闭 ``DesktopWindow`` 改为隐藏。圆标要等主窗口
        显示后再 ``show()``，这里只创建，不弹出。
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
        self._bind_density()
        if tray:
            icon = window.icon_name if isinstance(window, DesktopWindow) else "grid"
            self.tray = TrayIcon(window, tooltip=self.name, icon=icon, parent=app)
            if self.tray.available:
                self._hold_quit()
        if float_ball:
            icon = window.icon_name if isinstance(window, DesktopWindow) else "grid"
            self.float_ball = FloatBall(window, tooltip=self.name, icon=icon, resident=True)
            self._hold_quit()
        if isinstance(window, QMainWindow):
            self.notifier.bind_status_bar(window.statusBar())
            anchor = window.centralWidget() or window
        else:
            anchor = window
        self.notifier.bind_toast_host(ToastHost(anchor))
        install_exception_hooks(app, parent=window, notifier=self.notifier, owner=self)
        return True


def raise_window(window: QWidget) -> None:
    """把已有窗口从托盘、悬浮球或最小化里拉回来。"""

    present_window(window)
