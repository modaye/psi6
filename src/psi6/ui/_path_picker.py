"""路径选择行：单文件 / 多文件 / 目录共用实现。"""

from __future__ import annotations

import contextlib
from collections.abc import Sequence
from enum import StrEnum
from pathlib import Path
from typing import Literal

from PySide6.QtCore import QEvent, QObject, QRunnable, QThreadPool, QTimer, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QWidget,
)

Mode = Literal["file", "files", "folder"]


class _ProbeSignals(QObject):
    checked = Signal(int, bool)


class _PathProbe(QRunnable):
    """在工作线程里查路径，避免网络路径卡住输入。"""

    def __init__(
        self,
        signals: _ProbeSignals,
        token: int,
        paths: list[Path],
        mode: Mode,
    ) -> None:
        super().__init__()
        self._signals = signals
        self._token = token
        self._paths = paths
        self._mode = mode

    def run(self) -> None:
        try:
            exists = _paths_exist(self._paths, self._mode)
        except OSError:
            exists = False
        with contextlib.suppress(RuntimeError):
            self._signals.checked.emit(self._token, exists)


def _paths_exist(paths: list[Path], mode: Mode) -> bool:
    if mode == "folder":
        return all(path.is_dir() for path in paths)
    return all(path.is_file() for path in paths)


class PathState(StrEnum):
    """路径输入的可见状态。"""

    EMPTY = "empty"
    SELECTED = "selected"
    INVALID = "invalid"


class PathPicker(QWidget):
    """可编辑路径 + 浏览按钮，支持拖放。

    多个路径在输入框里用分号 ``;`` 拼接。通过选择、拖放或 ``set_paths`` 得到的
    路径会原样记住，文件名里的分号不会被拆开；手动输入时仍以分号分隔。
    ``path_changed`` 随每次按键发出，适合即时校验。``path_edited`` 在输入结束、
    浏览、拖放或点清除之后发出，适合保存。
    """

    path_changed = Signal(object)
    path_edited = Signal(object)

    def __init__(
        self,
        *,
        mode: Mode,
        filters: str = "All Files (*)",
        allow_empty: bool = False,
        clearable: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("psi6PathPicker")
        self._mode: Mode = mode
        self._filters = filters
        self._allow_empty = allow_empty
        self._cached_paths: list[Path] | None = None
        self._cached_text = ""
        self._setting_text = False
        self._probe_token = 0
        self._probe_signals = _ProbeSignals(self)
        self._probe_signals.checked.connect(self._apply_probe)
        self.setAcceptDrops(True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self._edit = QLineEdit()
        self._edit.setPlaceholderText(self._placeholder())
        self._edit.setClearButtonEnabled(clearable)
        if clearable:
            for action in self._edit.actions():
                action.triggered.connect(self._emit_edited)
        self._edit.textChanged.connect(self._on_text_changed)
        self._edit.editingFinished.connect(self._emit_edited)
        self._edit.installEventFilter(self)
        # 路径存在性检查会访问磁盘，输入停顿后交给线程池，避免网络路径卡住界面。
        self._validate_timer = QTimer(self)
        self._validate_timer.setSingleShot(True)
        self._validate_timer.setInterval(150)
        self._validate_timer.timeout.connect(self._refresh_valid)
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
        self._emit_edited()
        event.acceptProposedAction()

    def _placeholder(self) -> str:
        if self._mode == "folder":
            return "选择目录"
        if self._mode == "files":
            return "选择一个或多个文件"
        return "选择文件"

    def _on_text_changed(self, _text: str) -> None:
        if not self._setting_text:
            self._cached_paths = None
            self._cached_text = ""
        self.path_changed.emit(self.path())
        self._validate_timer.start()

    def _emit_edited(self) -> None:
        self._validate_timer.stop()
        self._refresh_valid()
        self.path_edited.emit(self.path())

    def _refresh_valid(self) -> None:
        paths = self.paths()
        if not paths:
            self._set_invalid(False)
            return
        self._probe_token += 1
        QThreadPool.globalInstance().start(
            _PathProbe(self._probe_signals, self._probe_token, paths, self._mode)
        )

    def _apply_probe(self, token: int, exists: bool) -> None:
        if token != self._probe_token:
            return
        self._set_invalid(not exists)

    def _set_invalid(self, invalid: bool) -> None:
        if self.property("invalid") is invalid:
            return
        self.setProperty("invalid", invalid)
        self.style().unpolish(self)
        self.style().polish(self)

    def browse(self) -> None:
        """弹出系统对话框。``DropZone`` / ``ImageWell`` 的选择按钮走这里。"""

        start = self._edit.text().strip()
        if self._mode == "folder":
            chosen = QFileDialog.getExistingDirectory(self, "选择目录", start)
            if not chosen:
                return
            self.set_path(chosen)
        elif self._mode == "files":
            paths, _ = QFileDialog.getOpenFileNames(self, "选择文件", start, self._filters)
            if not paths:
                return
            self.set_paths(paths)
        else:
            path, _ = QFileDialog.getOpenFileName(self, "选择文件", start, self._filters)
            if not path:
                return
            self.set_path(path)
        self._emit_edited()

    def _browse(self) -> None:
        self.browse()

    def path(self) -> Path | None:
        paths = self.paths()
        return paths[0] if paths else None

    def paths(self) -> list[Path]:
        """按分号拆开当前文本。选择或拖放得到的路径按原样返回。"""

        text = self._edit.text().strip()
        if not text:
            return []
        if self._cached_paths is not None and text == self._cached_text:
            return list(self._cached_paths)
        return [Path(part.strip()) for part in text.split(";") if part.strip()]

    def set_path(self, path: Path | str | None) -> None:
        if path is None:
            self._set_text("", [])
            return
        self._set_text(str(path), [Path(path)])

    def set_paths(self, paths: Sequence[Path | str]) -> None:
        items = [Path(path) for path in paths]
        self._set_text("; ".join(str(path) for path in items), items)

    def _set_text(self, text: str, paths: list[Path]) -> None:
        self._cached_paths = paths
        self._cached_text = text.strip()
        self._setting_text = True
        try:
            self._edit.setText(text)
        finally:
            self._setting_text = False

    @property
    def state(self) -> PathState:
        paths = self.paths()
        if not paths:
            return PathState.EMPTY
        if _paths_exist(paths, self._mode):
            return PathState.SELECTED
        return PathState.INVALID

    def is_valid(self) -> bool:
        state = self.state
        return state is PathState.SELECTED or (state is PathState.EMPTY and self._allow_empty)
