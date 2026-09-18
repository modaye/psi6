"""带标题的内容分区，替代页面里手写 QGroupBox。"""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class Section(QWidget):
    """一块带标题和可选说明的内容区。业务把子控件 ``add_widget`` 进来。"""

    def __init__(
        self,
        title: str,
        *,
        description: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("psi6Section")
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 16, 12, 12)
        root.setSpacing(8)

        self._title = QLabel(title)
        self._title.setObjectName("psi6SectionTitle")
        root.addWidget(self._title)

        self._hint = QLabel(description)
        self._hint.setObjectName("psi6SectionHint")
        self._hint.setWordWrap(True)
        root.addWidget(self._hint)
        if not description:
            self._hint.hide()

        self._body = QVBoxLayout()
        self._body.setContentsMargins(0, 4, 0, 0)
        self._body.setSpacing(8)
        root.addLayout(self._body)

    @property
    def body(self) -> QVBoxLayout:
        """子控件应加入的布局。"""

        return self._body

    def add_widget(self, widget: QWidget, *, stretch: int = 0) -> None:
        """把子控件放进分区主体。"""

        self._body.addWidget(widget, stretch)

    def set_title(self, title: str) -> None:
        self._title.setText(title)

    def set_description(self, description: str) -> None:
        self._hint.setText(description)
        if description:
            self._hint.show()
        else:
            self._hint.hide()
