"""状态栏进度。没有另行指定位置时，进度条放在这里，不放进按钮行。"""

from __future__ import annotations

from PySide6.QtWidgets import QProgressBar, QStatusBar


class StatusProgress(QProgressBar):
    """挂在状态栏右侧的进度条。

    说明文字用状态栏左侧的 ``showMessage``。条本身只表示比例，不占页面中间。
    ``on_progress`` 可以直接接到 ``set_progress``。
    产品明确要求进度出现在页面里时，再单独放一个 ``QProgressBar``，不要两处同时显示。
    """

    def __init__(self, status_bar: QStatusBar) -> None:
        super().__init__(status_bar)
        self._status = status_bar
        self.setObjectName("psi6StatusProgress")
        self.setTextVisible(False)
        self.setFixedWidth(140)
        self.setMaximumHeight(14)
        self.hide()
        status_bar.addPermanentWidget(self)

    def set_progress(self, current: int, total: int, message: str = "") -> None:
        """显示进度。``total`` 小于等于 0 时为不定进度。"""

        if total > 0:
            self.setRange(0, total)
            self.setValue(max(0, min(current, total)))
        else:
            self.setRange(0, 0)
        self.show()
        if message:
            self._status.showMessage(message)

    def finish(self, message: str = "") -> None:
        """收起进度条。有结束语时留在状态栏文字里。"""

        self.hide()
        self.reset()
        if message:
            self._status.showMessage(message)
