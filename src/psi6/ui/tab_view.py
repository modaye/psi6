"""多视图文档标签：可关闭、可重排，布局状态可序列化。

用 ``QTabWidget`` 承接已主题化的页签与关闭按钮，另用一层 ``QStackedWidget``
在所有文档都关掉之后显示空态。标签顺序与内容页由 ``key`` 关联，调用方持有
``QWidget``：关闭只是把控件交还，不会销毁。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from PySide6.QtCore import Property, QEvent, QObject, QPoint, QRectF, Qt, Signal
from PySide6.QtGui import QPaintEvent
from PySide6.QtWidgets import QStackedWidget, QTabBar, QTabWidget, QVBoxLayout, QWidget

from psi6.runtime.config import ConfigStore
from psi6.theme.paint import as_color, create_painter
from psi6.theme.runtime import token_color
from psi6.ui import motion
from psi6.ui.context_menu import MenuAction, MenuTarget, attach_context_menu
from psi6.ui.empty_state import EmptyState

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
            inset = 12.0
            target_x = rect.x() + inset
            target_w = max(12.0, rect.width() - inset * 2)
            self.setGeometry(0, self._bar.height() - 3, self._bar.width(), 3)
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
            painter.drawRoundedRect(QRectF(self._x, 0.5, self._w, 2), 1, 1)


class TabView(QWidget):
    """一组带关闭按钮的文档标签，顺序可拖动调整。

    状态只记 ``key`` 的顺序和当前项，不记控件本身：恢复布局时应用先用
    ``add_tab`` 把控件放回来，再 ``set_state`` / ``restore_state`` 对齐顺序。
    因此 ``set_state`` 里出现但没有对应控件的 key 会被忽略，当前多出来的
    标签则追加到末尾，不会因为文件里少写几个 key 就丢掉已打开的文档。
    """

    current_changed = Signal(str)
    tab_closed = Signal(str)
    tab_moved = Signal(int, int)
    layout_changed = Signal()

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
        self._state_file = state_file
        self._keys: list[str] = []
        self._widgets: dict[str, QWidget] = {}
        self._updating = False
        self._current_emitted: str | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        # 页签与内容区必须贴在一起：QTabWidget::pane 用 top: -1px 盖住页签底边。
        layout.setSpacing(0)

        self._tabs = QTabWidget()
        self._tabs.setObjectName("psi6TabViewTabs")
        self._tabs.setTabsClosable(closable)
        self._tabs.setMovable(movable)
        self._empty = EmptyState(empty_title, empty_hint)
        self._view = QStackedWidget()
        self._view.addWidget(self._tabs)
        self._view.addWidget(self._empty)
        layout.addWidget(self._view, stretch=1)

        self._tabs.currentChanged.connect(self._on_current)
        self._tabs.tabCloseRequested.connect(self._on_close_requested)
        self._tabs.tabBar().tabMoved.connect(self._on_moved)
        self._mark = _ActiveMark(self._tabs.tabBar())
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
        self._tabs.addTab(widget, title)
        self._sync_empty()
        self.layout_changed.emit()

    def close_tab(self, key: str) -> bool:
        """关闭并把控件交还调用方（``setParent(None)``，不 ``deleteLater``）。"""

        if key not in self._widgets:
            return False
        index = self._keys.index(key)
        widget = self._widgets.pop(key)
        self._updating = True
        try:
            self._keys.pop(index)
            self._tabs.removeTab(index)
            widget.hide()
            widget.setParent(None)
        finally:
            self._updating = False
        self._sync_empty()
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
            self._tabs.setTabText(self._keys.index(key), title)

    def current_key(self) -> str:
        """当前文档 key；一个都没打开时是空串。"""

        index = self._tabs.currentIndex()
        return self._keys[index] if 0 <= index < len(self._keys) else ""

    def set_current(self, key: str) -> None:
        if key in self._keys:
            self._tabs.setCurrentIndex(self._keys.index(key))

    def state(self) -> dict[str, Any]:
        """可 JSON 化的布局状态：标签顺序 + 当前项。"""

        return {"keys": list(self._keys), "current": self.current_key()}

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
        self._updating = True
        try:
            for target, key in enumerate(wanted):
                source = self._keys.index(key)
                if source != target:
                    self._tabs.tabBar().moveTab(source, target)
                    self._keys.insert(target, self._keys.pop(source))
        finally:
            self._updating = False
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
        if not self._updating:
            self._emit_current()

    def _emit_current(self) -> None:
        # removeTab / set_state 之后 Qt 可能不发 currentChanged，这里补发；
        # 去重避免同一次操作里把同一个 key 播两遍。
        key = self.current_key()
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
        self.tab_moved.emit(source, destination)
        self.layout_changed.emit()

    def _sync_empty(self) -> None:
        self._view.setCurrentWidget(self._tabs if self._keys else self._empty)
