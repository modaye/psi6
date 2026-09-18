"""首页拖放热区：大点击面 + URL 拖入。路径行请用 ``FileInput``。"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDragMoveEvent, QDropEvent, QMouseEvent
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

from psi6.theme.runtime import token_int
from psi6.ui.file_input import FileInput, FolderInput
from psi6.ui.icon import Icon
from psi6.ui.tag import Tag

Mode = Literal["file", "files", "folder"]
Size = Literal["compact", "comfortable", "hero"]


class DropZone(QWidget):
    """把文件拖进来或点一下选择。``filters`` 与 ``FileInput`` 同形，不要写死扩展名。"""

    clicked = Signal()
    files_dropped = Signal(list)

    def __init__(
        self,
        title: str = "把文件拖到这里",
        hint: str = "也可以点击选择",
        *,
        icon: str = "file",
        filters: str = "All Files (*)",
        mode: Mode = "file",
        size: Size = "comfortable",
        badge: str = "",
        browse_on_click: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("psi6DropZone")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        control = token_int("control_height", 32)
        height = {
            "compact": control * 4,
            "comfortable": control * 6,
            "hero": control * 8,
        }.get(size, control * 6)
        self.setMinimumHeight(max(140, height))
        self.setAccessibleName(title)
        self._filters = filters
        self._mode: Mode = mode
        self._browse_on_click = browse_on_click
        self._suffixes = _suffixes_from_filters(filters)
        icon_size = 36 if size == "hero" else 28 if size == "comfortable" else 22

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 28)
        root.setSpacing(10)
        root.addStretch(1)

        self._icon_host = QWidget()
        self._icon_host.setObjectName("psi6DropZoneIcon")
        self._icon_host.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._icon_host.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._icon_host.setFixedSize(icon_size + 28, icon_size + 28)
        icon_layout = QVBoxLayout(self._icon_host)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        self._icon = Icon(icon, size=icon_size, tone="info")
        self._icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        icon_layout.addWidget(self._icon, alignment=Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._icon_host, alignment=Qt.AlignmentFlag.AlignHCenter)

        self._title = QLabel(title)
        self._title.setObjectName("psi6DropZoneTitle")
        self._title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._title.setWordWrap(True)
        self._title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        root.addWidget(self._title)

        self._hint = QLabel(hint)
        self._hint.setObjectName("psi6DropZoneHint")
        self._hint.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._hint.setWordWrap(True)
        self._hint.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        root.addWidget(self._hint)
        if not hint:
            self._hint.hide()

        self._badge = Tag(badge or "点击选择", tone="info", checkable=False)
        self._badge.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._badge.setCursor(Qt.CursorShape.ArrowCursor)
        root.addWidget(self._badge, alignment=Qt.AlignmentFlag.AlignHCenter)

        root.addStretch(1)
        if mode == "folder":
            picker: FileInput | FolderInput = FolderInput(allow_empty=True, parent=self)
        else:
            picker = FileInput(
                filters=filters,
                multiple=mode == "files",
                allow_empty=True,
                parent=self,
            )
        picker.hide()
        picker.path_changed.connect(self._on_picked)
        self._picker = picker
        self._set_flag("dropHover", False)
        self._set_flag("pressed", False)

    def set_copy(self, title: str, hint: str = "", *, badge: str | None = None) -> None:
        """更新标题与说明。空 ``badge`` 隐藏角标。"""

        self._title.setText(title)
        self.setAccessibleName(title)
        self._hint.setText(hint)
        if hint:
            self._hint.show()
        else:
            self._hint.hide()
        if badge is not None:
            text = badge.strip()
            self._badge.setText(text)
            self._badge.setVisible(bool(text))

    def ingest(self, paths: Sequence[Path | str]) -> None:
        """程序化送入路径（测试或粘贴）。只发出通过过滤的项。"""

        accepted: list[Path] = []
        for raw in paths:
            normalized = self._normalize(Path(raw))
            if normalized is not None and normalized not in accepted:
                accepted.append(normalized)
        if accepted:
            self.files_dropped.emit(accepted)

    def browse(self) -> None:
        """打开与 ``filters`` / ``mode`` 对应的系统对话框。"""

        self._picker.browse()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if self._drop_paths(event.mimeData().urls()):
            event.acceptProposedAction()
            self._set_flag("dropHover", True)
            return
        event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if self._drop_paths(event.mimeData().urls()):
            event.acceptProposedAction()
            return
        event.ignore()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        del event
        self._set_flag("dropHover", False)

    def dropEvent(self, event: QDropEvent) -> None:
        self._set_flag("dropHover", False)
        paths = self._drop_paths(event.mimeData().urls())
        if not paths:
            event.ignore()
            return
        event.acceptProposedAction()
        self.ingest(paths)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._set_flag("pressed", True)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._set_flag("pressed", False)
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit()
            if self._browse_on_click:
                self.browse()
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:  # noqa: ANN001
        if event.key() in {Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space}:
            self.clicked.emit()
            if self._browse_on_click:
                self.browse()
            return
        super().keyPressEvent(event)

    def _on_picked(self, _value: object) -> None:
        paths = self._picker.paths()
        if paths:
            self.ingest(paths)

    def _drop_paths(self, urls: Sequence) -> list[Path]:
        paths: list[Path] = []
        for url in urls:
            if not url.isLocalFile():
                continue
            text = url.toLocalFile()
            if text:
                paths.append(Path(text))
        return [path for path in paths if self._normalize(path) is not None]

    def _normalize(self, path: Path) -> Path | None:
        if self._mode == "folder":
            if path.is_dir():
                return path
            if path.is_file() and path.parent.is_dir():
                return path.parent
            if not path.suffix:
                return path
            return None
        if self._suffixes and path.suffix.lower().lstrip(".") not in self._suffixes:
            return None
        if path.is_dir():
            return None
        return path

    def _set_flag(self, name: str, value: bool) -> None:
        self.setProperty(name, value)
        style = self.style()
        style.unpolish(self)
        style.polish(self)
        self.update()


def _suffixes_from_filters(filters: str) -> set[str]:
    """从 ``Python (*.py *.pyw);;All (*)`` 抽出小写后缀。含 ``*`` 且无具体后缀则不过滤。"""

    found = {match.group(1).lower() for match in re.finditer(r"\*\.([A-Za-z0-9]+)", filters)}
    return found
