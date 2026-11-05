"""现代桌面工作区：工具栏、面包屑和可拖拽分栏。

侧栏换页仍用 ``AppShell``。本控件负责一页内部的命令和左右栏；栏可以显隐，
拖动后的宽度与显隐状态能导出并持久化，但不提供浮动窗口或自由停靠面板。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QSplitter,
    QSplitterHandle,
    QVBoxLayout,
    QWidget,
)

from psi6.runtime.config import ConfigStore
from psi6.theme.runtime import token_int

Pane = str

_PLACES = ("left", "center", "right")
_DEFAULT_STATE_FILE = "layout.json"


class _PaneSplitter(QSplitter):
    """分栏。布局算完后才按权重收回宽度，避免被等分盖掉。"""

    def __init__(self, owner: Workspace) -> None:
        super().__init__(Qt.Orientation.Horizontal, owner)
        self._owner = owner

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._owner._after_splitter_resize()


class ToolBar(QWidget):
    """一页的命令条。主要动作在左，次要动作在右。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("psi6ToolBar")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self._primary = QHBoxLayout()
        self._primary.setSpacing(8)
        self._secondary = QHBoxLayout()
        self._secondary.setSpacing(8)
        layout.addLayout(self._primary)
        layout.addStretch(1)
        layout.addLayout(self._secondary)
        self.apply_metrics()

    def apply_metrics(self) -> None:
        """间距跟随当前主题，紧凑密度会收紧命令条。"""

        gap = token_int("space_sm", 8)
        layout = self.layout()
        if layout is not None:
            layout.setSpacing(gap)
        self._primary.setSpacing(gap)
        self._secondary.setSpacing(gap)

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if event.type() in {QEvent.Type.PaletteChange, QEvent.Type.StyleChange}:
            self.apply_metrics()

    def add_primary(self, widget: QWidget) -> None:
        """放开始、保存这类主动作。"""

        self._primary.addWidget(widget)

    def add_secondary(self, widget: QWidget) -> None:
        """放取消、筛选这类次要动作。"""

        self._secondary.addWidget(widget)


