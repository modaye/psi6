"""标签：过滤条件、文件类型，不要用它替代表格行。"""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import QEvent, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QPen
from PySide6.QtWidgets import QPushButton, QWidget

from psi6.theme.apply import apply_psi6_button_style
from psi6.theme.colors import mix_hex
from psi6.theme.paint import as_color, create_painter
from psi6.theme.runtime import token_color, token_int
from psi6.ui._tone import set_tone
from psi6.ui.flow_layout import FlowLayout
from psi6.ui.tone import Tone, normalize_tone

_THEME_EVENTS = {QEvent.Type.PaletteChange, QEvent.Type.StyleChange}


def _tone_paint(tone: str) -> tuple[str, str, str]:
    """填充、字色、描边。描边比填充更靠近语义色，仍是和底色的混合。"""

    name = normalize_tone(tone)
    canvas = token_color("bg")
    if name == "neutral":
        return token_color("hover"), token_color("muted"), token_color("control_border")
    ink = token_color("danger" if name == "error" else name)
    return mix_hex(ink, canvas, 0.88), ink, mix_hex(ink, canvas, 0.72)


class Tag(QPushButton):
    """可点选的短标签。``checkable`` 时用作筛选芯片。

    胶囊自己画。样式表的圆角描边在 1px 上会发虚，这里把边内收半像素再描。
    """

    def __init__(
        self,
        text: str,
        *,
        tone: Tone | str = "neutral",
        checkable: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)
        self.setObjectName("psi6Tag")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        apply_psi6_button_style(self)
        self.setCheckable(checkable)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        set_tone(self, tone)
        self._sync_height()

    def _sync_height(self) -> None:
        self.setFixedHeight(max(20, token_int("control_height_sm")))

    def sizeHint(self) -> QSize:
        pad = token_int("space_md")
        width = self.fontMetrics().horizontalAdvance(self.text()) + pad * 2
        return QSize(max(width, self.height()), self.height())

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def enterEvent(self, event) -> None:
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.update()
        super().leaveEvent(event)

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if event.type() in _THEME_EVENTS:
            self._sync_height()
            self.update()

    def paintEvent(self, _event) -> None:
        """抗锯齿胶囊。不走样式表描边。"""

        fill, ink, edge = _tone_paint(str(self.property("tone") or "neutral"))
        if not self.isEnabled():
            fill, ink, edge = (
                token_color("bg"),
                token_color("disabled"),
                token_color("border_subtle"),
            )
        elif self.isChecked():
            fill, ink, edge = token_color("info"), token_color("on_primary"), token_color("info")
        elif self.underMouse():
            ink = token_color("text")
            edge = token_color("primary")
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = rect.height() / 2
        pen = QPen(as_color(edge))
        pen.setWidthF(1.0)
        with create_painter(self, clear_pen=False) as painter:
            painter.setPen(pen)
            painter.setBrush(as_color(fill))
            painter.drawRoundedRect(rect, radius, radius)
            painter.setPen(as_color(ink))
            painter.setFont(self.font())
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text())


class TagRow(QWidget):
    """一排互斥标签。宽度不够时换行。再点已选项则取消。空列表时隐藏。"""

    tag_selected = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("psi6TagRow")
        self._flow = FlowLayout(self)
        self._tags: list[Tag] = []
        self.hide()

    def set_labels(self, labels: Sequence[str], *, tone: Tone | str = "info") -> None:
        """重建标签。重复项会去掉，最多 12 个。

        标签行应已经放进布局。还没有父控件时只建好标签并保持隐藏。
        """

        unique: list[str] = []
        seen: set[str] = set()
        for raw in labels:
            text = str(raw).strip()
            if not text or text in seen:
                continue
            seen.add(text)
            unique.append(text)
            if len(unique) >= 12:
                break
        self.clear()
        for text in unique:
            tag = Tag(text, tone=tone)
            tag.clicked.connect(lambda checked, value=text: self._on_clicked(value, checked))
            self._flow.addWidget(tag)
            self._tags.append(tag)
        if not self._tags or self.parentWidget() is None:
            # 空列表保持隐藏。还没进布局时也不 show()，初始显隐由调用方放进布局后再决定。
            self.hide()
        else:
            self.show()

    def selected(self) -> str:
        """当前选中的标签文本；没有选中则为空串。"""

        for tag in self._tags:
            if tag.isChecked():
                return tag.text()
        return ""

    def select(self, label: str) -> None:
        """按文本选中并发出信号；空串表示全部取消。"""

        self.set_checked(label)
        self.tag_selected.emit(self.selected())

    def set_checked(self, label: str) -> None:
        """同步选中态，不发信号。用于和搜索框互相同步。"""

        wanted = label.strip()
        for tag in self._tags:
            tag.blockSignals(True)
            tag.setChecked(tag.text() == wanted)
            tag.blockSignals(False)

    def clear(self) -> None:
        """去掉全部标签。"""

        while self._flow.count():
            item = self._flow.takeAt(0)
            if item is None:
                break
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.deleteLater()
        self._tags.clear()
        self.hide()

    def _on_clicked(self, value: str, checked: bool) -> None:
        if not checked:
            self.tag_selected.emit("")
            return
        for tag in self._tags:
            if tag.text() != value:
                tag.setChecked(False)
        self.tag_selected.emit(value)
