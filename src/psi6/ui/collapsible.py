"""可折叠分区：把不常用字段收进「高级选项」。"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QPushButton, QVBoxLayout, QWidget

from psi6.ui.icon import apply_button_icon


class Collapsible(QWidget):
    """标题行 + 可隐藏主体。默认收起。"""

    toggled = Signal(bool)

    def __init__(
        self,
        title: str,
        *,
        expanded: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("psi6Collapsible")
        self._title = title
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        self._header = QPushButton()
        self._header.setObjectName("psi6CollapsibleHeader")
        self._header.setCheckable(True)
        self._header.toggled.connect(self._on_toggled)
        root.addWidget(self._header)

        self._body = QWidget()
        self._body.setObjectName("psi6CollapsibleBody")
        self._body_layout = QVBoxLayout(self._body)
        self._body_layout.setContentsMargins(0, 0, 0, 0)
        self._body_layout.setSpacing(8)
        root.addWidget(self._body)
        self._header.blockSignals(True)
        self._header.setChecked(expanded)
        self._header.blockSignals(False)
        if not expanded:
            self._body.hide()
        self._sync_header()

    @property
    def body(self) -> QVBoxLayout:
        """子控件应加入的布局。"""

        return self._body_layout

    def add_widget(self, widget: QWidget, *, stretch: int = 0) -> None:
        """把子控件放进折叠主体。"""

        self._body_layout.addWidget(widget, stretch)

    def is_expanded(self) -> bool:
        return self._header.isChecked()

    def set_expanded(self, expanded: bool) -> None:
        self._header.blockSignals(True)
        self._header.setChecked(expanded)
        self._header.blockSignals(False)
        self._apply_expanded(expanded)

    def _on_toggled(self, expanded: bool) -> None:
        self._apply_expanded(expanded)
        self.toggled.emit(expanded)

    def _apply_expanded(self, expanded: bool) -> None:
        if expanded:
            self._body.show()
        else:
            self._body.hide()
        self._sync_header()

    def _sync_header(self) -> None:
        expanded = self._header.isChecked()
        apply_button_icon(self._header, "chevron-down" if expanded else "chevron-right")
        self._header.setText(self._title)
