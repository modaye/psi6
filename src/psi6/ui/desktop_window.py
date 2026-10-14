"""主窗口。默认用 Qt 标题栏；``frameless=True`` 才自绘标题栏。"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QPoint, QRect, Qt
from PySide6.QtGui import QMouseEvent, QResizeEvent, QShowEvent
from PySide6.QtWidgets import QMainWindow, QStatusBar, QVBoxLayout, QWidget

from psi6.ui.title_bar import TitleBar
from psi6.ui.window_shape import (
    apply_native_round,
    grip_rects,
    round_mask,
    supports_window_mask,
    window_radius,
)

_EDGE = 8

_CURSORS = {
    "left": Qt.CursorShape.SizeHorCursor,
    "right": Qt.CursorShape.SizeHorCursor,
    "top": Qt.CursorShape.SizeVerCursor,
    "bottom": Qt.CursorShape.SizeVerCursor,
    "top-left": Qt.CursorShape.SizeFDiagCursor,
    "bottom-right": Qt.CursorShape.SizeFDiagCursor,
    "top-right": Qt.CursorShape.SizeBDiagCursor,
    "bottom-left": Qt.CursorShape.SizeBDiagCursor,
}


class _EdgeGrip(QWidget):
    """只覆盖窗口边框的拉伸热区。光标设在自身，不会污染内容区。"""

    def __init__(self, host: DesktopWindow, edge: str) -> None:
        super().__init__(host)
        self.setObjectName("psi6EdgeGrip")
        self._host = host
        self._edge = edge
        self.setCursor(_CURSORS[edge])
        self.setMouseTracking(True)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and not self._host.isMaximized():
            self._host.begin_resize(self._edge, event.globalPosition().toPoint())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._host.update_resize(event.globalPosition().toPoint())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._host.end_resize()
        super().mouseReleaseEvent(event)


class DesktopWindow(QMainWindow):
    """主窗口。默认使用 Qt 自带标题栏和状态栏。

    ``frameless=True`` 才换成自绘 ``TitleBar``、圆角和无边框缩放。
    业务内容交给 ``set_body``。
    """

    def __init__(
        self,
        *,
        title: str,
        icon: str = "grid",
        frameless: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self._frameless = frameless
        self.setProperty("frameless", frameless)
        self._icon_name = icon
        self.title_bar: TitleBar | None = None
        self.close_to_tray = False
        self._force_quit = False
        self._resize_edge: str | None = None
        self._press_global = QPoint()
        self._press_geom = QRect()
        self._body_host = QWidget()
        self._body_host.setObjectName("psi6DesktopBody")
        self._body_host.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._body_layout = QVBoxLayout(self._body_host)
        self._body_layout.setContentsMargins(0, 0, 0, 0)
        self._body_layout.setSpacing(0)
        if frameless:
            self._init_frameless()
        else:
            self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            super().setCentralWidget(self._body_host)

    def _init_frameless(self) -> None:
        """无边框壳：自绘标题栏、内嵌状态栏、边缘缩放。"""

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Window
            | Qt.WindowType.WindowSystemMenuHint
            | Qt.WindowType.WindowMinMaxButtonsHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.unsetCursor()
        chrome = QWidget()
        chrome.setObjectName("psi6DesktopRoot")
        chrome.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._chrome = chrome
        column = QVBoxLayout(chrome)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)
        self.title_bar = TitleBar(self, title=self.windowTitle(), icon=self._icon_name)
        column.addWidget(self.title_bar)
        column.addWidget(self._body_host, stretch=1)
        self._status = QStatusBar()
        self._status.setObjectName("psi6WindowStatus")
        self._status.setSizeGripEnabled(False)
        column.addWidget(self._status)
        super().setCentralWidget(chrome)
        self._grips = {edge: _EdgeGrip(self, edge) for edge in _CURSORS}
        self._layout_grips()

    @property
    def frameless(self) -> bool:
        """是否使用自绘标题栏。"""

        return self._frameless

    @property
    def icon_name(self) -> str:
        """窗口图标名。托盘和自绘标题栏都读这个。"""

        return self._icon_name

    def statusBar(self) -> QStatusBar:  # type: ignore[override]
        """无边框时用壳内状态栏，否则用 Qt 自带状态栏。"""

        if getattr(self, "_frameless", False):
            return self._status
        return super().statusBar()

    def set_body(self, widget: QWidget) -> None:
        """把业务内容放到标题栏下方。"""

        while self._body_layout.count():
            item = self._body_layout.takeAt(0)
            child = item.widget()
            if child is not None:
                child.hide()
                child.deleteLater()
        self._body_layout.addWidget(widget)
        if self._frameless:
            self._raise_grips()

    def setCentralWidget(self, widget: QWidget | None) -> None:  # type: ignore[override]
        if widget is None:
            return
        self.set_body(widget)

    def setWindowTitle(self, title: str) -> None:
        super().setWindowTitle(title)
        title_bar = getattr(self, "title_bar", None)
        if title_bar is not None:
            title_bar.set_title(title)

    def set_icon(self, name: str) -> None:
        """窗口图标名。无边框时同步到自绘标题栏。"""

        self._icon_name = name
        if self.title_bar is not None:
            self.title_bar.set_icon(name)

    def request_quit(self) -> None:
        """真正退出。托盘「退出」必须走这里，不能只 hide。"""

        self.close_to_tray = False
        self._force_quit = True
        self.close()

    def begin_resize(self, edge: str, global_pos: QPoint) -> None:
        self._resize_edge = edge
        self._press_global = global_pos
        self._press_geom = self.geometry()

    def update_resize(self, global_pos: QPoint) -> None:
        if self._resize_edge is None or self.isMaximized():
            return
        delta = global_pos - self._press_global
        geom = QRect(self._press_geom)
        min_w = max(self.minimumWidth(), 320)
        min_h = max(self.minimumHeight(), 240)
        edge = self._resize_edge
        if edge in {"left", "top-left", "bottom-left"}:
            geom.setLeft(min(geom.right() - min_w, geom.left() + delta.x()))
        if edge in {"right", "top-right", "bottom-right"}:
            geom.setRight(max(geom.left() + min_w, geom.right() + delta.x()))
        if edge in {"top", "top-left", "top-right"}:
            geom.setTop(min(geom.bottom() - min_h, geom.top() + delta.y()))
        if edge in {"bottom", "bottom-left", "bottom-right"}:
            geom.setBottom(max(geom.top() + min_h, geom.bottom() + delta.y()))
        self.setGeometry(geom)

    def end_resize(self) -> None:
        self._resize_edge = None

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        if not getattr(self, "_frameless", False):
            return
        self._sync_shape()
        self._layout_grips()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if not getattr(self, "_frameless", False):
            return
        self._sync_shape()
        self._layout_grips()

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        title_bar = getattr(self, "title_bar", None)
        if (
            getattr(self, "_frameless", False)
            and title_bar is not None
            and event.type() == QEvent.Type.WindowStateChange
        ):
            title_bar.sync_max_button()
            self._sync_shape()
            self._layout_grips()

    def closeEvent(self, event) -> None:  # noqa: ANN001
        if self.close_to_tray and not self._force_quit:
            event.ignore()
            self.hide()
            return
        super().closeEvent(event)

    def _sync_shape(self) -> None:
        """圆角裁切与 DWM 偏好。最大化时取消，避免贴边露缝。"""

        if not hasattr(self, "_chrome"):
            return
        rounded = not (self.isMaximized() or self.isFullScreen())
        apply_native_round(self, rounded=rounded)
        radius = window_radius() if rounded else 0
        if rounded and radius > 0 and supports_window_mask():
            self.setMask(round_mask(self.rect(), radius))
        else:
            self.clearMask()
        for widget in (self._chrome, self.title_bar, self._status):
            widget.setProperty("rounded", rounded)
            style = widget.style()
            style.unpolish(widget)
            style.polish(widget)
            widget.update()

    def _layout_grips(self) -> None:
        if not hasattr(self, "_grips"):
            return
        visible = not (self.isMaximized() or self.isFullScreen())
        blocked = self.title_bar.controls_rect_in(self) if visible else None
        rects = grip_rects(self.size(), thickness=_EDGE, blocked=blocked) if visible else {}
        for edge, grip in self._grips.items():
            rect = rects.get(edge)
            if rect is None or not visible:
                grip.hide()
                continue
            grip.setGeometry(rect)
            grip.show()
            grip.raise_()

    def _raise_grips(self) -> None:
        for grip in getattr(self, "_grips", {}).values():
            grip.raise_()
