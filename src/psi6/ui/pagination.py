"""分页。页码从 1 开始。超过 7 页时只留首页、末页和当前页两侧，中间用省略号。"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from psi6.theme.runtime import token_int
from psi6.ui.buttons import ghost_button, primary_button
from psi6.ui.icon import IconButton

_ELLIPSIS = "…"


def page_window(total: int, current: int) -> list[int | str]:
    """当前页附近要画出的页码。``…`` 表示中间被收起的一段。

    不超过 7 页时全部列出。更多页时始终保留第 1 页和最后一页，
    当前页左右各留一页；和首页或末页之间空出两页以上才放省略号。
    """

    total = max(1, total)
    current = max(1, min(current, total))
    if total <= 7:
        return list(range(1, total + 1))
    pages: list[int | str] = [1]
    start = max(2, current - 1)
    end = min(total - 1, current + 1)
    if start > 2:
        pages.append(_ELLIPSIS)
    pages.extend(range(start, end + 1))
    if end < total - 1:
        pages.append(_ELLIPSIS)
    pages.append(total)
    return pages


class Pagination(QWidget):
    """上一页、页码和下一页。当前页是主按钮，其余是幽灵按钮。"""

    page_changed = Signal(int)

    def __init__(self, total: int = 1, *, current: int = 1, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("psi6Pagination")
        self._total = max(1, total)
        self._current = max(1, min(current, self._total))
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(4)
        self._rebuild()

    def total(self) -> int:
        return self._total

    def current(self) -> int:
        return self._current

    def set_total(self, total: int) -> None:
        """改总页数。当前页超出时收到最后一页，并发 ``page_changed``。"""

        self._total = max(1, total)
        clamped = min(self._current, self._total)
        changed = clamped != self._current
        self._current = clamped
        self._rebuild()
        if changed:
            self.page_changed.emit(self._current)

    def set_current(self, page: int) -> None:
        """切到 ``page``。越界收到 1 或最后一页。页码没变时不发信号。"""

        page = max(1, min(page, self._total))
        if page == self._current:
            return
        self._current = page
        self._rebuild()
        self.page_changed.emit(page)

    def _rebuild(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        side = max(28, token_int("control_height_sm", 28))
        # 两位数要放得下。样式表的内边距比 28 宽，按「88」的建议宽度取齐。
        probe = ghost_button("88")
        chip = max(side, probe.sizeHint().width())
        chip_height = max(side, probe.sizeHint().height())
        probe.deleteLater()
        previous = IconButton("arrow-left", label="上一页", extent=chip_height)
        previous.setEnabled(self._current > 1)
        previous.clicked.connect(lambda: self.set_current(self._current - 1))
        self._layout.addWidget(previous)
        for entry in page_window(self._total, self._current):
            if entry == _ELLIPSIS:
                mark = QLabel(_ELLIPSIS)
                mark.setObjectName("psi6Hint")
                mark.setFixedWidth(side)
                mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self._layout.addWidget(mark)
                continue
            button = (
                primary_button(str(entry)) if entry == self._current else ghost_button(str(entry))
            )
            button.setFixedSize(chip, chip_height)
            button.clicked.connect(
                lambda _checked=False, chosen=entry: self.set_current(int(chosen))
            )
            self._layout.addWidget(button)
        following = IconButton("arrow-right", label="下一页", extent=chip_height)
        following.setEnabled(self._current < self._total)
        following.clicked.connect(lambda: self.set_current(self._current + 1))
        self._layout.addWidget(following)
