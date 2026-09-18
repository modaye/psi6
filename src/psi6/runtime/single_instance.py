"""进程互斥：第二份实例唤醒第一份，而不是再开一个窗口。"""

from __future__ import annotations

import re

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket


def instance_key(organization: str, name: str) -> str:
    """QLocalServer 名称：只保留字母数字与连字符。"""

    raw = f"psi6-{organization}-{name}"
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "-", raw)
    return cleaned[:120]


class SingleInstance(QObject):
    """本机 socket 锁。``try_acquire`` 失败说明已有实例在听。"""

    activated = Signal()

    def __init__(self, key: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._key = key
        self._server: QLocalServer | None = None

    @property
    def key(self) -> str:
        return self._key

    def try_acquire(self) -> bool:
        """成为唯一实例则返回 True；已有实例则返回 False。"""

        if self._is_alive():
            return False
        QLocalServer.removeServer(self._key)
        server = QLocalServer(self)
        server.newConnection.connect(self._on_connection)
        if not server.listen(self._key):
            return False
        self._server = server
        return True

    def notify_existing(self, payload: bytes = b"activate") -> bool:
        """通知已运行实例把窗口提到前台。"""

        socket = QLocalSocket(self)
        socket.connectToServer(self._key)
        if not socket.waitForConnected(200):
            return False
        socket.write(payload)
        socket.flush()
        socket.waitForBytesWritten(200)
        socket.disconnectFromServer()
        return True

    def close(self) -> None:
        if self._server is not None:
            self._server.close()
            QLocalServer.removeServer(self._key)
            self._server = None

    def _is_alive(self) -> bool:
        socket = QLocalSocket(self)
        socket.connectToServer(self._key)
        ok = socket.waitForConnected(150)
        if ok:
            socket.disconnectFromServer()
        return ok

    def _on_connection(self) -> None:
        if self._server is None:
            return
        socket = self._server.nextPendingConnection()
        if socket is not None:
            socket.readyRead.connect(socket.readAll)
            socket.disconnected.connect(socket.deleteLater)
        self.activated.emit()
