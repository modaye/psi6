"""标签：过滤条件、文件类型，不要用它替代表格行。"""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QPushButton, QWidget

from psi6.ui._tone import set_tone
from psi6.ui.flow_layout import FlowLayout
from psi6.ui.tone import Tone


class Tag(QPushButton):
    """可点选的短标签。``checkable`` 时用作筛选芯片。"""

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
        self.setCheckable(checkable)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        set_tone(self, tone)


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
        """重建标签。重复项会去掉，最多 12 个。"""

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
        if self._tags:
            self.show()
        else:
            self.hide()

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
