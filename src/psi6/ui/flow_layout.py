"""流式布局：一行放不下就换行。标签、工具箱瓷砖用，不要手算坐标。"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import QLayout, QLayoutItem, QWidget

from psi6.theme.runtime import token_int


class FlowLayout(QLayout):
    """按控件 ``sizeHint`` 从左到右排列，超出宽度换下一行。"""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        spacing: int | None = None,
    ) -> None:
        super().__init__(parent)
        self._items: list[QLayoutItem] = []
        self._explicit_spacing = spacing
        self._apply_spacing()

    def _apply_spacing(self) -> None:
        gap = token_int("space_sm", 6) if self._explicit_spacing is None else self._explicit_spacing
        self.setSpacing(max(0, gap))

    def apply_metrics(self) -> None:
        """主题 / 密度切换后重读自动间距。

        ``QLayout`` 不是 ``QWidget``，收不到 ``StyleChange``，构造时缓存的
        ``setSpacing`` 只能靠 ``refresh_metrics`` 的布局树广播来刷新。
        显式传过 ``spacing`` 的布局是调用方自己定的，不覆盖。
        """

        if self._explicit_spacing is None:
            self._apply_spacing()
            self.invalidate()

    def addItem(self, item: QLayoutItem) -> None:
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int) -> QLayoutItem | None:
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int) -> QLayoutItem | None:
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientation:
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._fill(QRect(0, 0, width, 0), test=True)

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self._fill(rect, test=False)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _fill(self, rect: QRect, *, test: bool) -> int:
        margins = self.contentsMargins()
        area = rect.adjusted(margins.left(), margins.top(), -margins.right(), -margins.bottom())
        cursor_x = area.x()
        cursor_y = area.y()
        line_height = 0
        gap = self.spacing()
        right = area.x() + area.width()
        for item in self._items:
            hint = item.sizeHint()
            next_x = cursor_x + hint.width()
            if line_height and next_x > right and cursor_x > area.x():
                cursor_x = area.x()
                cursor_y += line_height + gap
                next_x = cursor_x + hint.width()
                line_height = 0
            if not test:
                item.setGeometry(QRect(QPoint(cursor_x, cursor_y), hint))
            cursor_x = next_x + gap
            line_height = max(line_height, hint.height())
        return cursor_y + line_height - rect.y() + margins.bottom()
