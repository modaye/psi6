"""空态：表格、日志、属性在没有数据时的占位。"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from psi6.ui.icon import Icon
from psi6.ui.tone import Tone


class EmptyState(QWidget):
    """居中说明当前为什么是空的，以及下一步做什么。"""

    action_clicked = Signal()

    def __init__(
        self,
        title: str = "暂无数据",
        hint: str = "",
        *,
        action_text: str = "",
        icon: str = "inbox",
        tone: Tone | str = "neutral",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("psi6EmptyState")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 32, 24, 32)
        root.setSpacing(8)
        root.addStretch()

        self._icon = Icon(icon, size=28, tone=tone)
        root.addWidget(self._icon, alignment=Qt.AlignmentFlag.AlignHCenter)

        self._title = QLabel(title)
        self._title.setObjectName("psi6EmptyTitle")
        self._title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._title.setWordWrap(True)
        self._title.setMinimumWidth(280)
        self._title.setMaximumWidth(420)
        self._title.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        root.addWidget(self._title, alignment=Qt.AlignmentFlag.AlignHCenter)

        self._hint = QLabel(hint)
        self._hint.setObjectName("psi6EmptyHint")
        self._hint.setWordWrap(True)
        self._hint.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._hint.setMinimumWidth(280)
        self._hint.setMaximumWidth(420)
        self._hint.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        root.addWidget(self._hint, alignment=Qt.AlignmentFlag.AlignHCenter)
        if not hint:
            self._hint.hide()

        self._action = QPushButton(action_text)
        self._action.setObjectName("psi6Primary")
        self._action.clicked.connect(self.action_clicked.emit)
        root.addWidget(self._action, alignment=Qt.AlignmentFlag.AlignHCenter)
        if not action_text:
            self._action.hide()
        root.addStretch()

    def set_copy(
        self,
        title: str,
        hint: str = "",
        *,
        action_text: str = "",
        icon: str | None = None,
    ) -> None:
        """更新文案。``action_text`` 为空则隐藏按钮。"""

        self._title.setText(title)
        self._hint.setText(hint)
        if hint:
            self._hint.show()
        else:
            self._hint.hide()
        self._action.setText(action_text)
        if action_text:
            self._action.show()
        else:
            self._action.hide()
        if icon:
            self._icon.set_name(icon)
