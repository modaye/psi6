"""播放控制条：影视 / 音乐共用，不内置解码器。"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSlider, QWidget

from psi6.ui.icon import IconButton


class TransportBar(QWidget):
    """上一首 / 播放暂停 / 下一首 / 进度 / 静音 / 音量。"""

    play_toggled = Signal(bool)
    previous_requested = Signal()
    next_requested = Signal()
    seeked = Signal(int)
    volume_changed = Signal(int)
    muted = Signal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("psi6Transport")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._playing = False
        self._muted = False
        self._last_volume = 80
        row = QHBoxLayout(self)
        row.setContentsMargins(10, 8, 10, 8)
        row.setSpacing(6)
        prev_btn = IconButton("skip-back", label="上一首", size=18)
        prev_btn.clicked.connect(self.previous_requested.emit)
        self._play = IconButton("play", label="播放", size=18)
        self._play.clicked.connect(self._toggle)
        next_btn = IconButton("skip-forward", label="下一首", size=18)
        next_btn.clicked.connect(self.next_requested.emit)
        row.addWidget(prev_btn)
        row.addWidget(self._play)
        row.addWidget(next_btn)
        self._time = QLabel("0:00 / 0:00")
        self._time.setObjectName("psi6Hint")
        row.addWidget(self._time)
        self._seek = QSlider(Qt.Orientation.Horizontal)
        self._seek.setRange(0, 1000)
        self._seek.sliderReleased.connect(lambda: self.seeked.emit(self._seek.value()))
        row.addWidget(self._seek, stretch=1)
        self._mute = IconButton("volume", label="静音", size=18)
        self._mute.clicked.connect(self._toggle_mute)
        row.addWidget(self._mute)
        self._volume = QSlider(Qt.Orientation.Horizontal)
        self._volume.setRange(0, 100)
        self._volume.setValue(80)
        self._volume.setFixedWidth(88)
        self._volume.valueChanged.connect(self._on_volume)
        row.addWidget(self._volume)

    def set_playing(self, playing: bool) -> None:
        self._playing = playing
        self._play.set_name("pause" if playing else "play")
        self._play.setToolTip("暂停" if playing else "播放")
        self._play.setAccessibleName(self._play.toolTip())

    def set_time(self, current: str, total: str) -> None:
        self._time.setText(f"{current} / {total}")

    def set_progress(self, value: int) -> None:
        self._seek.blockSignals(True)
        self._seek.setValue(max(0, min(1000, value)))
        self._seek.blockSignals(False)

    def set_volume(self, value: int) -> None:
        bounded = max(0, min(100, value))
        if not self._muted:
            self._last_volume = bounded or self._last_volume
        self._volume.blockSignals(True)
        self._volume.setValue(0 if self._muted else bounded)
        self._volume.blockSignals(False)

    def set_muted(self, muted: bool) -> None:
        self._muted = muted
        self._mute.set_name("volume-off" if muted else "volume")
        self._mute.setToolTip("取消静音" if muted else "静音")
        self._mute.setAccessibleName(self._mute.toolTip())
        self._volume.blockSignals(True)
        self._volume.setValue(0 if muted else self._last_volume)
        self._volume.blockSignals(False)

    def is_muted(self) -> bool:
        return self._muted

    def _toggle(self) -> None:
        self.set_playing(not self._playing)
        self.play_toggled.emit(self._playing)

    def _toggle_mute(self) -> None:
        self.set_muted(not self._muted)
        self.muted.emit(self._muted)
        self.volume_changed.emit(0 if self._muted else self._last_volume)

    def _on_volume(self, value: int) -> None:
        if value > 0 and self._muted:
            self._muted = False
            self._mute.set_name("volume")
            self._mute.setToolTip("静音")
            self._mute.setAccessibleName("静音")
            self.muted.emit(False)
        if value == 0 and not self._muted:
            self.set_muted(True)
            self.muted.emit(True)
        if value > 0:
            self._last_volume = value
        self.volume_changed.emit(value)
