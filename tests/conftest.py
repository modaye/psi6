"""pytest-qt 在无显示器环境下使用 offscreen，并先指定系统字体目录。"""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_windir = os.environ.get("WINDIR")
if _windir:
    _fonts = Path(_windir) / "Fonts"
    if _fonts.is_dir():
        os.environ.setdefault("QT_QPA_FONTDIR", str(_fonts))
