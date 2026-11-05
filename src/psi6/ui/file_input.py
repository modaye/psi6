"""文件与目录输入控件。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QWidget

from psi6.ui._path_picker import PathPicker, PathState

__all__ = ["FileInput", "FolderInput", "PathState"]


class _PathInput(QWidget):
    """把 ``PathPicker`` 包成公开控件，转发信号与读写方法。"""

    path_changed = Signal(object)
    path_edited = Signal(object)

    def __init__(self, picker: PathPicker, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._picker = picker
        self._picker.path_changed.connect(self.path_changed.emit)
        self._picker.path_edited.connect(self.path_edited.emit)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._picker)

    def path(self) -> Path | None:
        return self._picker.path()

    def paths(self) -> list[Path]:
        return self._picker.paths()

    def set_path(self, path: Path | str | None) -> None:
        self._picker.set_path(path)

    def set_paths(self, paths: list[Path | str]) -> None:
        self._picker.set_paths(paths)

    def is_valid(self) -> bool:
        return self._picker.is_valid()

    def browse(self) -> None:
        """打开系统选择对话框。首页大热区请用 ``DropZone``。"""

        self._picker.browse()

    @property
    def state(self) -> PathState:
        return self._picker.state


class FileInput(_PathInput):
    """选择一个或多个本地文件，并校验路径是否存在。

    多个文件在输入框里用分号分隔。``path_changed`` 每次按键都发出；
    ``path_edited`` 在编辑结束、浏览、拖放或清除后发出。
    """

    def __init__(
        self,
        *,
        filters: str = "All Files (*)",
        multiple: bool = False,
        allow_empty: bool = False,
        clearable: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            PathPicker(
                mode="files" if multiple else "file",
                filters=filters,
                allow_empty=allow_empty,
                clearable=clearable,
            ),
            parent,
        )


class FolderInput(_PathInput):
    """选择本地目录。信号含义与 ``FileInput`` 相同。"""

    def __init__(
        self,
        *,
        allow_empty: bool = False,
        clearable: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            PathPicker(mode="folder", allow_empty=allow_empty, clearable=clearable), parent
        )
