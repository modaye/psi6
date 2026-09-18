"""筛选输入：结果表、日志、清单共用。"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QLineEdit, QWidget

from psi6.theme.runtime import token_int
from psi6.ui.icon import token_color
from psi6.icons.render import pixmap_for


class SearchField(QLineEdit):
    """带搜索图标和清除按钮的筛选框。"""

    query_changed = Signal(str)

    def __init__(
        self,
        *,
        placeholder: str = "筛选…",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("psi6SearchField")
        self.setPlaceholderText(placeholder)
        self.setClearButtonEnabled(True)
        self._leading = QAction(self)
        self.addAction(self._leading, QLineEdit.ActionPosition.LeadingPosition)
        self.textChanged.connect(self.query_changed.emit)
        self._sync_leading()

    def query(self) -> str:
        """当前筛选文本。"""

        return self.text().strip()

    def changeEvent(self, event) -> None:  # noqa: ANN001
        super().changeEvent(event)
        self._sync_leading()

    def _sync_leading(self) -> None:
        pix = pixmap_for(
            "search",
            color=token_color(self, tone="neutral"),
            size=max(12, token_int("icon_size", 16) - 2),
        )
        self._leading.setIcon(QIcon(pix))
        self._leading.setIconVisibleInMenu(False)
