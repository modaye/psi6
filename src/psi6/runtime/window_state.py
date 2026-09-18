"""主窗口位置与最大化状态。存在 ``window.json``，与业务 ``config.json`` 分开。"""

from __future__ import annotations

from PySide6.QtCore import QByteArray
from PySide6.QtWidgets import QWidget

from psi6.runtime.config import ConfigStore

_FILE = "window.json"


def save_window(window: QWidget, store: ConfigStore, app_name: str) -> None:
    """把 ``saveGeometry`` 写到用户目录。"""

    blob = bytes(window.saveGeometry().toBase64()).decode("ascii")
    store.save_data(
        app_name,
        _FILE,
        {"geometry": blob, "maximized": bool(window.isMaximized())},
    )


def restore_window(window: QWidget, store: ConfigStore, app_name: str) -> bool:
    """恢复上次几何。无边框窗 ``restoreGeometry`` 常常丢最大化，所以另存一份标志。"""

    payload = store.load_data(app_name, _FILE)
    if not payload:
        return False
    blob = payload.get("geometry")
    if not isinstance(blob, str) or not blob:
        return False
    restored = bool(window.restoreGeometry(QByteArray.fromBase64(blob.encode("ascii"))))
    if restored and payload.get("maximized") and not window.isMaximized():
        window.showMaximized()
    return restored
