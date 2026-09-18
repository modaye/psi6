"""对话框封装可调用。"""

from __future__ import annotations

from pytestqt.qtbot import QtBot
from PySide6.QtWidgets import QWidget

from psi6.ui import dialogs


def test_inform_does_not_raise(qtbot: QtBot, monkeypatch) -> None:
    widget = QWidget()
    qtbot.addWidget(widget)
    monkeypatch.setattr(dialogs.QMessageBox, "information", lambda *args, **kwargs: None)
    dialogs.inform(widget, "标题", "内容")


def test_confirm_yes(qtbot: QtBot, monkeypatch) -> None:
    from PySide6.QtWidgets import QMessageBox

    widget = QWidget()
    qtbot.addWidget(widget)
    monkeypatch.setattr(
        dialogs.QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )
    assert dialogs.confirm(widget, "确认", "继续？") is True
