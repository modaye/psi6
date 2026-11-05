"""撤销栈：push 立刻执行，Ctrl+Z 不抢走输入框自己的撤销。"""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import QLineEdit, QVBoxLayout, QWidget
from pytestqt.qtbot import QtBot

from psi6.ui.history import EditHistory
from psi6.ui.shortcuts import ShortcutBook


def test_push_undo_and_redo() -> None:
    history = EditHistory()
    value = {"n": 0}

    def apply() -> None:
        value["n"] += 1

    def revert() -> None:
        value["n"] -= 1

    history.push("加一", apply=apply, revert=revert)
    assert value["n"] == 1
    assert history.can_undo()
    history.undo()
    assert value["n"] == 0
    assert history.can_redo()
    history.redo()
    assert value["n"] == 1
    history.clear()
    assert not history.can_undo()


def test_install_undo_yields_to_a_line_edit(qtbot: QtBot) -> None:
    window = QWidget()
    layout = QVBoxLayout(window)
    edit = QLineEdit()
    layout.addWidget(edit)
    qtbot.addWidget(window)
    window.show()
    steps: list[str] = []
    history = EditHistory()
    history.push("标记", apply=lambda: steps.append("do"), revert=lambda: steps.append("undo"))
    book = history.install(window)
    assert isinstance(book, ShortcutBook)
    override = QKeyEvent(
        QEvent.Type.ShortcutOverride,
        Qt.Key.Key_Z,
        Qt.KeyboardModifier.ControlModifier,
    )
    assert edit.event(override)
    assert override.isAccepted()
    matches = [
        item
        for item in window.findChildren(QShortcut)
        if item.isEnabled()
        and item.key().toString(QKeySequence.SequenceFormat.PortableText) == "Ctrl+Z"
    ]
    assert len(matches) == 1
    matches[0].activated.emit()
    assert steps == ["do", "undo"]
    assert history.can_redo()
