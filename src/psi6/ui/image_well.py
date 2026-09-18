"""图标/图片井：缩略图 + 选择/清除。对话框仍走 ``FileInput``。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from psi6.ui.buttons import ghost_button, text_button
from psi6.ui.file_input import FileInput
from psi6.ui.icon import Icon

_DEFAULT_FILTERS = "Images (*.png *.ico *.jpg *.jpeg *.webp *.bmp *.icns)"


class ImageWell(QWidget):
    """确认页可选图标。没有图时显示占位，不强迫选择。"""

    path_changed = Signal(object)

    def __init__(
        self,
        *,
        filters: str = _DEFAULT_FILTERS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("psi6ImageWell")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        row = QHBoxLayout(self)
        row.setContentsMargins(12, 12, 12, 12)
        row.setSpacing(12)
        self._frame = QWidget()
        self._frame.setObjectName("psi6ImageWellThumb")
        self._frame.setFixedSize(64, 64)
        inner = QVBoxLayout(self._frame)
        inner.setContentsMargins(0, 0, 0, 0)
        self._placeholder = Icon("file-plus", size=22, tone="info")
        inner.addWidget(self._placeholder, alignment=Qt.AlignmentFlag.AlignCenter)
        self._thumb = QLabel()
        self._thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inner.addWidget(self._thumb, alignment=Qt.AlignmentFlag.AlignCenter)
        row.addWidget(self._frame)
        col = QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(6)
        hint = QLabel("图标可跳过")
        hint.setObjectName("psi6Hint")
        col.addWidget(hint)
        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        choose = ghost_button("选择")
        choose.setAccessibleName("选择图标")
        choose.clicked.connect(self._choose)
        actions.addWidget(choose)
        clear = text_button("清除")
        clear.setAccessibleName("清除图标")
        clear.clicked.connect(self.clear)
        actions.addWidget(clear)
        actions.addStretch()
        col.addLayout(actions)
        row.addLayout(col, stretch=1)
        self._input = FileInput(filters=filters, allow_empty=True, parent=self)
        self._input.hide()
        self._input.path_changed.connect(self._on_picked)
        self._sync_thumb(None)

    def path(self) -> Path | None:
        return self._input.path()

    def set_path(self, path: Path | str | None) -> None:
        self._input.set_path(path)

    def clear(self) -> None:
        """去掉当前图。"""

        self._input.set_path(None)

    def _choose(self) -> None:
        self._input.browse()

    def _on_picked(self, value: object) -> None:
        path = value if isinstance(value, Path) else self._input.path()
        self._sync_thumb(path)
        self.path_changed.emit(path)

    def _sync_thumb(self, path: Path | None) -> None:
        if path is None or not path.is_file():
            self._thumb.clear()
            self._thumb.hide()
            self._placeholder.show()
            return
        pix = QPixmap(str(path))
        if pix.isNull():
            self._thumb.clear()
            self._thumb.hide()
            self._placeholder.show()
            return
        self._placeholder.hide()
        self._thumb.setPixmap(
            pix.scaled(
                64,
                64,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self._thumb.show()


IconPreview = ImageWell
