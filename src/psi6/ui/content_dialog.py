"""带主体的主题对话框。短句仍用 ``confirm`` / ``fail`` / ``inform``。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from psi6.ui.buttons import ghost_button, primary_button


class ContentDialog(QDialog):
    """标题 + 任意 ``QWidget`` 主体（粘贴框、FAQ、CheckList）。"""

    def __init__(
        self,
        title: str,
        body: QWidget,
        *,
        primary: str = "确定",
        secondary: str = "取消",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("psi6ContentDialog")
        self.setModal(True)
        self.setWindowTitle(title)
        self.setMinimumWidth(440)
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)
        heading = QLabel(title)
        heading.setObjectName("psi6DialogTitle")
        heading.setWordWrap(True)
        root.addWidget(heading)
        root.addWidget(body, stretch=1)
        bar = QHBoxLayout()
        bar.addStretch()
        self._secondary = None
        text = secondary.strip()
        if text:
            cancel = ghost_button(text)
            cancel.setAccessibleName(text)
            cancel.clicked.connect(self.reject)
            bar.addWidget(cancel)
            self._secondary = cancel
        ok = primary_button(primary)
        ok.setAccessibleName(primary)
        ok.setDefault(True)
        ok.clicked.connect(self.accept)
        bar.addWidget(ok)
        self._primary = ok
        root.addLayout(bar)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

    def run(self) -> bool:
        """弹出并返回是否点了主按钮。"""

        return self.exec() == QDialog.DialogCode.Accepted
