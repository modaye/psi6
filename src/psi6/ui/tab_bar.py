"""文档工作区的标签条。自己绘制，不用传统 ``QTabBar`` 的边框页签。"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QEvent, QPoint, QRect, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QKeyEvent, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QTabBar, QWidget

from psi6.icons.render import device_ratio, pixmap_for
from psi6.theme.apply import keyboard_focus_ring
from psi6.theme.paint import as_color, create_painter
from psi6.theme.runtime import token_color, token_int
from psi6.ui.tab_item import MIN_TAB_WIDTH, close_visible, modified_dot_visible, tab_width


class WorkspaceTabBar(QTabBar):
    """选中标签是内容表面的延伸。关闭按钮按悬停显隐。"""

    blank_activated = Signal()
    close_at = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("psi6WorkspaceTabBar")
        self.setDrawBase(False)
        self.setExpanding(False)
        self.setUsesScrollButtons(True)
        self.setElideMode(Qt.TextElideMode.ElideRight)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self._closable = True
        self._hover = -1
        self._close_hover = False
        self._document_keys: Callable[[QKeyEvent], bool] | None = None

    def set_closable(self, closable: bool) -> None:
        """是否在标签上画关闭。程序化 ``close_tab`` 不受这一个开关影响。"""

        self._closable = bool(closable)
        self.update()

    def document_closable(self) -> bool:
        return self._closable

    def set_document_keys(self, handler: Callable[[QKeyEvent], bool]) -> None:
        """Ctrl+Tab 等由文档区处理，标签条不再按顺序轮换。"""

        self._document_keys = handler

    def tabSizeHint(self, index: int) -> QSize:
        """短标题保持 180，长标题不超过 240。高度跟紧凑控件。"""

        height = max(24, token_int("control_height_sm", 28))
        text = self.fontMetrics().horizontalAdvance(self.tabText(index))
        width = tab_width(text, has_icon=bool(self._fields(index).get("icon")))
        return QSize(width, height)

    def minimumTabSizeHint(self, index: int) -> QSize:
        """放不下时可以收到 112，再窄就滚动，不压成几个省略号。"""

        hint = self.tabSizeHint(index)
        return QSize(MIN_TAB_WIDTH, hint.height())

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        with create_painter(self) as painter:
            painter.fillRect(self.rect(), as_color(token_color("color_bg")))
            seam = as_color(token_color("color_border_subtle"))
            painter.fillRect(0, self.height() - 1, self.width(), 1, seam)
            for index in range(self.count()):
                self._paint_tab(painter, index)

    def event(self, event: QEvent) -> bool:
        """Ctrl+Tab 留给 ``TabView`` 做最近使用切换，不按标签顺序轮转。"""

        if event.type() == QEvent.Type.ShortcutOverride and isinstance(event, QKeyEvent):
            ctrl = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
            switching = event.key() in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab)
            if ctrl and switching:
                event.ignore()
                return False
        return super().event(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """标签条默认会用 Ctrl+Tab 按顺序轮换。文档区改走最近使用。"""

        if self._document_keys is not None and self._document_keys(event):
            event.accept()
            return
        super().keyPressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self._track(event.position().toPoint())
        super().mouseMoveEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self._hover = -1
        self._close_hover = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        index = self.tabAt(event.position().toPoint())
        if (
            event.button() == Qt.MouseButton.LeftButton
            and index >= 0
            and self._close_hit(index, event.position().toPoint())
        ):
            self.close_at.emit(index)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            index = self.tabAt(event.position().toPoint())
            if index >= 0 and self._may_close(index, hovered=True):
                self.close_at.emit(index)
                event.accept()
                return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        on_blank = self.tabAt(event.position().toPoint()) < 0
        if event.button() == Qt.MouseButton.LeftButton and on_blank:
            self.blank_activated.emit()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def _fields(self, index: int) -> dict[str, Any]:
        data = self.tabData(index)
        return data if isinstance(data, dict) else {}

    def _may_close(self, index: int, *, hovered: bool) -> bool:
        fields = self._fields(index)
        return close_visible(
            closable=self._closable,
            pinned=bool(fields.get("pinned")),
            selected=index == self.currentIndex(),
            hovered=hovered,
            modified=bool(fields.get("modified")),
        )

    def _close_rect(self, tab: QRect) -> QRect:
        side = 16
        return QRect(tab.right() - side - 8, tab.center().y() - side // 2, side, side)

    def _close_hit(self, index: int, pos: QPoint) -> bool:
        if not self._may_close(index, hovered=index == self._hover):
            return False
        return self._close_rect(self.tabRect(index)).contains(pos)

    def _track(self, pos: QPoint) -> None:
        index = self.tabAt(pos)
        close = index >= 0 and self._close_rect(self.tabRect(index)).contains(pos)
        if index != self._hover or close != self._close_hover:
            self._hover = index
            self._close_hover = close
            self.update()

    def _paint_tab(self, painter: QPainter, index: int) -> None:
        rect = self.tabRect(index)
        if not rect.isValid() or rect.width() <= 0:
            return
        fields = self._fields(index)
        selected = index == self.currentIndex()
        hovered = index == self._hover
        surface = as_color(token_color("color_surface"))
        if selected:
            cover = QRect(rect.x(), rect.y(), rect.width(), self.height() - rect.y())
            painter.fillRect(cover, surface)
        elif hovered:
            painter.fillRect(rect.adjusted(0, 2, 0, -2), as_color(token_color("color_hover")))
        self._paint_icon(painter, rect, str(fields.get("icon") or ""), selected or hovered)
        showing_close = self._may_close(index, hovered=hovered)
        if showing_close:
            self._paint_close(
                painter,
                self._close_rect(rect),
                hot=hovered and self._close_hover,
                raised=hovered,
            )
        elif modified_dot_visible(modified=bool(fields.get("modified")), showing_close=False):
            self._paint_dot(painter, self._close_rect(rect))
        self._paint_title(
            painter,
            rect,
            index,
            selected or hovered,
            has_icon=bool(fields.get("icon")),
        )
        if selected and keyboard_focus_ring(self):
            self._paint_focus(painter, rect)

    def _paint_icon(self, painter: QPainter, tab: QRect, name: str, active: bool) -> None:
        if not name:
            return
        color = token_color("color_text" if active else "color_muted")
        size = max(12, token_int("icon_size", 16))
        try:
            pixmap = pixmap_for(name, color=color, size=size, ratio=device_ratio(self))
        except (OSError, ValueError):
            return
        x = tab.x() + 10
        y = tab.center().y() - size // 2
        painter.drawPixmap(x, y, pixmap)

    def _paint_title(
        self,
        painter: QPainter,
        tab: QRect,
        index: int,
        active: bool,
        *,
        has_icon: bool,
    ) -> None:
        left = tab.x() + (32 if has_icon else 12)
        right = tab.right() - 28
        text_rect = QRect(left, tab.y(), max(8, right - left), tab.height())
        color = QColor(token_color("color_text" if active else "color_muted"))
        painter.setPen(color)
        label = painter.fontMetrics().elidedText(
            self.tabText(index),
            Qt.TextElideMode.ElideRight,
            text_rect.width(),
        )
        flags = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        painter.drawText(text_rect, int(flags), label)
        painter.setPen(Qt.PenStyle.NoPen)

    def _paint_close(self, painter: QPainter, rect: QRect, *, hot: bool, raised: bool) -> None:
        if hot or raised:
            tone = "color_pressed" if hot else "color_hover"
            painter.setBrush(as_color(token_color(tone)))
            painter.drawRoundedRect(QRectF(rect), 4, 4)
        color = as_color(token_color("color_text" if hot else "color_muted"))
        pen = QPen(color)
        pen.setWidthF(1.4)
        painter.setPen(pen)
        inset = 4.5
        painter.drawLine(
            QPoint(int(rect.left() + inset), int(rect.top() + inset)),
            QPoint(int(rect.right() - inset), int(rect.bottom() - inset)),
        )
        painter.drawLine(
            QPoint(int(rect.right() - inset), int(rect.top() + inset)),
            QPoint(int(rect.left() + inset), int(rect.bottom() - inset)),
        )
        painter.setPen(Qt.PenStyle.NoPen)

    def _paint_focus(self, painter: QPainter, tab: QRect) -> None:
        pen = QPen(as_color(token_color("color_focus")))
        pen.setWidth(max(1, token_int("focus_ring_width", 2)))
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(tab.adjusted(3, 3, -3, -4)), 4, 4)
        painter.setPen(Qt.PenStyle.NoPen)

    def _paint_dot(self, painter: QPainter, slot: QRect) -> None:
        painter.setBrush(as_color(token_color("color_primary")))
        side = 6
        dot = QRect(0, 0, side, side)
        dot.moveCenter(slot.center())
        painter.drawEllipse(dot)
