"""图标控件：随当前主题 token 着色、缩放。"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QSize, Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QPushButton, QSizePolicy, QToolButton, QWidget

from psi6.icons.render import icon_for, pixmap_for
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
    return max(12, token_int("icon_size", 16))


def _theme_control_height() -> int:
    return max(24, token_int("control_height", 32))


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
        self.setFixedSize(self._size, self._size)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def set_name(self, name: str) -> None:
        self._name = name
        self.update()

    def set_tone(self, tone: Tone | str) -> None:
        self._tone = normalize_tone(tone)
        self.update()

    def name(self) -> str:
        return self._name

    def changeEvent(self, event: QEvent) -> None:  # type: ignore[override]
        super().changeEvent(event)
        if event.type() in {QEvent.Type.PaletteChange, QEvent.Type.StyleChange}:
            self._sync_metrics()
            self.update()

    def _sync_metrics(self) -> None:
        if self._explicit_size is not None:
            return
        size = _theme_icon_size()
        if size != self._size:
            self._size = size
            self.setFixedSize(size, size)

    def paintEvent(self, event) -> None:  # noqa: ANN001
        del event
        color = token_color(self, tone=self._tone)
        pix = pixmap_for(self._name, color=color, size=self._size)
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

    def changeEvent(self, event) -> None:  # noqa: ANN001
        super().changeEvent(event)
        self._sync_metrics()

    def _sync_metrics(self) -> None:
        icon = self._explicit_size if self._explicit_size is not None else _theme_icon_size()
        extent = (
            self._explicit_extent
            if self._explicit_extent is not None
            else max(_theme_control_height(), icon + 16)
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
        self.setIcon(icon_for(self._name, color=color, size=self._icon_size))


def apply_button_icon(button: QPushButton, name: str, *, size: int | None = None) -> None:
    """给普通按钮加上着色图标。主按钮用 ``on_primary``，避免深色图标叠在强调色上。"""

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
    button.setIcon(icon_for(name, color=color, size=extent))
    button.setIconSize(QSize(extent, extent))
