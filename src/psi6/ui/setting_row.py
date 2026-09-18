"""设置行：左侧说明，右侧开关。适合偏好页，不替代表单里的复选框。"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from psi6.ui.switch import Switch


class SettingRow(QWidget):
    """一行设置。``toggled`` 给出开关状态。"""

    toggled = Signal(bool)

    def __init__(
        self,
        title: str,
        *,
        hint: str = "",
        checked: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("psi6SettingRow")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 8, 0, 8)
        row.setSpacing(12)
        text = QVBoxLayout()
        text.setContentsMargins(0, 0, 0, 0)
        text.setSpacing(2)
        self._title = QLabel(title)
        self._title.setObjectName("psi6SettingTitle")
        text.addWidget(self._title)
        self._hint = QLabel(hint)
        self._hint.setObjectName("psi6Hint")
        self._hint.setWordWrap(True)
        text.addWidget(self._hint)
        if not hint:
            self._hint.hide()
        row.addLayout(text, stretch=1)
        self._switch = Switch(checked=checked)
        self._switch.setAccessibleName(title)
        self._switch.toggled.connect(self.toggled.emit)
        row.addWidget(self._switch, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    def is_checked(self) -> bool:
        return self._switch.isChecked()

    def set_checked(self, checked: bool) -> None:
        self._switch.setChecked(checked)

    def switch(self) -> Switch:
        """行内开关，便于绑定快捷键或测试。"""

        return self._switch
