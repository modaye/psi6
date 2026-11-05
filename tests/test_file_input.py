"""FileInput / FolderInput 校验。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLineEdit, QWidget
from pytestqt.qtbot import QtBot

from psi6.ui.file_input import FileInput, FolderInput, PathState


def test_file_input_valid_and_invalid(qtbot: QtBot, tmp_path: Path) -> None:
    existing = tmp_path / "a.txt"
    existing.write_text("x", encoding="utf-8")
    widget = FileInput()
    qtbot.addWidget(widget)
    assert widget.is_valid() is False
    widget.set_path(existing)
    assert widget.path() == existing
    assert widget.is_valid() is True
    widget.set_path(tmp_path / "missing.txt")
    assert widget.is_valid() is False
    assert widget.state is PathState.INVALID


def test_allow_empty_folder(qtbot: QtBot) -> None:
    widget = FolderInput(allow_empty=True)
    qtbot.addWidget(widget)
    assert widget.state is PathState.EMPTY
    assert widget.is_valid() is True


def test_path_edited_waits_until_editing_finishes(qtbot: QtBot, tmp_path: Path) -> None:
    widget = FileInput(allow_empty=True)
    qtbot.addWidget(widget)
    changed: list[object] = []
    edited: list[object] = []
    widget.path_changed.connect(changed.append)
    widget.path_edited.connect(edited.append)
    widget.show()
    qtbot.waitExposed(widget)
    edit = widget.findChild(QLineEdit)
    assert edit is not None
    assert edit.isClearButtonEnabled()
    edit.setFocus()
    qtbot.keyClicks(edit, "memo")
    assert changed
    assert edited == []
    qtbot.keyClick(edit, Qt.Key.Key_Return)
    assert len(edited) == 1
    assert str(edited[0]).endswith("memo")


def test_folder_input(qtbot: QtBot, tmp_path: Path) -> None:
    widget = FolderInput()
    qtbot.addWidget(widget)
    widget.set_path(tmp_path)
    assert widget.is_valid() is True
    widget.set_path(tmp_path / "nope")
    assert widget.is_valid() is False


def test_invalid_state_refresh_is_debounced(qtbot: QtBot, tmp_path: Path) -> None:
    widget = FileInput()
    qtbot.addWidget(widget)
    picker = widget.findChild(QWidget, "psi6PathPicker")
    assert picker is not None
    widget.set_path(tmp_path / "missing.txt")
    assert widget.state is PathState.INVALID
    assert picker.property("invalid") is False
    qtbot.waitUntil(lambda: picker.property("invalid") is True, timeout=1000)


def test_paths_with_semicolons_are_kept(qtbot: QtBot, tmp_path: Path) -> None:
    tricky = tmp_path / "a;b.txt"
    tricky.write_text("x", encoding="utf-8")
    plain = tmp_path / "plain.txt"
    plain.write_text("x", encoding="utf-8")
    widget = FileInput(multiple=True)
    qtbot.addWidget(widget)
    widget.set_paths([plain, tricky])
    assert widget.paths() == [plain, tricky]
    assert widget.is_valid() is True
    single = FileInput()
    qtbot.addWidget(single)
    single.set_path(tricky)
    assert single.paths() == [tricky]
