"""应用壳：左侧导航 + 页面栈，工具/监控/聊天等共用。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from PySide6.QtCore import Property, QEasingCurve, QEvent, QPropertyAnimation, Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from psi6.theme.runtime import token_int, token_ms
from psi6.ui.icon import IconButton, token_color


@dataclass(frozen=True)
class NavDestination:
    """侧栏一项。``page_id`` 对应 ``AppShell.add_page``。"""

    page_id: str
    title: str
    icon: str


class Sidebar(QWidget):
    """窄侧栏。可展开为标题+图标，或收成仅图标轨道。"""

    destination_changed = Signal(str)
    compact_changed = Signal(bool)

    def __init__(
        self,
        destinations: Sequence[NavDestination],
        *,
        title: str = "psi6",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("psi6Sidebar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._compact = False
        self._destinations = list(destinations)
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 16, 12, 12)
        root.setSpacing(4)
        self._heading = QLabel(title)
        self._heading.setObjectName("psi6SidebarTitle")
        root.addWidget(self._heading)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: dict[str, QPushButton] = {}
        for index, item in enumerate(destinations):
            button = QPushButton(f"  {item.title}")
            button.setObjectName("psi6NavItem")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setAccessibleName(item.title)
            button.setProperty("psi6NavTitle", item.title)
            button.setProperty("psi6IconName", item.icon)
            button.setProperty("compact", False)
            self._group.addButton(button, index)
            button.clicked.connect(lambda _=False, page_id=item.page_id: self._emit(page_id))
            root.addWidget(button)
            self._buttons[item.page_id] = button
            self._paint_nav_icon(button, item.icon)
        root.addStretch()
        self._toggle = IconButton("sidebar", label="收起侧栏")
        self._toggle.clicked.connect(self.toggle_compact)
        root.addWidget(self._toggle, alignment=Qt.AlignmentFlag.AlignLeft)
        if destinations:
            first = destinations[0].page_id
            self._buttons[first].setChecked(True)
        self._rail_width = self._target_width()
        self._width_ani = QPropertyAnimation(self, b"railWidth", self)
        self._width_ani.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.apply_metrics()

    def is_compact(self) -> bool:
        return self._compact

    def set_compact(self, compact: bool) -> None:
        """``True`` 为仅图标轨道。"""

        changed = compact != self._compact
        self._compact = compact
        self._heading.setVisible(not compact)
        for button in self._buttons.values():
            title = button.property("psi6NavTitle")
            label = title if isinstance(title, str) else button.text()
            button.setProperty("compact", compact)
            button.style().unpolish(button)
            button.style().polish(button)
            if compact:
                button.setText("")
                button.setToolTip(label)
            else:
                button.setText(f"  {label}")
                button.setToolTip("")
        hint = "展开侧栏" if compact else "收起侧栏"
        self._toggle.setToolTip(hint)
        self._toggle.setAccessibleName(hint)
        self.apply_metrics(animate=changed)
        if changed:
            self.compact_changed.emit(compact)

    def toggle_compact(self) -> None:
        self.set_compact(not self._compact)

    def _target_width(self) -> int:
        key = "sidebar_compact_width" if self._compact else "sidebar_width"
        fallback = 56 if self._compact else 212
        return token_int(key, fallback)

    def _get_rail_width(self) -> int:
        return self._rail_width

    def _set_rail_width(self, value: int) -> None:
        self._rail_width = max(48, int(value))
        self.setFixedWidth(self._rail_width)

    railWidth = Property(int, _get_rail_width, _set_rail_width)

    def apply_metrics(self, *, animate: bool = False) -> None:
        """按当前 token 与密度重算宽度。主题切换后调用。"""

        target = self._target_width()
        margins = (8, 12, 8, 8) if self._compact else (12, 16, 12, 12)
        layout = self.layout()
        if layout is not None:
            layout.setContentsMargins(*margins)
        duration = token_ms() if animate else 0
        if hasattr(self, "_width_ani"):
            self._width_ani.stop()
        if duration <= 0 or target == self.width():
            self._set_rail_width(target)
            return
        self._width_ani.setDuration(duration)
        self._width_ani.setStartValue(self.width())
        self._width_ani.setEndValue(target)
        self._width_ani.start()

    def select(self, page_id: str) -> None:
        button = self._buttons.get(page_id)
        if button is not None:
            button.setChecked(True)

    def _emit(self, page_id: str) -> None:
        self.destination_changed.emit(page_id)

    def _paint_nav_icon(self, button: QPushButton, name: str) -> None:
        from psi6.icons.render import icon_for

        button.setIcon(icon_for(name, color=token_color(button), size=token_int("icon_size", 16)))

    def refresh_icons(self) -> None:
        """主题切换后重绘侧栏图标。"""

        for button in self._buttons.values():
            name = button.property("psi6IconName")
            if isinstance(name, str):
                self._paint_nav_icon(button, name)
        self._toggle.changeEvent(QEvent(QEvent.Type.PaletteChange))

    def changeEvent(self, event: QEvent) -> None:  # type: ignore[override]
        super().changeEvent(event)
        if event.type() in {QEvent.Type.PaletteChange, QEvent.Type.StyleChange}:
            self.apply_metrics()
            self.refresh_icons()


class AppShell(QWidget):
    """桌面程序主结构：侧栏选页面，内容区切栈。"""

    page_changed = Signal(str)

    def __init__(
        self,
        destinations: Sequence[NavDestination],
        *,
        title: str = "psi6",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("psi6AppShell")
        self._pages: dict[str, QWidget] = {}
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.sidebar = Sidebar(destinations, title=title)
        self.sidebar.destination_changed.connect(self.show_page)
        layout.addWidget(self.sidebar)
        self._stack = QStackedWidget()
        layout.addWidget(self._stack, stretch=1)
        self._order = [item.page_id for item in destinations]

    def set_sidebar_compact(self, compact: bool) -> None:
        self.sidebar.set_compact(compact)

    def add_page(self, page_id: str, widget: QWidget) -> None:
        """注册一页。``page_id`` 必须出现在 destinations 中。"""

        self._pages[page_id] = widget
        self._stack.addWidget(widget)

    def show_page(self, page_id: str) -> None:
        widget = self._pages.get(page_id)
        if widget is None:
            return
        self._stack.setCurrentWidget(widget)
        self.sidebar.select(page_id)
        self.page_changed.emit(page_id)

    def current_id(self) -> str:
        current = self._stack.currentWidget()
        for page_id, widget in self._pages.items():
            if widget is current:
                return page_id
        return self._order[0] if self._order else ""
