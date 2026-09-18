"""播放队列：曲目表 + 当前行标记。解码仍在业务层。"""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QVBoxLayout, QWidget

from psi6.ui.data_table import DataTable, TableColumn


class Playlist(QWidget):
    """曲目表。``track_activated`` 给出原始曲目下标。"""

    track_activated = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("psi6Playlist")
        self._tracks: list[dict[str, str]] = []
        self._current = -1
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        self._table = DataTable(
            [
                TableColumn("title", "曲目", stretch=True),
                TableColumn("artist", "艺人"),
                TableColumn("time", "时长"),
            ],
        )
        self._table.row_activated.connect(self._activate_visible)
        self._table.selection_changed.connect(self._on_select)
        root.addWidget(self._table)

    def set_tracks(self, rows: Sequence[dict[str, str]]) -> None:
        self._tracks = [dict(row) for row in rows]
        self._render()

    def set_current(self, index: int) -> None:
        self._current = index
        self._render()

    def current_index(self) -> int:
        return self._current

    def set_filter(self, query: str) -> None:
        self._table.set_filter(query)

    def _render(self) -> None:
        self._table.blockSignals(True)
        self._table.set_rows(self._tracks)
        if 0 <= self._current < len(self._tracks):
            self._table.select_row(self._current)
        self._table.blockSignals(False)

    def _on_select(self) -> None:
        rows = self._table.selected_rows()
        if not rows:
            return
        title = rows[0].get("title")
        artist = rows[0].get("artist")
        for index, track in enumerate(self._tracks):
            if track.get("title") == title and track.get("artist") == artist:
                if index != self._current:
                    self.set_current(index)
                    self.track_activated.emit(index)
                return

    def _activate_visible(self, visible_index: int) -> None:
        visible = self._table.visible_rows()
        if not (0 <= visible_index < len(visible)):
            return
        row = visible[visible_index]
        for index, track in enumerate(self._tracks):
            if track.get("title") == row.get("title") and track.get("artist") == row.get("artist"):
                self.set_current(index)
                self.track_activated.emit(index)
                return
