"""无边框窗口的拖动标题栏：图标、标题、最小化 / 最大化 / 关闭。"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QPoint, QRect, QSize, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from psi6.theme.runtime import token_int
from psi6.ui.icon import Icon, IconButton


def drag_origin_after_restore(
    global_pos: QPoint,
    frame_size: QSize,
    ratio: float,
    local_y: int,
) -> QPoint:
    """从最大化拖出后，窗口左上角应对齐到光标下的标题栏位置。"""

    width = max(int(frame_size.width()), 1)
    clamped = min(max(ratio, 0.0), 1.0)
    return QPoint(global_pos.x() - int(width * clamped), global_pos.y() - int(local_y))


class TitleBar(QWidget):
    """自定义标题栏。双击切换最大化；拖动移动宿主窗口。"""

    def __init__(
        self,
        host: QWidget,
        *,
        title: str,
        icon: str = "grid",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("psi6TitleBar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._host = host
        self._icon_name = icon
        self._drag_offset: QPoint | None = None
        self._drag_ratio = 0.0
        self._drag_local_y = 0
        row = QHBoxLayout(self)
        row.setContentsMargins(10, 0, 4, 0)
        row.setSpacing(8)
        self._icon = Icon(icon)
        row.addWidget(self._icon)
        self._title = QLabel(title)
        self._title.setObjectName("psi6TitleText")
        row.addWidget(self._title, stretch=1)
        self._min = IconButton("win-min", label="最小化")
        self._min.setObjectName("psi6TitleButton")
        self._min.clicked.connect(host.showMinimized)
        self._max = IconButton("win-max", label="最大化")
        self._max.setObjectName("psi6TitleButton")
        self._max.clicked.connect(self._toggle_max)
        self._close = IconButton("win-close", label="关闭")
        self._close.setObjectName("psi6TitleClose")
        self._close.clicked.connect(host.close)
        row.addWidget(self._min)
        row.addWidget(self._max)
        row.addWidget(self._close)
        self._sync_metrics()
        self.sync_max_button()

    def _sync_metrics(self) -> None:
        self.setFixedHeight(max(28, token_int("title_bar_height", 36)))

    def changeEvent(self, event: QEvent) -> None:  # type: ignore[override]
        super().changeEvent(event)
        if event.type() in {QEvent.Type.PaletteChange, QEvent.Type.StyleChange}:
            self._sync_metrics()

    def set_title(self, title: str) -> None:
        self._title.setText(title)

    def set_icon(self, name: str) -> None:
        self._icon_name = name
        self._icon.set_name(name)

    @property
    def icon_name(self) -> str:
        """当前标题栏图标名，主题 ``icons/`` 同名 svg 可覆盖。"""

        return self._icon_name

    def controls_rect_in(self, target: QWidget) -> QRect:
        """最小化 / 最大化 / 关闭在 ``target`` 坐标系下的并集，拉伸热区要避开。"""

        top_left = self._min.mapTo(target, QPoint(0, 0))
        bottom_right = self._close.mapTo(target, QPoint(self._close.width(), self._close.height()))
        return QRect(top_left, bottom_right).normalized()

    def sync_max_button(self) -> None:
        maximized = self._host.isMaximized()
        self._max.set_name("win-restore" if maximized else "win-max")
        self._max.setToolTip("还原" if maximized else "最大化")
        self._max.setAccessibleName(self._max.toolTip())

    def _toggle_max(self) -> None:
        if self._host.isMaximized():
            self._host.showNormal()
        else:
            self._host.showMaximized()
        self.sync_max_button()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_max()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            top_left = self._host.frameGeometry().topLeft()
            self._drag_offset = event.globalPosition().toPoint() - top_left
            self._drag_ratio = event.position().x() / max(self.width(), 1)
            self._drag_local_y = int(event.position().y())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_offset is None or not (event.buttons() & Qt.MouseButton.LeftButton):
            super().mouseMoveEvent(event)
            return
        global_pos = event.globalPosition().toPoint()
        if self._host.isMaximized():
            self._host.showNormal()
            self.sync_max_button()
            origin = drag_origin_after_restore(
                global_pos,
                self._host.frameGeometry().size(),
                self._drag_ratio,
                self._drag_local_y,
            )
            self._host.move(origin)
            self._drag_offset = global_pos - self._host.frameGeometry().topLeft()
            event.accept()
            return
        self._host.move(global_pos - self._drag_offset)
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_offset = None
        super().mouseReleaseEvent(event)
