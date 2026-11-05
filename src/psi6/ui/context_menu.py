"""右键上下文菜单：图标、快捷键提示、危险项、勾选 / 单选态，并自动挂到控件上。

``QMenu`` 的样式已经在全局 QSS 里，这一层补的是**语义**和**挂载方式**：

* 用 ``MenuAction`` 描述一项，构造时才知道能不能点、要不要打勾、是不是危险动作。
* ``ContextMenu`` 把描述渲染成 ``QMenu``，图标按当前 token 着色，换肤时自动重画。
* ``attach_context_menu()`` 把菜单接到 ``DataTable`` / ``TreeView`` / ``TabView`` 这类
  容器上：右键命中的是哪一行、哪个节点、哪个页签，回调里就能拿到。

菜单只在右键时创建，平时不占内存；行的数据是**命中时的快照**，别把它存下来当状态用。
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from PySide6.QtCore import QEvent, QObject, QPoint, Qt
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtWidgets import QMenu, QWidget

from psi6.icons.render import device_ratio, icon_for
from psi6.ui.icon import token_color

__all__ = [
    "MenuAction",
    "MenuTarget",
    "attach_context_menu",
    "build_menu",
    "menu_for",
]

# 菜单是原生弹出窗口，不继承控件的调色板；主题变化时要自己重画图标。
_THEME_EVENTS = frozenset({QEvent.Type.PaletteChange, QEvent.Type.ScreenChangeInternal})


@dataclass(frozen=True)
class MenuAction:
    """菜单里的一项。

    ``separator=True`` 时只画分隔线，其余字段忽略。``checked`` 传 ``None`` 表示不显示
    勾选；``group`` 相同的几项自动互斥（单选），并自动补一条分隔线。

    ``callback`` 的返回值会被忽略，写成返回列表的推导式（如批量关闭多个页签）也合法。
    """

    label: str = ""
    callback: Callable[[], Any] | None = None
    icon: str = ""
    shortcut: str = ""
    enabled: bool = True
    dangerous: bool = False
    checked: bool | None = None
    group: str = ""
    separator: bool = False

    @classmethod
    def line(cls) -> MenuAction:
        """一条分隔线。"""

        return cls(separator=True)

    @property
    def checkable(self) -> bool:
        return self.checked is not None


@dataclass
class MenuTarget:
    """右键命中目标，回调和菜单构造都能读。

    ``kind`` 是容器名（``table`` / ``tree`` / ``tabs``），``key`` 是这一行的稳定标识
    （表格 / 树的原始行索引或节点 id、页签 key），``data`` 是命中时的行 / 节点快照。
    """

    kind: str
    key: Any = None
    data: Any = None
    position: QPoint = field(default_factory=QPoint)

    @property
    def hit(self) -> bool:
        """右键是否落在真实条目上（空白处为 ``False``）。"""

        return self.key is not None


@runtime_checkable
class _MenuHost(Protocol):
    """能被 ``attach_context_menu`` 挂载的容器。"""

    def _context_menu_source(self) -> QWidget: ...


class _MenuIconRefresher(QObject):
    """菜单图标跟随主题重画。菜单是独立窗口，收不到宿主的 PaletteChange。"""

    def __init__(self, menu: QMenu) -> None:
        super().__init__(menu)
        self._menu = menu

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # type: ignore[override]
        if watched is self._menu and event.type() in _THEME_EVENTS:
            _paint_icons(self._menu)
        return False


def _action_icon(name: str, host: QWidget, *, dangerous: bool) -> Any:
    color = token_color(host, tone="error" if dangerous else "neutral")
    return icon_for(name, color=color, size=16, ratio=device_ratio(host))


def _paint_icons(menu: QMenu) -> None:
    """按当前 token 重画菜单里所有带图标的项。"""

    for action in menu.actions():
        name = action.property("psi6Icon")
        if not isinstance(name, str) or not name:
            continue
        dangerous = bool(action.property("psi6Dangerous"))
        host = menu.parentWidget()
        if host is None:
            continue
        action.setIcon(_action_icon(name, host, dangerous=dangerous))


def build_menu(
    actions: Iterable[MenuAction],
    *,
    host: QWidget,
    title: str = "",
) -> QMenu:
    """把描述渲染成 ``QMenu``。

    ``host`` 用来取当前主题色画图标，并作为菜单的父对象（菜单不能脱离控件单独存在，
    否则换肤后图标颜色会停在旧值）。空动作序列返回一个只有标题的空菜单，调用方自己
    决定要不要弹出。
    """

    menu = QMenu(host)
    menu.setAccessibleName(title or "上下文菜单")
    if title:
        menu.setTitle(title)
    group: QActionGroup | None = None
    group_name = ""
    previous_separator = True  # 开头不补分隔线
    has_group = False

    for spec in actions:
        if spec.separator:
            if not previous_separator:
                menu.addSeparator()
                previous_separator = True
            continue

        # 切换单选组时补一条分隔线，视觉上把「选哪个」和「做什么」分开。
        if spec.group and spec.group != group_name:
            if not previous_separator:
                menu.addSeparator()
                previous_separator = True
            group = QActionGroup(menu)
            group.setExclusive(True)
            group_name = spec.group
            has_group = True
        elif not spec.group and group_name:
            group = None
            group_name = ""

        action = QAction(spec.label, menu)
        action.setEnabled(spec.enabled)
        if spec.shortcut:
            # 只做提示，不注册真实快捷键：同一个动作可能出现在多个菜单里。
            action.setShortcut(QKeySequence(spec.shortcut))
            action.setShortcutVisibleInContextMenu(True)
        if spec.icon:
            action.setIcon(_action_icon(spec.icon, host, dangerous=spec.dangerous))
            action.setProperty("psi6Icon", spec.icon)
            action.setProperty("psi6Dangerous", spec.dangerous)
        if spec.checkable:
            action.setCheckable(True)
            action.setChecked(bool(spec.checked))
            if group is not None:
                group.addAction(action)
        if spec.callback is not None:
            # 用宿主当接收者：菜单关掉就回收，不会因为回调持有菜单而泄漏。
            action.triggered.connect(lambda _checked=False, cb=spec.callback: cb())
        menu.addAction(action)
        previous_separator = False

    if menu.actions() or title:
        # 末尾的分隔线没有视觉意义，去掉；开头在上面已经跳过了。
        while menu.actions() and menu.actions()[-1].isSeparator():
            menu.removeAction(menu.actions()[-1])
        refresher = _MenuIconRefresher(menu)
        menu.installEventFilter(refresher)
        menu.setProperty("psi6HasMenuGroup", has_group)
    return menu


def menu_for(
    target: MenuTarget,
    builder: Callable[[MenuTarget], Sequence[MenuAction] | None],
    *,
    host: QWidget,
) -> QMenu | None:
    """按命中目标问调用方要菜单；返回 ``None`` 表示这次不弹。"""

    specs = builder(target)
    if not specs:
        return None
    return build_menu(specs, host=host)


def attach_context_menu(
    widget: _MenuHost,
    builder: Callable[[MenuTarget], Sequence[MenuAction] | None],
    *,
    policy: Qt.ContextMenuPolicy = Qt.ContextMenuPolicy.CustomContextMenu,
    source: QWidget | None = None,
) -> QWidget:
    """给容器挂右键菜单，返回真正安装策略的那个内部视图。

    ``builder`` 收到命中目标、返回动作序列；返回空或 ``None`` 就不弹菜单。容器只要
    实现 ``_context_menu_source()`` 给出内部视图，以及 ``_context_menu_target(pos)``
    给出命中目标。

    ``source`` 可以指定挂到别的视图上（例如表格的**列头**），此时命中目标由容器
    的 ``_column_menu_target`` 给出；不给就用 ``_context_menu_target``。
    """

    view = source if source is not None else widget._context_menu_source()
    view.setContextMenuPolicy(policy)
    view.setProperty("psi6ContextMenu", True)

    handler = _ContextMenuHandler(view, builder, widget, use_column_target=source is not None)
    view.installEventFilter(handler)
    view._psi6_menu_handler = handler  # type: ignore[attr-defined]
    return view


class _ContextMenuHandler(QObject):
    """把视图的右键事件转成 ``MenuTarget`` 再交给调用方。"""

    def __init__(
        self,
        source: QWidget,
        builder: Callable[[MenuTarget], Sequence[MenuAction] | None],
        container: QWidget,
        *,
        use_column_target: bool = False,
    ) -> None:
        super().__init__(source)
        self._source = source
        self._builder = builder
        self._container = container
        self._use_column_target = use_column_target

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # type: ignore[override]
        if watched is self._source and event.type() == QEvent.Type.ContextMenu:
            return self._popup(event)
        return False

    def _popup(self, event: QEvent) -> bool:
        owner = self._source
        container = self._container
        attr = "_column_menu_target" if self._use_column_target else "_context_menu_target"
        target_fn = getattr(container, attr, None)
        if not callable(target_fn):
            return False
        pos = event.pos()  # type: ignore[attr-defined]
        target = target_fn(pos)
        if target is None:
            return True
        menu = menu_for(target, self._builder, host=owner)
        if menu is None:
            return True
        menu.exec(owner.mapToGlobal(pos))
        menu.deleteLater()
        return True
