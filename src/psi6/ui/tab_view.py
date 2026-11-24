"""文档工作区标签：可关闭、可重排，布局状态可序列化。

内容仍由 ``QTabWidget`` 管。标签条自己绘制：选中项与内容表面连在一起，
关闭按钮按悬停出现。标签顺序与内容页由 ``key`` 关联，调用方持有
``QWidget``：关闭只是把控件交还，不会销毁。最近关闭且控件仍有效的，
可以用 ``reopen_last`` 放回来。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import Property, QEvent, QObject, QPoint, QRectF, Qt, Signal
from PySide6.QtGui import QGuiApplication, QKeyEvent, QPaintEvent
from PySide6.QtWidgets import QStackedWidget, QTabBar, QTabWidget, QVBoxLayout, QWidget

from psi6.runtime.config import ConfigStore
from psi6.theme.paint import as_color, create_painter
from psi6.theme.runtime import token_color
from psi6.ui import motion
from psi6.ui.context_menu import MenuAction, MenuTarget, attach_context_menu
from psi6.ui.empty_state import EmptyState
from psi6.ui.tab_bar import WorkspaceTabBar
from psi6.ui.tab_item import TabItem
from psi6.ui.tab_overflow import TabOverflowButton

_DEFAULT_STATE_FILE = "tabs.json"


class _ActiveMark(QWidget):
    """贴在文档页签底部的主色条。切换时滑到新页签，不推动布局。"""

    def __init__(self, bar: QTabBar) -> None:
        super().__init__(bar)
        self._bar = bar
        self._x = 0.0
        self._w = 0.0
        self._syncing = False
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        bar.installEventFilter(self)
        bar.currentChanged.connect(lambda _index: self.follow(True))
        bar.tabMoved.connect(lambda *_args: self.follow(False))
        self.follow(False)

    def _get_x(self) -> float:
        return self._x

    def _set_x(self, value: float) -> None:
        self._x = float(value)
        self.update()

    def _get_w(self) -> float:
        return self._w

    def _set_w(self, value: float) -> None:
        self._w = float(value)
        self.update()

    markX = Property(float, _get_x, _set_x)
    markW = Property(float, _get_w, _set_w)

    def follow(self, animate: bool) -> None:
        """把指示器放到当前页签下。``animate`` 为假时直接到位（缩放、拖动）。"""

        if self._syncing:
            return
        self._syncing = True
        try:
            index = self._bar.currentIndex()
            if index < 0 or self._bar.height() < 4:
                self.hide()
                return
            rect = self._bar.tabRect(index)
            target_x = float(rect.x())
            target_w = max(12.0, float(rect.width()))
            self.setGeometry(0, self._bar.height() - 2, self._bar.width(), 2)
            self.show()
            self.raise_()
            if not animate:
                motion.stop(self, "markX")
                motion.stop(self, "markW")
                self._x = target_x
                self._w = target_w
                self.update()
                return
            motion.animate(self, "markX", self._x, target_x, speed="normal")
            motion.animate(self, "markW", self._w, target_w, speed="normal")
        finally:
            self._syncing = False

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self._bar and event.type() in (
            QEvent.Type.Resize,
            QEvent.Type.Show,
        ):
            self.follow(False)
        return False

    def paintEvent(self, _event: QPaintEvent) -> None:
        with create_painter(self) as painter:
            painter.setBrush(as_color(token_color("color_primary")))
            painter.drawRect(QRectF(self._x, 0, self._w, 2))


@dataclass
class _ClosedDocument:
    """最近关掉的一份文档。控件若已被销毁，恢复时跳过。"""

    key: str
    title: str
    widget: QWidget
    icon: str
    path: str
    modified: bool
    pinned: bool


class TabView(QWidget):
    """一组文档标签。选中项与内容区同一表面，顺序可拖动调整。

    状态默认只记 ``key`` 的顺序和当前项，不记控件本身：恢复布局时应用先用
    ``add_tab`` 把控件放回来，再 ``set_state`` / ``restore_state`` 对齐顺序。
    因此 ``set_state`` 里出现但没有对应控件的 key 会被忽略，当前多出来的
    标签则追加到末尾，不会因为文件里少写几个 key 就丢掉已打开的文档。
    图标、路径、修改和固定只在用过这些字段时才写进状态。
    """

    current_changed = Signal(str)
    tab_closed = Signal(str)
    tab_moved = Signal(int, int)
    layout_changed = Signal()
    blank_activated = Signal()

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        closable: bool = True,
        movable: bool = True,
        empty_title: str = "没有打开的文档",
        empty_hint: str = "从左侧列表或新建动作打开一个。",
        state_file: str = _DEFAULT_STATE_FILE,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("psi6TabView")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._state_file = state_file
        self._keys: list[str] = []
        self._widgets: dict[str, QWidget] = {}
        self._items: dict[str, TabItem] = {}
        self._recent: list[str] = []
        self._closed: list[_ClosedDocument] = []
        self._updating = False
        self._current_emitted: str | None = None
        self._closable = bool(closable)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._tabs = QTabWidget()
        self._tabs.setObjectName("psi6TabViewTabs")
        self._tabs.setDocumentMode(True)
        self._bar = WorkspaceTabBar()
        self._tabs.setTabBar(self._bar)
        # 关闭图形由标签条自己画。Qt 自带的叉会一直占着位置。
        self._tabs.setTabsClosable(False)
        self._tabs.setMovable(movable)
        self._bar.set_closable(self._closable)
        self._bar.set_document_keys(self._dispatch_document_key)
        self._overflow = TabOverflowButton(self._tabs)
        self._overflow.bind(
            rows=self._document_rows,
            recent=lambda: list(self._recent),
            icon_name=self.icon,
            activate=self.set_current,
        )
        self._tabs.setCornerWidget(self._overflow, Qt.Corner.TopRightCorner)
        self._empty = EmptyState(empty_title, empty_hint)
        self._view = QStackedWidget()
        self._view.addWidget(self._tabs)
        self._view.addWidget(self._empty)
        layout.addWidget(self._view, stretch=1)

        self._tabs.currentChanged.connect(self._on_current)
        self._tabs.tabCloseRequested.connect(self._on_close_requested)
        self._bar.close_at.connect(self._on_close_requested)
        self._bar.blank_activated.connect(self.blank_activated.emit)
        self._bar.tabMoved.connect(self._on_moved)
        self._mark = _ActiveMark(self._bar)
        self.context_menu(self._document_menu)
        self._sync_empty()

    def context_menu(self, builder: Callable[[MenuTarget], Sequence[MenuAction] | None]) -> QTabBar:
        """在页签条上挂右键菜单，返回 ``QTabBar``。

        ``builder`` 拿到命中页签的 ``MenuTarget``：``key`` 是页签 key，``data`` 是标题。
        右键落在页签条空白处时退回当前页签；一份文档都没有时 ``target.hit`` 为 ``False``。
        """

        return attach_context_menu(self, builder)  # type: ignore[return-value]

    def _context_menu_source(self) -> QWidget:
        return self._tabs.tabBar()

    def _context_menu_target(self, pos: QPoint) -> MenuTarget | None:
        bar = self._tabs.tabBar()
        index = bar.tabAt(pos)
        if not 0 <= index < len(self._keys):
            # 空白处：有当前页就针对当前页，没有就交给调用方决定要不要弹空菜单。
            # 注意 current_key() 一个都没打开时返回空串（既有契约），这里按索引判断。
            index = self._tabs.currentIndex()
            if not 0 <= index < len(self._keys):
                return MenuTarget("tabs", position=pos)
        key = self._keys[index]
        # 右键落在未选中的页签：先切过去，菜单里的「当前页」才和行为一致。
        if self._tabs.currentIndex() != index:
            self._tabs.setCurrentIndex(index)
        return MenuTarget("tabs", key=key, data=self.title(key), position=pos)

    def add_tab(self, key: str, title: str, widget: QWidget) -> None:
        """打开一个文档。``key`` 已存在时只切到它，不重复插入。"""

        key = str(key)
        if key in self._widgets:
            self.set_current(key)
            return
        self._keys.append(key)
        self._widgets[key] = widget
        self._items[key] = TabItem(key, str(title))
        self._tabs.addTab(widget, title)
        self._write_bar(key)
        self._touch_recent(key)
        self._sync_empty()
        self._refresh_overflow()
        self.layout_changed.emit()

    def close_tab(self, key: str) -> bool:
        """关闭并把控件交还调用方（``setParent(None)``，不 ``deleteLater``）。"""

        if key not in self._widgets:
            return False
        index = self._keys.index(key)
        item = self._items.get(key, TabItem(key, self.title(key)))
        widget = self._widgets.pop(key)
        self._remember_closed(item, widget)
        self._updating = True
        try:
            self._keys.pop(index)
            self._items.pop(key, None)
            self._recent = [item_key for item_key in self._recent if item_key != key]
            self._tabs.removeTab(index)
            widget.hide()
            widget.setParent(None)
        finally:
            self._updating = False
        self._sync_empty()
        self._refresh_overflow()
        self.tab_closed.emit(key)
        # removeTab 会自己选新页，但那次 currentChanged 被 _updating 挡掉了。
        self._emit_current()
        self.layout_changed.emit()
        return True

    def close_all(self) -> None:
        for key in list(self._keys):
            self.close_tab(key)

    def keys(self) -> list[str]:
        """当前标签顺序对应的 key。"""

        return list(self._keys)

    def count(self) -> int:
        return len(self._keys)

    def widget(self, key: str) -> QWidget | None:
        return self._widgets.get(key)

    def title(self, key: str) -> str:
        if key not in self._keys:
            return ""
        return self._tabs.tabText(self._keys.index(key))

    def set_title(self, key: str, title: str) -> None:
        if key in self._keys:
            self._items[key].title = str(title)
            self._tabs.setTabText(self._keys.index(key), title)
            self._bar.update()

    def icon(self, key: str) -> str:
        """标签左侧图标名。没有则是空串。"""

        item = self._items.get(key)
        return item.icon if item is not None else ""

    def set_icon(self, key: str, name: str) -> None:
        """设置文件类型图标。空串表示不画图标。未知名字在绘制时跳过。"""

        item = self._items.get(key)
        if item is None:
            return
        item.icon = str(name)
        self._write_bar(key)

    def path(self, key: str) -> str:
        item = self._items.get(key)
        return item.path if item is not None else ""

    def set_path(self, key: str, path: str) -> None:
        """供「复制文件路径」使用。不参与标签宽度。"""

        item = self._items.get(key)
        if item is not None:
            item.path = str(path)

    def modified(self, key: str) -> bool:
        item = self._items.get(key)
        return bool(item and item.modified)

    def set_modified(self, key: str, modified: bool) -> None:
        """未保存时在关闭按钮的位置画一个点。悬停时点让位给关闭。"""

        item = self._items.get(key)
        if item is None:
            return
        item.modified = bool(modified)
        self._write_bar(key)

    def pinned(self, key: str) -> bool:
        item = self._items.get(key)
        return bool(item and item.pinned)

    def set_pinned(self, key: str, pinned: bool) -> None:
        """固定的标签排到左侧，标签条上不画关闭。"""

        if self._store_pinned(key, pinned):
            self._gather_pins()

    def _store_pinned(self, key: str, pinned: bool) -> bool:
        item = self._items.get(key)
        if item is None:
            return False
        item.pinned = bool(pinned)
        self._write_bar(key)
        return True

    def close_others(self, key: str) -> None:
        """关掉除 ``key`` 和固定标签以外的文档。"""

        for item_key in list(self._keys):
            if item_key != key and not self.pinned(item_key):
                self.close_tab(item_key)

    def close_right(self, key: str) -> None:
        """关掉 ``key`` 右侧未固定的文档。"""

        if key not in self._keys:
            return
        start = self._keys.index(key) + 1
        for item_key in list(self._keys[start:]):
            if not self.pinned(item_key):
                self.close_tab(item_key)

    def reopen_last(self) -> bool:
        """把最近关闭、且控件还活着的文档放回来。没有可恢复的则返回 ``False``。"""

        while self._closed:
            closed = self._closed.pop()
            if closed.key in self._widgets or not _widget_alive(closed.widget):
                continue
            self.add_tab(closed.key, closed.title, closed.widget)
            self.set_icon(closed.key, closed.icon)
            self.set_path(closed.key, closed.path)
            self.set_modified(closed.key, closed.modified)
            self.set_pinned(closed.key, closed.pinned)
            self.set_current(closed.key)
            return True
        return False

    def current_key(self) -> str:
        """当前文档 key；一个都没打开时是空串。"""

        index = self._tabs.currentIndex()
        return self._keys[index] if 0 <= index < len(self._keys) else ""

    def set_current(self, key: str) -> None:
        if key in self._keys:
            self._tabs.setCurrentIndex(self._keys.index(key))

    def state(self) -> dict[str, Any]:
        """可 JSON 化的布局状态：标签顺序 + 当前项。

        没有图标、路径、修改或固定时，字典只有 ``keys`` 和 ``current``。
        """

        payload: dict[str, Any] = {"keys": list(self._keys), "current": self.current_key()}
        items: dict[str, dict[str, Any]] = {}
        for key in self._keys:
            item = self._items.get(key)
            if item is None:
                continue
            extra: dict[str, Any] = {}
            if item.icon:
                extra["icon"] = item.icon
            if item.path:
                extra["path"] = item.path
            if item.modified:
                extra["modified"] = True
            if item.pinned:
                extra["pinned"] = True
            if extra:
                items[key] = extra
        if items:
            payload["items"] = items
        return payload

    def set_state(self, state: Mapping[str, Any]) -> None:
        """按状态重排已有标签。缺失 / 多余 / 类型不对的字段都安全跳过。"""

        raw = state.get("keys")
        if not isinstance(raw, (list, tuple)):
            return
        wanted: list[str] = []
        for item in raw:
            key = str(item)
            if key in self._widgets and key not in wanted:
                wanted.append(key)
        for key in self._keys:
            if key not in wanted:
                wanted.append(key)
        self._reorder(wanted)
        raw_items = state.get("items")
        if isinstance(raw_items, Mapping):
            for key, extra in raw_items.items():
                if key not in self._items or not isinstance(extra, Mapping):
                    continue
                if "icon" in extra:
                    self.set_icon(str(key), str(extra.get("icon") or ""))
                if "path" in extra:
                    self.set_path(str(key), str(extra.get("path") or ""))
                if "modified" in extra:
                    self.set_modified(str(key), bool(extra.get("modified")))
                if "pinned" in extra:
                    self._store_pinned(str(key), bool(extra.get("pinned")))
            self._gather_pins()
        current = state.get("current")
        if isinstance(current, str) and current in self._widgets:
            self.set_current(current)
        self._sync_empty()
        self._emit_current()
        self.layout_changed.emit()

    def save_state(self, store: ConfigStore, app_name: str) -> None:
        """把布局写进应用的 JSON 数据目录。"""

        store.save_data(app_name, self._state_file, self.state())

    def restore_state(self, store: ConfigStore, app_name: str) -> bool:
        """读回布局；文件不存在或损坏时返回 ``False``，布局保持原样。"""

        payload = store.load_data(app_name, self._state_file)
        if not payload:
            return False
        self.set_state(payload)
        return True

    def _on_current(self, index: int) -> None:
        del index
        if self._updating:
            return
        self._touch_recent(self.current_key())
        self._emit_current()
        self._bar.update()

    def _emit_current(self) -> None:
        # removeTab / set_state 之后 Qt 可能不发 currentChanged，这里补发；
        # 去重避免同一次操作里把同一个 key 播两遍。
        key = self.current_key()
        self._touch_recent(key)
        if key == self._current_emitted:
            return
        self._current_emitted = key
        self.current_changed.emit(key)

    def _on_close_requested(self, index: int) -> None:
        if 0 <= index < len(self._keys):
            self.close_tab(self._keys[index])

    def _on_moved(self, source: int, destination: int) -> None:
        if self._updating:
            return
        if not (0 <= source < len(self._keys) and 0 <= destination < len(self._keys)):
            return
        self._keys.insert(destination, self._keys.pop(source))
        self._gather_pins()
        self.tab_moved.emit(source, destination)
        self.layout_changed.emit()

    def _sync_empty(self) -> None:
        self._view.setCurrentWidget(self._tabs if self._keys else self._empty)

    def _document_rows(self) -> list[tuple[str, str]]:
        return [(key, self.title(key)) for key in self._keys]

    def _write_bar(self, key: str) -> None:
        if key not in self._keys:
            return
        item = self._items[key]
        self._bar.setTabData(
            self._keys.index(key),
            {"icon": item.icon, "modified": item.modified, "pinned": item.pinned},
        )
        self._bar.update()

    def _touch_recent(self, key: str) -> None:
        if not key:
            return
        self._recent = [item for item in self._recent if item != key]
        self._recent.insert(0, key)

    def _remember_closed(self, item: TabItem, widget: QWidget) -> None:
        self._closed.append(
            _ClosedDocument(
                item.key,
                item.title,
                widget,
                item.icon,
                item.path,
                item.modified,
                item.pinned,
            )
        )
        if len(self._closed) > 12:
            del self._closed[:-12]

    def _reorder(self, wanted: list[str]) -> None:
        self._updating = True
        try:
            for target, key in enumerate(wanted):
                source = self._keys.index(key)
                if source != target:
                    self._bar.moveTab(source, target)
                    self._keys.insert(target, self._keys.pop(source))
        finally:
            self._updating = False

    def _gather_pins(self) -> None:
        if not any(self.pinned(key) for key in self._keys):
            return
        wanted = [key for key in self._keys if self.pinned(key)]
        wanted.extend(key for key in self._keys if not self.pinned(key))
        if wanted != self._keys:
            self._reorder(wanted)

    def _refresh_overflow(self) -> None:
        needed = self._bar.count() > 0 and self._bar.sizeHint().width() > self._bar.width() + 8
        self._overflow.setVisible(needed)

    def _dispatch_document_key(self, event: QKeyEvent) -> bool:
        """处理文档区快捷键。没对上的按键留给输入框。"""

        mods = event.modifiers()
        ctrl = bool(mods & Qt.KeyboardModifier.ControlModifier)
        shift = bool(mods & Qt.KeyboardModifier.ShiftModifier)
        alt = bool(mods & Qt.KeyboardModifier.AltModifier)
        if not ctrl or alt:
            return False
        key = event.key()
        if key == Qt.Key.Key_W and not shift:
            self._close_current()
            return True
        if key in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab) and not shift:
            self._activate_previous()
            return True
        if key in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab) and shift:
            self._activate_older()
            return True
        if key == Qt.Key.Key_T and shift:
            self._reopen_last()
            return True
        if Qt.Key.Key_1 <= key <= Qt.Key.Key_9 and not shift:
            self._goto_number(key - Qt.Key.Key_1 + 1)
            return True
        return False

    def _reopen_last(self) -> None:
        self.reopen_last()

    def _close_current(self) -> None:
        key = self.current_key()
        if key and not self.pinned(key):
            self.close_tab(key)

    def _activate_previous(self) -> None:
        if len(self._recent) < 2:
            return
        self.set_current(self._recent[1])

    def _activate_older(self) -> None:
        if len(self._recent) < 2:
            return
        target = self._recent[-1]
        if target == self.current_key():
            return
        self.set_current(target)

    def _goto_number(self, number: int) -> None:
        if not self._keys:
            return
        index = len(self._keys) - 1 if number == 9 else number - 1
        if 0 <= index < len(self._keys):
            self.set_current(self._keys[index])

    def _document_menu(self, target: MenuTarget) -> list[MenuAction]:
        if not target.hit or not isinstance(target.key, str):
            return []
        key = target.key
        title = self.title(key)
        return [
            MenuAction("关闭", lambda: self.close_tab(key), icon="x", shortcut="Ctrl+W"),
            MenuAction("关闭其他标签", lambda: self.close_others(key), enabled=self.count() > 1),
            MenuAction("关闭右侧标签", lambda: self.close_right(key)),
            MenuAction("关闭全部标签", self.close_all, dangerous=True, enabled=self.count() > 0),
            MenuAction.line(),
            MenuAction("复制标签名称", lambda: _copy_text(title), enabled=bool(title)),
            MenuAction(
                "复制文件路径",
                lambda: _copy_text(self.path(key)),
                enabled=bool(self.path(key)),
            ),
            MenuAction.line(),
            MenuAction(
                "取消固定" if self.pinned(key) else "固定标签",
                lambda: self.set_pinned(key, not self.pinned(key)),
            ),
        ]

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if self._dispatch_document_key(event):
            event.accept()
            return
        super().keyPressEvent(event)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._refresh_overflow()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._refresh_overflow()


def _copy_text(text: str) -> None:
    clipboard = QGuiApplication.clipboard()
    if clipboard is not None:
        clipboard.setText(text)


def _widget_alive(widget: QWidget) -> bool:
    try:
        from shiboken6 import Shiboken
    except ImportError:
        return False
    return bool(Shiboken.isValid(widget))