class Breadcrumb(QWidget):
    """只显示位置，不负责切换页面。最后一段是当前位置。"""

    def __init__(self, crumbs: Sequence[str] | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("psi6BreadcrumbBar")
        self._crumbs: list[str] = []
        self._row = QHBoxLayout(self)
        self._row.setContentsMargins(0, 0, 0, 0)
        self.apply_metrics()
        if crumbs:
            self.set_crumbs(crumbs)

    def apply_metrics(self) -> None:
        """分隔间距跟随当前主题。"""

        layout = self.layout()
        if layout is not None:
            layout.setSpacing(token_int("space_sm", 8))

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if event.type() in {QEvent.Type.PaletteChange, QEvent.Type.StyleChange}:
            self.apply_metrics()

    def set_crumbs(self, crumbs: Sequence[str]) -> None:
        """用新的路径替换当前显示。"""

        self._crumbs = [str(item) for item in crumbs]
        while self._row.count():
            item = self._row.takeAt(0)
            if item is None:
                break
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for index, text in enumerate(self._crumbs):
            if index:
                separator = QLabel("/")
                separator.setObjectName("psi6Breadcrumb")
                self._row.addWidget(separator)
            label = QLabel(text)
            current = index == len(self._crumbs) - 1
            label.setObjectName("psi6BreadcrumbCurrent" if current else "psi6Breadcrumb")
            self._row.addWidget(label)
        self._row.addStretch(1)

    def crumbs(self) -> list[str]:
        """当前路径。"""

        return list(self._crumbs)


class Workspace(QWidget):
    """工具栏和面包屑在上，可拖拽的左、中、右栏在下。

    省略的栏不占位；栏可以显隐，拖动后的宽度按栏名记在控件上，不写入窗口几何。
    ``state()`` / ``set_state()`` 把显隐与宽度导出成可 JSON 化的字典，
    ``save_state()`` / ``restore_state()`` 走应用的 ``ConfigStore``。
    """

    layout_changed = Signal()

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        state_file: str = _DEFAULT_STATE_FILE,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("psi6Workspace")
        self._state_file = state_file
        self.toolbar = ToolBar()
        self.breadcrumb = Breadcrumb()
        self._panes: dict[str, QWidget] = {}
        self._stretch: dict[str, int] = {}
        self._hidden: set[str] = set()
        # 按 place 记宽度：隐藏一栏后其余栏的宽度不会因为下标错位而丢失。
        self._pane_sizes: dict[str, int] = {}
        self._dragged = False
        self._fitting = False
        self._splitter = _PaneSplitter(self)
        self._splitter.setObjectName("psi6WorkspaceSplit")
        self._splitter.setChildrenCollapsible(False)
        layout = QVBoxLayout(self)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.breadcrumb)
        layout.addWidget(self._splitter, stretch=1)
        self.apply_metrics()

    def apply_metrics(self) -> None:
        """页边距和分隔条跟随当前主题的间距。切到紧凑密度时一起变窄。"""

        margin_x = token_int("space_lg", 16)
        margin_y = token_int("space_md", 12)
        gap = token_int("space_sm", 8)
        layout = self.layout()
        if layout is not None:
            layout.setContentsMargins(margin_x, margin_y, margin_x, margin_y)
            layout.setSpacing(gap)
        self._splitter.setHandleWidth(max(6, gap))
        self.toolbar.apply_metrics()
        self.breadcrumb.apply_metrics()

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if event.type() in {QEvent.Type.PaletteChange, QEvent.Type.StyleChange}:
            self.apply_metrics()

    def set_crumbs(self, crumbs: Sequence[str]) -> None:
        """设置面包屑。"""

        self.breadcrumb.set_crumbs(crumbs)

    def set_pane(self, place: Pane, widget: QWidget) -> None:
        """放入 ``left``、``center`` 或 ``right``。再次调用会替换该栏。"""

        if place not in _PLACES:
            raise ValueError(f"未知分栏: {place}")
        self._panes[place] = widget
        self._rebuild()

    def set_stretch(self, place: Pane, factor: int) -> None:
        """用户还没拖过时，按权重分配宽度。主区通常大于侧栏。"""

        if place not in _PLACES:
            raise ValueError(f"未知分栏: {place}")
        if factor < 1:
            raise ValueError("分栏权重至少为 1")
        self._stretch[place] = factor
        self._apply_stretch()

    def sizes(self) -> list[int]:
        """当前各栏宽度，顺序与可见栏一致。"""

        return list(self._splitter.sizes())

    def visible_panes(self) -> list[str]:
        """当前可见的栏，顺序与可见栏一致。"""

        return list(self._visible_places())

    def is_pane_visible(self, place: Pane) -> bool:
        return place in self._panes and place not in self._hidden

    def set_pane_visible(self, place: Pane, visible: bool) -> None:
        """显隐一栏。隐藏只是从分栏里摘下来，控件本身保留，随时可以再显示。"""

        if place not in _PLACES:
            raise ValueError(f"未知分栏: {place}")
        if visible:
            changed = place in self._hidden
            self._hidden.discard(place)
        else:
            changed = place not in self._hidden
            self._hidden.add(place)
        if changed:
            self._rebuild()
            self.layout_changed.emit()

    def state(self) -> dict[str, Any]:
        """显隐与各栏宽度。宽度按栏名记，面板增删后依然对齐得上。"""

        places = self._visible_places()
        sizes = self._splitter.sizes()
        size_map = {
            place: int(size) for place, size in zip(places, sizes, strict=False) if size > 0
        }
        return {
            "hidden": sorted(self._hidden),
            "sizes": size_map,
            "dragged": bool(self._dragged),
        }

    def set_state(self, state: Mapping[str, Any]) -> None:
        """恢复显隐与宽度；缺失、多余或类型不对的字段一律安全跳过。"""

        hidden = state.get("hidden")
        if isinstance(hidden, (list, tuple)):
            self._hidden = {str(place) for place in hidden if str(place) in _PLACES}
        sizes = state.get("sizes")
        pane_sizes: dict[str, int] = {}
        if isinstance(sizes, Mapping):
            for place, value in sizes.items():
                key = str(place)
                if (
                    key in _PLACES
                    and isinstance(value, (int, float))
                    and not isinstance(value, bool)
                    and value > 0
                ):
                    pane_sizes[key] = int(value)
        self._pane_sizes = pane_sizes
        self._dragged = bool(state.get("dragged")) and bool(pane_sizes)
        self._rebuild()
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

    def _visible_places(self) -> list[str]:
        return [place for place in _PLACES if place in self._panes and place not in self._hidden]

    def _rebuild(self) -> None:
        splitter = self._splitter
        splitter.setUpdatesEnabled(False)
        try:
            while splitter.count():
                widget = splitter.widget(0)
                if widget is None:
                    break
                widget.hide()
                # 解除父子关系：被替换掉或被隐藏的栏不再作为隐藏子控件常驻。
                widget.setParent(None)
            for place in self._visible_places():
                widget = self._panes.get(place)
                if widget is None:
                    continue
                widget.setMinimumWidth(0)
                policy = widget.sizePolicy()
                policy.setHorizontalPolicy(QSizePolicy.Policy.Ignored)
                widget.setSizePolicy(policy)
                # 先挂回分栏再显示。无父对象时 show() 会先开出一个独立窗口。
                splitter.addWidget(widget)
                widget.show()
            for index in range(1, splitter.count()):
                handle = splitter.handle(index)
                handle.removeEventFilter(self)
                handle.installEventFilter(self)
        finally:
            splitter.setUpdatesEnabled(True)
        self._apply_stretch()
        # show() 会先留下一帧未稳定的栏宽，等这次布局请求处理完再读才是最终宽度。
        app = QApplication.instance()
        if app is not None:
            app.sendPostedEvents(None, QEvent.Type.LayoutRequest)

    def eventFilter(self, watched, event: QEvent) -> bool:
        if isinstance(watched, QSplitterHandle) and event.type() == QEvent.Type.MouseButtonRelease:
            sizes = self._splitter.sizes()
            if any(size > 0 for size in sizes):
                places = self._visible_places()
                if len(places) == len(sizes):
                    # 只覆盖可见栏：隐藏中的栏仍留着上次的宽度，再次显示时能按名字取回。
                    self._pane_sizes.update(
                        {
                            place: size
                            for place, size in zip(places, sizes, strict=False)
                            if size > 0
                        }
                    )
                self._dragged = True
                self.layout_changed.emit()
        return super().eventFilter(watched, event)

    def _apply_stretch(self) -> None:
        count = self._splitter.count()
        places = self._visible_places()
        if count == 0 or not places:
            return
        # 拖过之后按栏名恢复，而不是按位置：隐藏一栏也不会让宽度串行错位。
        if self._dragged and all(place in self._pane_sizes for place in places):
            self._fit([self._pane_sizes[place] for place in places])
            return
        for index, place in enumerate(places):
            self._splitter.setStretchFactor(index, self._stretch.get(place, 1))
        width = self._splitter.width()
        if width <= 0:
            return
        total = sum(self._stretch.get(place, 1) for place in places)
        handle = self._splitter.handleWidth() * max(0, count - 1)
        usable = max(width - handle, count)
        self._fit([max(1, usable * self._stretch.get(place, 1) // total) for place in places])

    def _fit(self, sizes: list[int]) -> None:
        self._fitting = True
        try:
            self._splitter.setSizes(sizes)
        finally:
            self._fitting = False

    def _after_splitter_resize(self) -> None:
        if self._dragged or self._fitting:
            return
        self._apply_stretch()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._after_splitter_resize()
