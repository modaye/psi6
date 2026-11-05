"""窗口级快捷键：每个序列只登记一次，按键会调用回调。"""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QWidget
from pytestqt.qtbot import QtBot

from psi6.ui.command_palette import Command, CommandPalette
from psi6.ui.shortcuts import ShortcutBook


def _fire(host: QWidget, sequence: str) -> None:
    """触发已经登记的 ``QShortcut``。

    offscreen 平台送不进真实按键，这里直接核对键序、作用域和回调是否接上。
    """

    key = QKeySequence(sequence).toString(QKeySequence.SequenceFormat.PortableText)
    matches = [
        item
        for item in host.findChildren(QShortcut)
        if item.isEnabled()
        and item.key().toString(QKeySequence.SequenceFormat.PortableText) == key
        and item.context() == Qt.ShortcutContext.WindowShortcut
    ]
    assert len(matches) == 1
    matches[0].activated.emit()


def test_binding_fires_and_replaces_the_same_command(qtbot: QtBot) -> None:
    window = QWidget()
    qtbot.addWidget(window)
    fired: list[str] = []
    book = ShortcutBook(window)
    book.bind("open", "Ctrl+K", lambda: fired.append("first"))
    book.bind("open", "Ctrl+K", lambda: fired.append("second"))
    _fire(window, "Ctrl+K")
    assert fired == ["second"]
    assert book.sequence_for("open") == "Ctrl+K"


def test_duplicate_sequence_is_rejected(qtbot: QtBot) -> None:
    window = QWidget()
    qtbot.addWidget(window)
    book = ShortcutBook(window)
    book.bind("open", "Ctrl+K", lambda: None)
    with pytest.raises(ValueError, match="已经绑在"):
        book.bind("close", "Ctrl+K", lambda: None)
    book.unbind("open")
    assert book.sequence_for("open") == ""
    book.bind("close", "Ctrl+K", lambda: None)
    assert book.sequence_for("close") == "Ctrl+K"


def test_empty_sequence_and_unknown_keys(qtbot: QtBot) -> None:
    window = QWidget()
    qtbot.addWidget(window)
    book = ShortcutBook(window)
    book.bind("open", "Ctrl+K", lambda: None)
    book.bind("open", "", lambda: None)
    assert book.sequence_for("open") == ""
    with pytest.raises(ValueError, match="无法识别"):
        book.bind("open", "not-a-key", lambda: None)


def test_command_palette_install_emits_the_command(qtbot: QtBot) -> None:
    window = QWidget()
    qtbot.addWidget(window)
    window.show()
    window.setFocus()
    palette = CommandPalette(window)
    qtbot.addWidget(palette)
    fired: list[str] = []
    palette.activated.connect(fired.append)
    palette.set_commands([Command("find", "查找", shortcut="Ctrl+F")])
    palette.install(window)
    _fire(window, "Ctrl+F")
    assert fired == ["find"]


def test_palette_shares_a_book_without_clearing_other_commands(qtbot: QtBot) -> None:
    window = QWidget()
    qtbot.addWidget(window)
    window.show()
    window.setFocus()
    fired: list[str] = []
    book = ShortcutBook(window)
    book.bind("save", "Ctrl+S", lambda: fired.append("save"))
    palette = CommandPalette(window)
    qtbot.addWidget(palette)
    palette.activated.connect(fired.append)
    palette.set_commands([Command("find", "查找", shortcut="Ctrl+K")])
    palette.install(window, book)
    _fire(window, "Ctrl+S")
    _fire(window, "Ctrl+K")
    assert fired == ["save", "find"]
