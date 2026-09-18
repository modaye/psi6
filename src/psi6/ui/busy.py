"""忙碌层：盖在结果表上，避免任务跑着还能点选空表。"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget

from psi6.ui.icon import Icon


class BusyOverlay(QWidget):
    """作为 ``host`` 的子控件覆盖其客户区。不进布局，随宿主 Resize。"""

    def __init__(self, host: QWidget) -> None:
        super().__init__(host)
        self.setObjectName("psi6BusyOverlay")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.hide()

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)
        layout.addWidget(Icon("refresh", size=22, tone="info"), alignment=Qt.AlignmentFlag.AlignCenter)
        self._bar = QProgressBar()
        self._bar.setRange(0, 0)
        self._bar.setFixedWidth(220)
        self._bar.setTextVisible(False)
        layout.addWidget(self._bar, alignment=Qt.AlignmentFlag.AlignCenter)
        self._label = QLabel("正在处理…")
        self._label.setObjectName("psi6Hint")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._label)

        host.installEventFilter(self)
        self._sync_geometry()

    def show_busy(self, message: str = "正在处理…") -> None:
        """显示覆盖层。"""

        self._label.setText(message.strip() or "正在处理…")
        self._sync_geometry()
        self.show()
        self.raise_()

    def hide_busy(self) -> None:
        """隐藏覆盖层。"""

        self.hide()

    def is_busy(self) -> bool:
        return not self.isHidden()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self.parent() and event.type() == QEvent.Type.Resize:
            self._sync_geometry()
        return super().eventFilter(watched, event)

    def _sync_geometry(self) -> None:
        host = self.parentWidget()
        if host is not None:
            self.setGeometry(host.rect())
