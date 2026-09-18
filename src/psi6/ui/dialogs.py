"""统一对话框，避免各处直接堆 ``QMessageBox``。"""

from __future__ import annotations

from PySide6.QtWidgets import QMessageBox, QWidget


def inform(parent: QWidget | None, title: str, text: str) -> None:
    """信息提示。"""

    QMessageBox.information(parent, title, text)


def warn(parent: QWidget | None, title: str, text: str) -> None:
    """警告，不阻断后续操作的选择。"""

    QMessageBox.warning(parent, title, text)


def fail(parent: QWidget | None, title: str, text: str, *, detail: str | None = None) -> None:
    """错误。``detail`` 放进可展开的详细信息，默认不把堆栈甩给用户。"""

    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Critical)
    box.setWindowTitle(title)
    box.setText(text)
    if detail:
        box.setDetailedText(detail)
    box.exec()


def confirm(parent: QWidget | None, title: str, text: str) -> bool:
    """确认。返回是否选择了「是」。"""

    answer = QMessageBox.question(
        parent,
        title,
        text,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    return answer == QMessageBox.StandardButton.Yes
