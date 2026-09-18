"""页面标题、统计卡片、分隔线。"""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from psi6.ui.icon import Icon
from psi6.ui.sparkline import Sparkline


class PageHeader(QWidget):
    """内容区顶部：标题、说明、右侧操作。"""

    def __init__(
        self,
        title: str,
        *,
        hint: str = "",
        icon: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("psi6PageHeader")
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        if icon:
            row.addWidget(Icon(icon, size=20), alignment=Qt.AlignmentFlag.AlignTop)
        text = QVBoxLayout()
        text.setContentsMargins(0, 0, 0, 0)
        text.setSpacing(2)
        self._title = QLabel(title)
        self._title.setObjectName("psi6PageTitle")
        text.addWidget(self._title)
        self._hint = QLabel(hint)
        self._hint.setObjectName("psi6PageHint")
        text.addWidget(self._hint)
        if not hint:
            self._hint.hide()
        row.addLayout(text, stretch=1)
        self._trailing = QHBoxLayout()
        self._trailing.setContentsMargins(0, 0, 0, 0)
        row.addLayout(self._trailing)

    def add_trailing(self, widget: QWidget) -> None:
        self._trailing.addWidget(widget)


class StatCard(QWidget):
    """Dashboard / 监控上的关键数字。"""

    def __init__(
        self,
        label: str,
        value: str,
        *,
        hint: str = "",
        icon: str = "activity",
        sparkline: Sequence[float] = (),
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("psi6StatCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.setMinimumWidth(168)
        self.setMaximumWidth(280)
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(6)
        top = QHBoxLayout()
        caption = QLabel(label)
        caption.setObjectName("psi6Hint")
        top.addWidget(caption)
        top.addStretch()
        top.addWidget(Icon(icon, tone="info"))
        root.addLayout(top)
        self._value = QLabel(value)
        self._value.setObjectName("psi6StatValue")
        root.addWidget(self._value)
        self._spark = Sparkline(sparkline)
        root.addWidget(self._spark)
        if not tuple(sparkline):
            self._spark.hide()
        self._hint = QLabel(hint)
        self._hint.setObjectName("psi6Hint")
        root.addWidget(self._hint)
        if not hint:
            self._hint.hide()

    def set_value(self, value: str, *, hint: str | None = None) -> None:
        self._value.setText(value)
        if hint is not None:
            self._hint.setText(hint)
            if hint:
                self._hint.show()
            else:
                self._hint.hide()

    def set_sparkline(self, values: Sequence[float]) -> None:
        self._spark.set_values(values)
        if len(tuple(values)) >= 2:
            self._spark.show()
        else:
            self._spark.hide()


class HLine(QFrame):
    """细分隔线。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("psi6Rule")
        self.setFrameShape(QFrame.Shape.HLine)
        self.setFrameShadow(QFrame.Shadow.Plain)
        self.setFixedHeight(1)
