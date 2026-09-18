"""路径选择行：单文件 / 多文件 / 目录共用实现。"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Literal

from PySide6.QtCore import QEvent, QObject, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QWidget,
)

Mode = Literal["file", "files", "folder"]


class PathState(StrEnum):
    """路径输入的可见状态。"""

    EMPTY = "empty"
    SELECTED = "selected"
    INVALID = "invalid"


class PathPicker(QWidget):
    """可编辑路径 + 浏览按钮，支持拖放。"""

    path_changed = Signal(object)

    def __init__(
        self,
        *,
        mode: Mode,
        filters: str = "All Files (*)",
        allow_empty: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("psi6PathPicker")
        self._mode: Mode = mode
        self._filters = filters
        self._allow_empty = allow_empty
        self.setAcceptDrops(True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self._edit = QLineEdit()
        self._edit.setPlaceholderText(self._placeholder())
        self._edit.textChanged.connect(self._on_text_changed)
        self._edit.installEventFilter(self)
        browse = QPushButton("浏览…")
        browse.setFixedWidth(72)
        browse.clicked.connect(self._browse)
        layout.addWidget(self._edit, stretch=1)
        layout.addWidget(browse)
        self._refresh_valid()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self._edit:
            if event.type() == QEvent.Type.DragEnter and isinstance(event, QDragEnterEvent):
                self.dragEnterEvent(event)
                return True
            if event.type() == QEvent.Type.Drop and isinstance(event, QDropEvent):
                self.dropEvent(event)
                return True
        return super().eventFilter(watched, event)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        paths = [
            Path(url.toLocalFile())
            for url in event.mimeData().urls()
            if url.isLocalFile() and url.toLocalFile()
        ]
        if not paths:
            return
        if self._mode == "folder":
            first = paths[0]
            self.set_path(first if first.is_dir() else first.parent)
        elif self._mode == "files":
            files = [path for path in paths if path.is_file()]
            if files:
                self.set_paths(files)
        else:
            file = next((path for path in paths if path.is_file()), None)
            if file is not None:
                self.set_path(file)
        event.acceptProposedAction()

    def _placeholder(self) -> str:
        if self._mode == "folder":
            return "选择目录"
        if self._mode == "files":
            return "选择一个或多个文件"
        return "选择文件"

    def _on_text_changed(self, _text: str) -> None:
        self._refresh_valid()
        self.path_changed.emit(self.path())

    def _refresh_valid(self) -> None:
        invalid = self.state is PathState.INVALID
        self.setProperty("invalid", invalid)
        self.style().unpolish(self)
        self.style().polish(self)

    def browse(self) -> None:
        """弹出系统对话框。``DropZone`` / ``ImageWell`` 的选择按钮走这里。"""

        start = self._edit.text().strip()
        if self._mode == "folder":
            chosen = QFileDialog.getExistingDirectory(self, "选择目录", start)
            if chosen:
                self.set_path(chosen)
            return
        if self._mode == "files":
            paths, _ = QFileDialog.getOpenFileNames(self, "选择文件", start, self._filters)
            if paths:
                self.set_paths(paths)
            return
        path, _ = QFileDialog.getOpenFileName(self, "选择文件", start, self._filters)
        if path:
            self.set_path(path)

    def _browse(self) -> None:
        self.browse()

    def path(self) -> Path | None:
        paths = self.paths()
        return paths[0] if paths else None

    def paths(self) -> list[Path]:
        text = self._edit.text().strip()
        if not text:
            return []
        return [Path(part.strip()) for part in text.split(";") if part.strip()]

    def set_path(self, path: Path | str | None) -> None:
        self._edit.setText("" if path is None else str(path))

    def set_paths(self, paths: list[Path | str]) -> None:
        self._edit.setText("; ".join(str(p) for p in paths))

    @property
    def state(self) -> PathState:
        paths = self.paths()
        if not paths:
            return PathState.EMPTY
        if self._paths_exist(paths):
            return PathState.SELECTED
        return PathState.INVALID

    def is_valid(self) -> bool:
        if self.state is PathState.EMPTY:
            return self._allow_empty
        return self.state is PathState.SELECTED

    def _paths_exist(self, paths: list[Path]) -> bool:
        if self._mode == "folder":
            return all(path.is_dir() for path in paths)
        return all(path.is_file() for path in paths)
