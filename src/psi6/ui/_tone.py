"""把动态 ``tone`` 属性刷进 QSS。"""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from psi6.ui.tone import Tone, normalize_tone


def set_tone(widget: QWidget, tone: str) -> Tone:
    """写入 ``tone`` 属性并强制样式刷新。"""

    resolved = normalize_tone(tone)
    widget.setProperty("tone", resolved)
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()
    return resolved
