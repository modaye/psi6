"""Qt 启动环境：字体目录、应用字体、噪音日志过滤。

PySide6 不再随包提供 ``lib/fonts``。必须在 ``QApplication`` 之前把
``QT_QPA_FONTDIR`` 指到系统字体目录，否则 offscreen 会刷
``QFontDatabase: Cannot find font directory``。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_FILTER_SNIPPETS = (
    "Cannot find font directory",
    "propagateSizeHints",
    "FT_New_Face",
    "setting window masks",
)
_handler_installed = False
_fonts_installed = False


def detect_font_dir() -> Path | None:
    """系统字体目录。Windows 优先 ``%WINDIR%\\Fonts``。"""

    windir = os.environ.get("WINDIR")
    if windir:
        windows_fonts = Path(windir) / "Fonts"
        if windows_fonts.is_dir():
            return windows_fonts
    for candidate in (
        Path("/usr/share/fonts"),
        Path("/usr/local/share/fonts"),
        Path.home() / ".fonts",
        Path("/Library/Fonts"),
        Path("/System/Library/Fonts"),
    ):
        if candidate.is_dir():
            return candidate
    return None


def prepare_qt_environment() -> Path | None:
    """必须在创建 ``QApplication`` 之前调用。设置 ``QT_QPA_FONTDIR``。"""

    if os.environ.get("QT_QPA_FONTDIR"):
        path = Path(os.environ["QT_QPA_FONTDIR"])
        return path if path.is_dir() else None
    found = detect_font_dir()
    if found is not None:
        os.environ["QT_QPA_FONTDIR"] = str(found)
    return found


def install_qt_message_filter() -> None:
    """丢掉 offscreen 插件的 ``propagateSizeHints`` 与缺字体目录噪音。"""

    global _handler_installed
    if _handler_installed:
        return
    from PySide6.QtCore import qInstallMessageHandler

    def handler(mode, context, message: str) -> None:  # noqa: ANN001
        del mode, context
        if any(snippet in message for snippet in _FILTER_SNIPPETS):
            return
        sys.stderr.write(message + "\n")

    qInstallMessageHandler(handler)
    _handler_installed = True


def install_app_fonts() -> list[str]:
    """在 ``QApplication`` 之后把系统 UI 字体登记进 ``QFontDatabase``。"""

    global _fonts_installed
    from PySide6.QtGui import QFontDatabase

    if _fonts_installed:
        return []
    loaded: list[str] = []
    root = detect_font_dir()
    if root is None:
        _fonts_installed = True
        return loaded
    names = (
        "segoeui.ttf",
        "segoeuib.ttf",
        "msyh.ttf",
        "msyhl.ttf",
        "consola.ttf",
        "CascadiaMono.ttf",
        "DejaVuSans.ttf",
    )
    for name in names:
        path = root / name
        if not path.is_file():
            continue
        font_id = QFontDatabase.addApplicationFont(str(path))
        if font_id != -1:
            loaded.extend(QFontDatabase.applicationFontFamilies(font_id))
    _fonts_installed = True
    return loaded
