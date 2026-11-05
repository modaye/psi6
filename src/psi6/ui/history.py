"""编辑撤销栈。一步由「怎么做」和「怎么撤回」两个回调组成。

输入框自己的逐字撤销仍然留给控件：聚焦在可编辑文本上时，Ctrl+Z 不会被这本栈抢走。
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QUndoCommand, QUndoStack
from PySide6.QtWidgets import QWidget

from psi6.ui.shortcuts import ShortcutBook

__all__ = ["EditHistory"]


class _Step(QUndoCommand):
    """一次可撤回的修改。``redo`` 在 ``push`` 时就会立刻执行。"""

    def __init__(
        self,
        label: str,
        apply: Callable[[], None],
        revert: Callable[[], None],
    ) -> None:
        super().__init__(label)
        self._apply = apply
        self._revert = revert

    def redo(self) -> None:
        self._apply()

    def undo(self) -> None:
        self._revert()


class EditHistory(QObject):
    """窗口级撤销 / 重做。

    ``push`` 会立刻调用 ``apply``。撤销调用 ``revert``，重做再调用 ``apply``。
    ``install`` 把 Ctrl+Z、Ctrl+Y、Ctrl+Shift+Z 登记到窗口；和命令面板共用一本
    ``ShortcutBook`` 时，同一序列不会登记两次。
    """

    changed = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._stack = QUndoStack(self)
        self._stack.indexChanged.connect(self._on_index_changed)
        self._book: ShortcutBook | None = None

    @Slot(int)
    def _on_index_changed(self, _index: int) -> None:
        self.changed.emit()

    def push(
        self,
        label: str,
        *,
        apply: Callable[[], None],
        revert: Callable[[], None],
    ) -> None:
        """记录一步并立刻执行 ``apply``。"""

        text = str(label).strip()
        if not text:
            raise ValueError("撤销说明不能为空")
        if apply is None or revert is None:
            raise ValueError("apply 和 revert 都不能为空")
        self._stack.push(_Step(text, apply, revert))

    def undo(self) -> None:
        """撤回最近一步。没有可撤回的修改时什么也不做。"""

        self._stack.undo()

    def redo(self) -> None:
        """重做刚才撤回的一步。"""

        self._stack.redo()

    def can_undo(self) -> bool:
        return self._stack.canUndo()

    def can_redo(self) -> bool:
        return self._stack.canRedo()

    def clear(self) -> None:
        """丢掉全部步骤。换了一批数据之后应调用，避免撤回到已经不存在的内容。"""

        self._stack.clear()

    def install(self, host: QWidget, book: ShortcutBook | None = None) -> ShortcutBook:
        """把撤销和重做登记到 ``host`` 所在窗口，返回用到的快捷键表。"""

        if book is None:
            book = self._book if self._book is not None and self._book.host is host else None
        if book is None:
            book = ShortcutBook(host)
        self._book = book
        book.bind("edit.undo", "Ctrl+Z", self.undo)
        book.bind("edit.redo", "Ctrl+Y", self.redo)
        book.bind("edit.redo-alt", "Ctrl+Shift+Z", self.redo)
        return book
