"""命令面板：检索动作。要让条目上的快捷键真正生效，调用 ``install``。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from psi6.ui.icon import Icon
from psi6.ui.shortcuts import ShortcutBook


@dataclass(frozen=True)
class Command:
    """一条可检索命令。"""

    command_id: str
    title: str
    hint: str = ""
    icon: str = "search"
    shortcut: str = ""


class CommandPalette(QDialog):
    """浮在当前窗口上的命令检索。``activated`` 给出 ``command_id``。"""

    activated = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("psi6CommandPalette")
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setModal(True)
        self.resize(460, 320)
        self._commands: tuple[Command, ...] = ()
        self._book: ShortcutBook | None = None
        self._owns_book = False
        self._bound_ids: list[str] = []
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)
        self._search = QLineEdit()
        self._search.setPlaceholderText("搜索命令…")
        self._search.textChanged.connect(self._rebuild)
        self._search.returnPressed.connect(self._accept_current)
        root.addWidget(self._search)
        self._list = QListWidget()
        self._list.setObjectName("psi6CommandList")
        self._list.itemActivated.connect(self._on_item)
        self._list.itemClicked.connect(self._on_item)
        root.addWidget(self._list, stretch=1)

    def set_commands(self, commands: list[Command] | tuple[Command, ...]) -> None:
        self._commands = tuple(commands)
        self._rebuild(self._search.text())
        self._rebind()

    def install(self, host: QWidget, book: ShortcutBook | None = None) -> ShortcutBook:
        """把带 ``shortcut`` 的命令登记到 ``host`` 所在窗口。按键发出 ``activated``。

        撤销和其它命令应与面板共用一本 ``ShortcutBook``，同一序列不会登记两次。
        菜单里的快捷键文字仍然只是提示。
        """

        self._release_bindings()
        if book is not None:
            if self._owns_book and self._book is not None and self._book is not book:
                self._book.clear()
            self._book = book
            self._owns_book = False
        elif self._book is None or not self._owns_book or self._book.host is not host:
            if self._owns_book and self._book is not None:
                self._book.clear()
            self._book = ShortcutBook(host)
            self._owns_book = True
        self._rebind()
        return self._book

    def _release_bindings(self) -> None:
        book = self._book
        if book is None:
            self._bound_ids = []
            return
        for command_id in self._bound_ids:
            book.unbind(command_id)
        self._bound_ids = []

    def _rebind(self) -> None:
        book = self._book
        if book is None:
            return
        self._release_bindings()
        bound: list[str] = []
        for command in self._commands:
            if not command.shortcut:
                continue
            command_id = command.command_id
            book.bind(command_id, command.shortcut, self._activate(command_id))
            bound.append(command_id)
        self._bound_ids = bound

    def _activate(self, command_id: str) -> Callable[[], None]:
        """按键或回车都发出同一条命令。闭包按 id 绑定，避免循环里串掉。"""

        def fire() -> None:
            self.activated.emit(command_id)

        return fire

    def popup(self, anchor: QWidget | None = None) -> None:
        """相对锚点窗口居中弹出。"""

        host = anchor or self.parentWidget()
        self._search.clear()
        self._rebuild("")
        if host is not None:
            geo = host.frameGeometry()
            self.move(
                geo.center().x() - self.width() // 2,
                geo.top() + 72,
            )
        self.show()
        self._search.setFocus(Qt.FocusReason.PopupFocusReason)

    def _rebuild(self, query: str = "") -> None:
        needle = query.strip().casefold()
        self._list.clear()
        for command in self._commands:
            haystack = f"{command.title} {command.hint} {command.shortcut}".casefold()
            if needle and needle not in haystack:
                continue
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, command.command_id)
            widget = _CommandRow(command)
            item.setSizeHint(widget.sizeHint())
            self._list.addItem(item)
            self._list.setItemWidget(item, widget)
        if self._list.count():
            self._list.setCurrentRow(0)

    def _on_item(self, item: QListWidgetItem) -> None:
        command_id = item.data(Qt.ItemDataRole.UserRole)
        if command_id:
            self.activated.emit(str(command_id))
            self.hide()

    def _accept_current(self) -> None:
        item = self._list.currentItem()
        if item is not None:
            self._on_item(item)


class _CommandRow(QFrame):
    def __init__(self, command: Command, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("psi6CommandRow")
        row = QHBoxLayout(self)
        row.setContentsMargins(8, 6, 8, 6)
        row.setSpacing(8)
        row.addWidget(Icon(command.icon))
        text = QVBoxLayout()
        text.setContentsMargins(0, 0, 0, 0)
        text.setSpacing(0)
        title = QLabel(command.title)
        text.addWidget(title)
        if command.hint:
            hint = QLabel(command.hint)
            hint.setObjectName("psi6Hint")
            text.addWidget(hint)
        row.addLayout(text, stretch=1)
        if command.shortcut:
            from psi6.ui.kbd import KbdHint

            row.addWidget(KbdHint(command.shortcut))
