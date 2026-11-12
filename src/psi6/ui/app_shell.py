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

from psi6.theme.apply import apply_psi6_button_style
from psi6.theme.runtime import token_color as theme_color
from psi6.theme.runtime import token_int, token_ms
from psi6.ui.icon import Icon, IconButton


@dataclass(frozen=True)
class NavDestination:
    """侧栏一项。``page_id`` 对应 ``AppShell.add_page``。

    ``badge`` 是右侧的短计数。``section`` 变化时在该项上方显示分组标题。
    ``caption`` 非空时，图标换成一枚字母标。``mark`` 指定字母，留空则取标题首字。
    """

    page_id: str
    title: str
    icon: str
    badge: str = ""
    section: str = ""
    caption: str = ""
    mark: str = ""


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
        self._root = root
        self._brand = QWidget()
        brand_row = QHBoxLayout(self._brand)
        brand_row.setContentsMargins(4, 0, 4, 16)
        brand_row.setSpacing(10)
        self._mark = QWidget()
        self._mark.setObjectName("psi6BrandMark")
        self._mark.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._mark.setFixedSize(36, 36)
        mark_layout = QHBoxLayout(self._mark)
        mark_layout.setContentsMargins(0, 0, 0, 0)
        self._brand_icon = Icon("file", size=18, tone="success")
        mark_layout.addWidget(self._brand_icon, alignment=Qt.AlignmentFlag.AlignCenter)
        brand_row.addWidget(self._mark)
        names = QVBoxLayout()
        names.setContentsMargins(0, 0, 0, 0)
        names.setSpacing(2)
        self._heading = QLabel(title)
        self._heading.setObjectName("psi6BrandTitle")
        names.addWidget(self._heading)
        self._caption = QLabel("")
        self._caption.setObjectName("psi6Hint")
        self._caption.hide()
        names.addWidget(self._caption)
        brand_row.addLayout(names, stretch=1)
        root.addWidget(self._brand)
        self._header_host = QWidget()
        self._header_layout = QVBoxLayout(self._header_host)
        self._header_layout.setContentsMargins(0, 0, 0, 8)
        self._header_host.hide()
        root.addWidget(self._header_host)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: dict[str, QPushButton] = {}
        self._section_labels: list[QLabel] = []
        previous_section = ""
        for item in destinations:
            if item.section and item.section != previous_section:
                previous_section = item.section
                caption = QLabel(item.section)
                caption.setObjectName("psi6NavSection")
                root.addWidget(caption)
                self._section_labels.append(caption)
            button = self._make_button(item)
            root.addWidget(button)
            self._buttons[item.page_id] = button
        root.addStretch()
        self._pinned_buttons: dict[str, QPushButton] = {}
        self._pinned = QVBoxLayout()
        self._pinned.setSpacing(4)
        root.addLayout(self._pinned)
        self._footer_host = QWidget()
        self._footer_layout = QVBoxLayout(self._footer_host)
        self._footer_layout.setContentsMargins(0, 8, 0, 0)
        self._footer_host.hide()
        root.addWidget(self._footer_host)
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
        self._caption.setVisible(bool(self._caption.text()) and not compact)
        self._header_host.setVisible(not compact and self._header_layout.count() > 0)
        self._footer_host.setVisible(not compact and self._footer_layout.count() > 0)
        for label in self._section_labels:
            label.setVisible(not compact)
        for button in (*self._buttons.values(), *self._pinned_buttons.values()):
            self._format_nav_text(button, compact=compact)
        for index in range(self._pinned.count()):
            pinned = self._pinned.itemAt(index)
            widget = pinned.widget() if pinned is not None else None
            if isinstance(widget, QLabel):
                widget.setVisible(not compact)
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
        button = self._buttons.get(page_id) or self._pinned_buttons.get(page_id)
        if button is not None:
            button.setChecked(True)

    def set_brand(self, title: str, caption: str = "", icon: str = "file") -> None:
        """侧栏顶部的产品名、一行小字和图标。"""

        self._heading.setText(title)
        self._caption.setText(caption)
        self._caption.setVisible(bool(caption) and not self._compact)
        self._brand_icon.set_name(icon)

    def set_badge(self, page_id: str, badge: str) -> None:
        """更新某一项右侧的计数。空字符串会把计数拿掉。"""

        button = self._buttons.get(page_id)
        if button is None:
            return
        button.setProperty("psi6Badge", badge)
        self._format_nav_text(button, compact=self._compact)

    def set_header_widget(self, widget: QWidget) -> None:
        """放在导航上方的控件，例如「新建」主按钮。再次调用会换掉上一个。"""

        self._replace_slot(self._header_host, self._header_layout, widget)

    def set_footer_widget(self, widget: QWidget) -> None:
        """放在最近任务和折叠按钮之间。"""

        self._replace_slot(self._footer_host, self._footer_layout, widget)

    def _replace_slot(self, host: QWidget, layout: QVBoxLayout, widget: QWidget) -> None:
        while layout.count():
            item = layout.takeAt(0)
            previous = item.widget() if item is not None else None
            if previous is not None:
                previous.hide()
                previous.deleteLater()
        layout.addWidget(widget)
        host.setVisible(not self._compact)

    def set_pinned(self, items: Sequence[NavDestination]) -> None:
        """替换折叠按钮上方的快捷项，例如最近打开的任务。

        再次调用会换掉上一组。点选后同样发出 ``destination_changed``。
        """

        while self._pinned.count():
            item = self._pinned.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is None:
                continue
            if isinstance(widget, QPushButton):
                self._group.removeButton(widget)
            widget.hide()
            widget.deleteLater()
        self._pinned_buttons.clear()
        if items and not self._compact:
            caption = QLabel("最近使用")
            caption.setObjectName("psi6NavSection")
            self._pinned.addWidget(caption)
        for item in items:
            button = self._make_button(item)
            self._pinned.addWidget(button)
            self._pinned_buttons[item.page_id] = button

    def pinned_button(self, page_id: str) -> QPushButton | None:
        """最近任务里的那个按钮。没有这一项时返回 ``None``。"""

        return self._pinned_buttons.get(page_id)

    def _make_button(self, item: NavDestination) -> QPushButton:
        button = QPushButton()
        button.setObjectName("psi6NavItem")
        apply_psi6_button_style(button)
        button.setCheckable(True)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setAccessibleName(item.title)
        button.setProperty("psi6NavTitle", item.title)
        button.setProperty("psi6Badge", item.badge)
        button.setProperty("psi6NavCaption", item.caption)
        button.setProperty("psi6IconName", item.icon)
        self._group.addButton(button)
        button.clicked.connect(lambda _=False, page_id=item.page_id: self._emit(page_id))
        button.toggled.connect(
            lambda _checked, host=button, icon_name=item.icon: self._paint_nav_icon(host, icon_name)
        )
        row = QHBoxLayout(button)
        row.setContentsMargins(8, 4, 8, 4)
        row.setSpacing(8)
        if item.caption:
            letter = QLabel(item.mark or item.title[:1] or "·")
            letter.setObjectName("psi6MiniMark")
            letter.setAlignment(Qt.AlignmentFlag.AlignCenter)
            letter.setFixedSize(28, 30)
            letter.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            row.addWidget(letter)
        else:
            icon = Icon(item.icon or "file", size=16)
            icon.setObjectName("psi6NavIcon")
            row.addWidget(icon)
        text = QVBoxLayout()
        text.setContentsMargins(0, 0, 0, 0)
        text.setSpacing(1)
        title = QLabel(item.title)
        title.setObjectName("psi6NavLabel")
        title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        text.addWidget(title)
        caption = QLabel(item.caption)
        caption.setObjectName("psi6NavCaption")
        caption.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        if not item.caption:
            caption.hide()
        text.addWidget(caption)
        row.addLayout(text, stretch=1)
        badge = QLabel(item.badge)
        badge.setObjectName("psi6NavBadge")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        if not item.badge:
            badge.hide()
        row.addWidget(badge)
        if item.caption:
            button.setMinimumHeight(48)
        self._format_nav_text(button, compact=self._compact)
        self._paint_nav_icon(button, item.icon)
        return button

    def _format_nav_text(self, button: QPushButton, *, compact: bool) -> None:
        title = button.property("psi6NavTitle")
        label = title if isinstance(title, str) else ""
        badge = button.property("psi6Badge")
        mark = badge if isinstance(badge, str) else ""
        caption = button.property("psi6NavCaption")
        note = caption if isinstance(caption, str) else ""
        button.setProperty("compact", compact)
        button.style().unpolish(button)
        button.style().polish(button)
        title_label = button.findChild(QLabel, "psi6NavLabel")
        caption_label = button.findChild(QLabel, "psi6NavCaption")
        badge_label = button.findChild(QLabel, "psi6NavBadge")
        if compact:
            button.setToolTip(label)
            if title_label is not None:
                title_label.hide()
            if caption_label is not None:
                caption_label.hide()
            if badge_label is not None:
                badge_label.hide()
            return
        button.setToolTip("")
        if title_label is not None:
            title_label.setText(label)
            title_label.show()
        if caption_label is not None:
            caption_label.setText(note)
            caption_label.setVisible(bool(note))
        if badge_label is not None:
            badge_label.setText(mark)
            badge_label.setVisible(bool(mark))

    def _emit(self, page_id: str) -> None:
        self.destination_changed.emit(page_id)

    def _paint_nav_icon(self, button: QPushButton, name: str) -> None:
        icon = button.findChild(Icon, "psi6NavIcon")
        if icon is None or not name:
            return
        icon.set_name(name)
        key = "color_primary" if button.isChecked() else "color_sidebar_text"
        icon.setProperty("psi6IconColor", theme_color(key))
        icon.update()

    def refresh_icons(self) -> None:
        """主题切换后重绘侧栏图标。"""

        for button in (*self._buttons.values(), *self._pinned_buttons.values()):
            name = button.property("psi6IconName")
            if isinstance(name, str):
                self._paint_nav_icon(button, name)
        self._toggle.refresh()

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
        column = QWidget()
        column_layout = QVBoxLayout(column)
        column_layout.setContentsMargins(0, 0, 0, 0)
        column_layout.setSpacing(0)
        self._header_host = QWidget()
        self._header_host.setObjectName("psi6ContentHeader")
        self._header_host.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._header_layout = QVBoxLayout(self._header_host)
        self._header_layout.setContentsMargins(16, 8, 16, 8)
        self._header_host.hide()
        column_layout.addWidget(self._header_host)
        self._stack = QStackedWidget()
        column_layout.addWidget(self._stack, stretch=1)
        layout.addWidget(column, stretch=1)
        self._order = [item.page_id for item in destinations]

    def set_sidebar_compact(self, compact: bool) -> None:
        self.sidebar.set_compact(compact)

    def set_pinned(self, items: Sequence[NavDestination]) -> None:
        """侧栏底部的快捷项，用来放最近任务。未知页面编号不会切换内容栈。"""

        self.sidebar.set_pinned(items)

    def pinned_button(self, page_id: str) -> QPushButton | None:
        """最近任务里的那个按钮。没有这一项时返回 ``None``。"""

        return self.sidebar.pinned_button(page_id)

    def set_brand(self, title: str, caption: str = "", icon: str = "file") -> None:
        self.sidebar.set_brand(title, caption, icon)

    def set_badge(self, page_id: str, badge: str) -> None:
        self.sidebar.set_badge(page_id, badge)

    def set_header_widget(self, widget: QWidget) -> None:
        self.sidebar.set_header_widget(widget)

    def set_footer_widget(self, widget: QWidget) -> None:
        self.sidebar.set_footer_widget(widget)

    def set_content_header(self, widget: QWidget) -> None:
        """内容区顶部，用来放面包屑和账号。再次调用会换掉上一个。"""

        while self._header_layout.count():
            item = self._header_layout.takeAt(0)
            previous = item.widget() if item is not None else None
            if previous is not None:
                previous.hide()
                previous.deleteLater()
        self._header_layout.addWidget(widget)
        self._header_host.show()

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
