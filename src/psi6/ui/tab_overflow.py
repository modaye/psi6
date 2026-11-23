"""放不下的文档标签：右侧按钮打开可搜索列表，按最近使用排序。"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtWidgets import (
    QFrame,
    QListWidget,
    QListWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from psi6.icons.render import icon_for
from psi6.ui.icon import token_color
from psi6.ui.search_field import SearchField


def ordered_documents(
    rows: Sequence[tuple[str, str]],
    recent: Sequence[str],
    query: str,
) -> list[tuple[str, str]]:
    """``rows`` 是文档顺序的 ``(key, title)``。查询为空时按最近使用，其余保持原顺序。"""

    rank = {key: index for index, key in enumerate(recent)}
    ordered = sorted(rows, key=lambda row: (rank.get(row[0], len(recent)), _index(rows, row[0])))
    needle = query.casefold().strip()
    if not needle:
        return list(ordered)
    return [row for row in ordered if needle in row[1].casefold() or needle in row[0].casefold()]


def _index(rows: Sequence[tuple[str, str]], key: str) -> int:
    for index, row in enumerate(rows):
        if row[0] == key:
            return index
    return len(rows)


class TabOverflowButton(QToolButton):
    """标签栏右上角的文档列表。放得下全部标签时隐藏。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("psi6TabOverflow")
        self.setToolTip("打开的文档")
        self.setAutoRaise(True)
        self._rows: Callable[[], list[tuple[str, str]]] = lambda: []
        self._recent: Callable[[], list[str]] = lambda: []
        self._icons: Callable[[str], str] = lambda _key: ""
        self._activate: Callable[[str], None] = lambda _key: None
        self.clicked.connect(self._open)
        self._sync_icon()

    def bind(
        self,
        *,
        rows: Callable[[], list[tuple[str, str]]],
        recent: Callable[[], list[str]],
        icon_name: Callable[[str], str],
        activate: Callable[[str], None],
    ) -> None:
        """列表内容由 ``TabView`` 提供，按钮不保存文档。"""

        self._rows = rows
        self._recent = recent
        self._icons = icon_name
        self._activate = activate

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() in (QEvent.Type.PaletteChange, QEvent.Type.StyleChange):
            self._sync_icon()

    def _sync_icon(self) -> None:
        from PySide6.QtGui import QIcon

        try:
            self.setIcon(icon_for("chevron-down", color=token_color(self), size=16))
        except (OSError, ValueError):
            self.setIcon(QIcon())

    def _open(self) -> None:
        popup = _TabOverflowPopup(
            self._rows(),
            self._recent(),
            self._icons,
            self._activate,
            self,
        )
        popup.popup_under(self)


class _TabOverflowPopup(QFrame):
    """点外面就关掉的文档列表。"""

    def __init__(
        self,
        rows: list[tuple[str, str]],
        recent: list[str],
        icon_name: Callable[[str], str],
        activate: Callable[[str], None],
        parent: QWidget,
    ) -> None:
        super().__init__(parent, Qt.WindowType.Popup)
        self.setObjectName("psi6TabOverflowPopup")
        self._rows = rows
        self._recent = recent
        self._icons = icon_name
        self._activate = activate
        self.setFixedWidth(280)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        self._search = SearchField(placeholder="搜索文档")
        self._list = QListWidget()
        self._list.setObjectName("psi6TabOverflowList")
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(self._search)
        layout.addWidget(self._list)
        self._search.query_changed.connect(self._refill)
        self._list.itemClicked.connect(self._choose)
        self._refill("")

    def popup_under(self, anchor: QWidget) -> None:
        self.adjustSize()
        self.move(anchor.mapToGlobal(QPoint(anchor.width() - self.width(), anchor.height() + 4)))
        self.show()
        self._search.setFocus()

    def _refill(self, query: str) -> None:
        self._list.clear()
        for key, title in ordered_documents(self._rows, self._recent, query):
            item = QListWidgetItem(title or key)
            item.setData(Qt.ItemDataRole.UserRole, key)
            name = self._icons(key)
            if name:
                item.setIcon(icon_for(name, color=token_color(self), size=16))
            self._list.addItem(item)

    def _choose(self, item: QListWidgetItem) -> None:
        key = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(key, str) and key:
            self._activate(key)
        self.close()
