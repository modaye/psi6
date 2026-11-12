"""图标控件：随当前主题 token 着色、缩放。"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QSize, Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QPushButton, QSizePolicy, QToolButton, QWidget

from psi6.icons.render import device_ratio, icon_for, pixmap_for
from psi6.theme.paint import create_painter
from psi6.theme.runtime import token_int
from psi6.ui.filters import install_press_scale
from psi6.ui.tone import Tone, normalize_tone

_TONE_KEYS = {
    "neutral": "psi6ColorText",
    "info": "psi6ColorInfo",
    "success": "psi6ColorSuccess",
    "warning": "psi6ColorWarning",
    "error": "psi6ColorDanger",
}

_ICON_EVENTS = frozenset(
    {
        QEvent.Type.PaletteChange,
        QEvent.Type.StyleChange,
        QEvent.Type.ScreenChangeInternal,
        QEvent.Type.DevicePixelRatioChange,
    }
)


def token_color(widget: QWidget, *, tone: str = "neutral") -> str:
    """从 ``apply_theme`` 写入的应用属性取色，缺省用文字色。"""

    forced = widget.property("psi6IconColor")
    if isinstance(forced, str) and forced.startswith("#"):
        return forced
    app = QApplication.instance()
    key = _TONE_KEYS.get(tone, "psi6ColorText")
    if app is not None:
        value = app.property(key)
        if isinstance(value, str) and value:
            return value
    color = widget.palette().color(QPalette.ColorRole.WindowText)
    return QColor(color).name()


def _theme_icon_size() -> int:
    return max(12, token_int("icon_size"))


def _theme_control_height() -> int:
    return max(24, token_int("control_height"))


class Icon(QWidget):
    """描边图标。``size`` 缺省跟 ``icon_size`` token；不要用 emoji 替代。"""

    def __init__(
        self,
        name: str,
        *,
        size: int | None = None,
        tone: Tone | str = "neutral",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("psi6Icon")
        self._name = name
        self._explicit_size = size
        self._size = size if size is not None else _theme_icon_size()
        self._tone = normalize_tone(tone)
        self._color_source: str | None = None
        self.setFixedSize(self._size, self._size)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def set_name(self, name: str) -> None:
        self._name = name
        self.update()

    def set_size(self, size: int | None) -> None:
        """改图标边长。``None`` 交回 ``icon_size`` token，重新自动跟随主题。"""

        resolved = max(8, int(size)) if size is not None else _theme_icon_size()
        self._explicit_size = size
        self._size = resolved
        self.setFixedSize(resolved, resolved)
        self.update()

    def set_tone(self, tone: Tone | str) -> None:
        self._tone = normalize_tone(tone)
        self.update()

    def set_color(self, color: str | None) -> None:
        """指定这一个图标的颜色。``None`` 回到 ``tone``。

        ``#RRGGBB`` 保持不变。``primary`` 或 ``color_primary`` 跟随当前主题。
        """

        self._color_source = color.strip() if isinstance(color, str) and color.strip() else None
        self._apply_color()
        self.update()

    def _apply_color(self) -> None:
        source = getattr(self, "_color_source", None)
        if not source:
            self.setProperty("psi6IconColor", "")
            return
        from psi6.ui.style import resolve_color

        self.setProperty("psi6IconColor", resolve_color(source))

    def name(self) -> str:
        return self._name

    def changeEvent(self, event: QEvent) -> None:  # type: ignore[override]
        super().changeEvent(event)
        if event.type() in _ICON_EVENTS:
            self._sync_metrics()
            self._apply_color()
            self.update()

    def _sync_metrics(self) -> None:
        if self._explicit_size is not None:
            return
        size = _theme_icon_size()
        if size != self._size:
            self._size = size
            self.setFixedSize(size, size)

    def paintEvent(self, event) -> None:
        del event
        color = token_color(self, tone=self._tone)
        pix = pixmap_for(
            self._name,
            color=color,
            size=self._size,
            ratio=device_ratio(self),
        )
        with create_painter(self, clear_pen=False) as painter:
            painter.drawPixmap(0, 0, pix)


class IconButton(QToolButton):
    """方形图标按钮。``extent`` 控制热区边长；缺省跟 ``control_height`` token。"""

    def __init__(
        self,
        name: str,
        *,
        label: str,
        size: int | None = None,
        extent: int | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("psi6IconButton")
        self._name = name
        self._explicit_size = size
        self._explicit_extent = extent
        self._icon_size = size if size is not None else _theme_icon_size()
        self._press_scale = 1.0
        self.setAutoRaise(True)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.setToolTip(label)
        self.setAccessibleName(label)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._sync_metrics()
        install_press_scale(self)

    def set_press_scale(self, value: float) -> None:
        """按下时略缩小图标。由 ``PressScaleFilter`` 调用。"""

        self._press_scale = max(0.8, min(1.0, float(value)))
        self._apply_icon_extent()

    def set_name(self, name: str) -> None:
        self._name = name
        self._sync_icon()

    def refresh(self) -> None:
        """主题切换后按当前 token 重算尺寸和颜色。"""

        self._sync_metrics()

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() in _ICON_EVENTS:
            self._sync_metrics()

    def _sync_metrics(self) -> None:
        icon = self._explicit_size if self._explicit_size is not None else _theme_icon_size()
        extent = (
            self._explicit_extent
            if self._explicit_extent is not None
            else max(28, _theme_control_height(), icon + 16)
        )
        self._icon_size = icon
        self.setFixedSize(extent, extent)
        self._apply_icon_extent()
        self._sync_icon()

    def _apply_icon_extent(self) -> None:
        size = max(8, round(self._icon_size * self._press_scale))
        self.setIconSize(QSize(size, size))

    def _sync_icon(self) -> None:
        color = token_color(self)
        self.setIcon(
            icon_for(
                self._name,
                color=color,
                size=self._icon_size,
                ratio=device_ratio(self),
            )
        )


class _ButtonIconRefresher(QObject):
    """普通按钮的图标不会自己重画；主题或屏幕比例变化时在这里补。"""

    def __init__(self, button: QPushButton) -> None:
        super().__init__(button)
        self._button = button
        self._name = ""
        self._size: int | None = None

    def configure(self, name: str, size: int | None) -> None:
        self._name = name
        self._size = size
        self.refresh()

    def refresh(self) -> None:
        if self._name:
            _paint_button_icon(self._button, self._name, self._size)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self._button and event.type() in _ICON_EVENTS:
            self.refresh()
        return False


def _paint_button_icon(button: QPushButton, name: str, size: int | None) -> None:
    extent = size if size is not None else _theme_icon_size()
    if button.objectName() == "psi6Primary":
        app = QApplication.instance()
        color = app.property("psi6ColorOnPrimary") if app is not None else None
        if not isinstance(color, str) or not color:
            color = token_color(button)
    elif button.objectName() == "psi6Danger":
        color = token_color(button, tone="error")
    else:
        color = token_color(button)
    button.setIcon(icon_for(name, color=color, size=extent, ratio=device_ratio(button)))
    button.setIconSize(QSize(extent, extent))


def apply_button_icon(button: QPushButton, name: str, *, size: int | None = None) -> None:
    """给普通按钮加上着色图标。主按钮用 ``on_primary``，避免深色图标叠在强调色上。

    图标会跟随主题、DPI 和屏幕切换重画，调用方只需在换图标时再调一次。
    """

    refresher = button.findChild(_ButtonIconRefresher)
    if refresher is None:
        refresher = _ButtonIconRefresher(button)
        button.installEventFilter(refresher)
    refresher.configure(name, size)
