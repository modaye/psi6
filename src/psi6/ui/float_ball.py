"""悬浮球：主窗口藏起后仍留在屏幕上的圆标。"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, ClassVar

from PySide6.QtCore import QEvent, QObject, QPoint, QPointF, QRect, QRectF, Qt, QTimer
from PySide6.QtGui import (
    QColor,
    QContextMenuEvent,
    QEnterEvent,
    QGuiApplication,
    QMouseEvent,
    QPaintEvent,
    QPen,
)
from PySide6.QtWidgets import QApplication, QWidget

from psi6.icons.render import device_ratio, pixmap_for
from psi6.theme.paint import create_painter
from psi6.theme.runtime import token_color, token_int
from psi6.ui.context_menu import MenuAction, build_menu
from psi6.ui.desktop_window import DesktopWindow
from psi6.ui.icon import token_color as glyph_color
from psi6.ui.window_presence import (
    present_window,
    quit_application,
    toggle_window,
    window_is_presented,
)


class FloatBall(QWidget):
    """屏幕上的小圆标。单击显示或隐藏主窗口，拖动换位置，右键退出。

    Python 丢掉最后一个引用时，Qt 会立刻拆掉这个置顶窗口，在 Windows 上会访问已释放的
    原生句柄。圆标改由类自己留到进程结束，真正销毁交给 ``QApplication`` 收尾。

    它自己就是一个窗口，不挂到主窗口上：主窗口 ``hide()`` 时圆标还在。
    构造时不 ``show()``。``App.run(..., float_ball=True)`` 会在主窗口显示后
    放到屏幕右下角再显示。手动使用时先 ``place_default()`` 或 ``move``，再 ``show()``。

    ``resident=True`` 时，``DesktopWindow`` 关闭改为隐藏，和托盘一样。
    进程是否在最后一个窗口关闭后退出，由 ``App`` 关掉 ``quitOnLastWindowClosed``。
    颜色只在绘制时读 token。直径跟 ``control_height``。
    """

    _alive: ClassVar[list[FloatBall]] = []

    def __init__(
        self,
        window: QWidget,
        *,
        tooltip: str,
        icon: str = "grid",
        resident: bool = False,
    ) -> None:
        super().__init__(None)
        self._window: QWidget | None = window
        self._host_open = True
        self._tooltip = tooltip
        self._icon_name = icon
        self._status = ""
        self._extra: list[MenuAction] = []
        self._press_global: QPoint | None = None
        self._origin: QPoint | None = None
        self._dragged = False
        self._pressed = False
        self._hover = False
        self._floated = False
        self.setObjectName("psi6FloatBall")
        self.setAccessibleName("悬浮球")
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.apply_metrics()
        self._apply_tooltip()
        window.destroyed.connect(self._on_host_destroyed)
        if resident and isinstance(window, DesktopWindow):
            window.close_to_tray = True
        FloatBall._alive.append(self)

    @property
    def icon_name(self) -> str:
        return self._icon_name

    @property
    def status(self) -> str:
        return self._status

    def set_icon(self, name: str) -> None:
        """换圆标中心的图标。空名字保留原来的图标。"""

        if name:
            self._icon_name = name
            self.update()

    def set_status(self, text: str) -> None:
        """附上短状态。非空时右下角画一个主色点，文字加到提示里。"""

        self._status = text.strip()
        self._apply_tooltip()
        self.update()

    def add_action(self, label: str, callback: Callable[[], Any], *, icon: str = "") -> None:
        """右键菜单在「退出」前追加一项。"""

        self._extra.append(MenuAction(label, callback=callback, icon=icon))

    def menu_actions(self) -> list[MenuAction]:
        """当前右键菜单。窗口已经销毁时只留「退出」。"""

        window = self._window
        if not self._host_open or window is None:
            return [
                MenuAction("退出", callback=self._request_quit, icon="win-close", dangerous=True)
            ]
        presented = window_is_presented(window)

        def show_host(host: QWidget = window) -> None:
            present_window(host)

        items = [
            MenuAction(
                "显示窗口",
                callback=show_host,
                icon="monitor",
                enabled=not presented,
            ),
            MenuAction(
                "隐藏窗口",
                callback=window.hide,
                icon="win-min",
                enabled=presented,
            ),
        ]
        if self._extra:
            items.append(MenuAction.line())
            items.extend(self._extra)
        items.append(MenuAction.line())
        items.append(
            MenuAction("退出", callback=self._request_quit, icon="win-close", dangerous=True)
        )
        return items

    def place_default(self) -> None:
        """放到主窗口所在屏幕工作区的右下角。显示之前调用。"""

        area = self._screen_area()
        if area is None:
            return
        margin = token_int("space_lg", 16)
        self.move(
            area.right() - self.width() - margin + 1,
            area.bottom() - self.height() - margin + 1,
        )
        self._clamp()

    def apply_metrics(self) -> None:
        """按当前 token 重算直径，并保证圆标还在屏幕工作区内。"""

        side = max(token_int("control_height_sm", 28), token_int("control_height", 36))
        if self.size().width() != side or self.size().height() != side:
            self.setFixedSize(side, side)
        self._clamp()
        self.update()

    def show(self) -> None:  # type: ignore[override]
        """第一次显示时才变成置顶圆窗。未显示就销毁时，这些标志会让原生层崩溃。"""

        if not self._floated:
            self._floated = True
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.Tool
                | Qt.WindowType.WindowStaysOnTopHint
            )
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
            self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        super().show()

    def quit(self) -> None:
        """藏起圆标并结束进程。右键「退出」会延后到菜单关闭后调用这里。"""

        self.hide()
        window = self._window
        if self._host_open and window is not None:
            quit_application(window)
        else:
            app = QApplication.instance()
            if isinstance(app, QApplication):
                app.quit()

    def paintEvent(self, event: QPaintEvent) -> None:  # type: ignore[override]
        del event
        side = self.width()
        if self._pressed:
            fill = token_color("pressed") or token_color("hover")
        elif self._hover:
            fill = token_color("hover")
        else:
            fill = token_color("elevated")
        fill = fill or token_color("surface")
        border = token_color("control_border") or token_color("border")
        box = QRectF(1, 1, side - 2, side - 2)
        with create_painter(self) as painter:
            painter.setPen(QPen(QColor(border), 1))
            painter.setBrush(QColor(fill))
            painter.drawEllipse(box)
            glyph = min(token_int("icon_size", 16), max(12, side // 2))
            pix = pixmap_for(
                self._icon_name,
                color=glyph_color(self),
                size=glyph,
                ratio=device_ratio(self),
            )
            ratio = pix.devicePixelRatio() or 1.0
            logical = pix.width() / ratio
            painter.drawPixmap(QPointF((side - logical) / 2, (side - logical) / 2), pix)
            if self._status:
                radius = max(3.0, token_int("space_sm", 8) / 2)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(token_color("primary")))
                painter.drawEllipse(
                    QRectF(side - radius * 2 - 2, side - radius * 2 - 2, radius * 2, radius * 2)
                )

    def enterEvent(self, event: QEnterEvent) -> None:  # type: ignore[override]
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:  # type: ignore[override]
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if event.type() in {
            QEvent.Type.PaletteChange,
            QEvent.Type.StyleChange,
            QEvent.Type.ScreenChangeInternal,
            QEvent.Type.DevicePixelRatioChange,
        }:
            self.apply_metrics()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        self._press_global = event.globalPosition().toPoint()
        self._origin = self.pos()
        self._dragged = False
        self._pressed = True
        if self.isVisible():
            self.grabMouse()
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if (
            not self._pressed
            or self._press_global is None
            or self._origin is None
            or not (event.buttons() & Qt.MouseButton.LeftButton)
        ):
            super().mouseMoveEvent(event)
            return
        delta = event.globalPosition().toPoint() - self._press_global
        app = QApplication.instance()
        threshold = app.startDragDistance() if isinstance(app, QApplication) else 10
        if delta.manhattanLength() >= threshold:
            self._dragged = True
        if self._dragged:
            self.move(self._origin + delta)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton or not self._pressed:
            super().mouseReleaseEvent(event)
            return
        if QWidget.mouseGrabber() is self:
            self.releaseMouse()
        dragged = self._dragged
        self._pressed = False
        self._dragged = False
        self._press_global = None
        self._origin = None
        if dragged:
            self._clamp()
        else:
            window = self._window
            if self._host_open and window is not None:
                toggle_window(window)
        self.update()

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:  # type: ignore[override]
        menu = build_menu(self.menu_actions(), host=self)
        try:
            menu.exec(event.globalPos())
        finally:
            menu.deleteLater()

    def _request_quit(self) -> None:
        """等右键菜单关掉再退出，避免在菜单回调里拆掉菜单自己。"""

        QTimer.singleShot(0, self.quit)

    def _apply_tooltip(self) -> None:
        tip = self._tooltip if not self._status else f"{self._tooltip}\n{self._status}"
        self.setToolTip(tip)

    def _on_host_destroyed(self, _host: QObject | None = None) -> None:
        """宿主正在析构。这里不能同步 ``hide()``，否则会在拆窗口时访问已死的原生句柄。"""

        self._host_open = False
        self._window = None
        if self.isVisible():
            QTimer.singleShot(0, self.hide)

    def _screen_area(self) -> QRect | None:
        screen = self.screen()
        window = self._window
        if screen is None and window is not None:
            screen = window.screen()
        if screen is None:
            screen = QGuiApplication.primaryScreen()
        if screen is None:
            return None
        return screen.availableGeometry()

    def _clamp(self) -> None:
        """把圆标留在工作区内，避免拖出屏幕后找不到。"""

        area = self._screen_area()
        if area is None or self.width() <= 0 or self.height() <= 0:
            return
        x = min(max(self.x(), area.left()), max(area.left(), area.right() - self.width() + 1))
        y = min(max(self.y(), area.top()), max(area.top(), area.bottom() - self.height() + 1))
        if x != self.x() or y != self.y():
            self.move(x, y)
