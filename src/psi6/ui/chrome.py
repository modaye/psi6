"""页面标题、统计卡片、分隔线。"""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from psi6.ui.icon import Icon
from psi6.ui.sparkline import Sparkline
from psi6.ui.style import set_style


class PageHeader(QWidget):
    """内容区顶部：标题、说明、右侧操作。"""

    def __init__(
        self,
        title: str,
        *,
        hint: str = "",
        icon: str = "",
        eyebrow: str = "",
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
        self._eyebrow = QLabel(eyebrow)
        self._eyebrow.setObjectName("psi6Eyebrow")
        text.addWidget(self._eyebrow)
        if not eyebrow:
            self._eyebrow.hide()
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
    """Dashboard / 监控上的关键数字。

    ``fill``、``icon_color``、``value_size``、``value_weight`` 只作用于这一张卡片。
    颜色可以是 ``#RRGGBB``，也可以是 ``primary`` 这类 token 名。
    """

    def __init__(
        self,
        label: str,
        value: str,
        *,
        hint: str = "",
        icon: str = "activity",
        sparkline: Sequence[float] = (),
        wide: bool = False,
        unit: str = "",
        hint_tone: str = "",
        fill: str = "",
        icon_color: str = "",
        value_size: int | None = None,
        value_weight: int | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("psi6StatCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.setMinimumWidth(168)
        if not wide:
            self.setMaximumWidth(280)
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(6)
        top = QHBoxLayout()
        caption = QLabel(label)
        caption.setObjectName("psi6Hint")
        top.addWidget(caption)
        top.addStretch()
        chip = QWidget()
        chip.setObjectName("psi6MetricIcon")
        chip.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        chip.setFixedSize(28, 28)
        chip_layout = QHBoxLayout(chip)
        chip_layout.setContentsMargins(0, 0, 0, 0)
        glyph = Icon(icon, size=14, tone="success")
        if icon_color:
            glyph.set_color(icon_color)
        chip_layout.addWidget(glyph, alignment=Qt.AlignmentFlag.AlignCenter)
        if fill:
            set_style(chip, fill=fill, radius=7)
        top.addWidget(chip)
        root.addLayout(top)
        self._value = QLabel(value)
        self._value.setObjectName("psi6StatValue")
        if value_size is not None or value_weight is not None:
            set_style(self._value, size=value_size, weight=value_weight, color="text")
        value_row = QHBoxLayout()
        value_row.setContentsMargins(0, 0, 0, 0)
        value_row.setSpacing(6)
        value_row.addWidget(self._value, alignment=Qt.AlignmentFlag.AlignBaseline)
        self._unit = QLabel(unit)
        self._unit.setObjectName("psi6Hint")
        value_row.addWidget(self._unit, alignment=Qt.AlignmentFlag.AlignBaseline)
        value_row.addStretch(1)
        if not unit:
            self._unit.hide()
        root.addLayout(value_row)
        self._spark = Sparkline(sparkline)
        root.addWidget(self._spark)
        if not tuple(sparkline):
            self._spark.hide()
        self._hint = QLabel(hint)
        self._hint.setObjectName("psi6Hint")
        if hint_tone:
            self._hint.setProperty("tone", hint_tone)
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


class Panel(QWidget):
    """一块白底表面。首页卡片、设置分组和侧栏说明都用它，不用自己写样式。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("psi6Panel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(16, 14, 16, 14)
        self.body.setSpacing(8)


class HLine(QFrame):
    """细分隔线。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("psi6Rule")
        self.setFrameShape(QFrame.Shape.HLine)
        self.setFrameShadow(QFrame.Shadow.Plain)
        self.setFixedHeight(1)
