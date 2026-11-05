"""进程互斥：第二份实例唤醒第一份，而不是再开一个窗口。"""

from __future__ import annotations

import re

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

ACTIVATE = b"psi6-activate-v1"
_MAX_PAYLOAD = 256


def instance_key(organization: str, name: str) -> str:
    """QLocalServer 名称：只保留字母数字与连字符。"""

    raw = f"psi6-{organization}-{name}"
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "-", raw)
    return cleaned[:120]


class SingleInstance(QObject):
    """本机 socket 锁。``try_acquire`` 失败说明已有实例在听。

    唤醒消息必须和构造时的 ``payload`` 完全一致，随机连上来的本地进程
    不会把窗口提到前台。
    """

    activated = Signal()

    def __init__(
        self,
        key: str,
        parent: QObject | None = None,
        *,
        payload: bytes = ACTIVATE,
    ) -> None:
        super().__init__(parent)
        if not payload or len(payload) > _MAX_PAYLOAD:
            raise ValueError(f"payload 长度必须在 1 到 {_MAX_PAYLOAD} 字节之间")
        self._key = key
        self._payload = bytes(payload)
        self._server: QLocalServer | None = None

    @property
    def key(self) -> str:
        return self._key

    def try_acquire(self) -> bool:
        """成为唯一实例则返回 True；已有实例则返回 False。

        先探测已有实例（Windows 命名管道允许同名服务对象并存，必须先探测）。
        只有 ``listen`` 失败、且再次探测确认没有活着的实例时，才清理残留
        socket 并重试，避免两个进程同时启动时删掉对方的锁。
        """

        if self._is_alive():
            return False
        server = QLocalServer(self)
        server.newConnection.connect(self._on_connection)
        if server.listen(self._key):
            self._server = server
            return True
        if self._is_alive():
            server.deleteLater()
            return False
        QLocalServer.removeServer(self._key)
        if not server.listen(self._key):
            server.deleteLater()
            return False
        self._server = server
        return True

    def notify_existing(self, payload: bytes | None = None) -> bool:
        """通知已运行实例把窗口提到前台。默认发送构造时约定的唤醒消息。"""

        data = self._payload if payload is None else bytes(payload)
        if not data or len(data) > _MAX_PAYLOAD:
            raise ValueError(f"payload 长度必须在 1 到 {_MAX_PAYLOAD} 字节之间")
        socket = QLocalSocket(self)
        socket.connectToServer(self._key)
        if not socket.waitForConnected(200):
            return False
        socket.write(data)
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
            socket.abort()
        return ok

    def _on_connection(self) -> None:
        if self._server is None:
            return
        while (socket := self._server.nextPendingConnection()) is not None:
            socket.readyRead.connect(self._read_sender)
            socket.disconnected.connect(socket.deleteLater)
            self._read_activation(socket)

    def _read_sender(self) -> None:
        socket = self.sender()
        if isinstance(socket, QLocalSocket):
            self._read_activation(socket)

    def _read_activation(self, socket: QLocalSocket) -> None:
        if socket.property("psi6Accepted"):
            return
        buffer = bytearray(socket.property("psi6Payload") or b"")
        room = _MAX_PAYLOAD + 1 - len(buffer)
        if room > 0:
            buffer.extend(socket.read(room).data())
        if len(buffer) > _MAX_PAYLOAD:
            socket.setProperty("psi6Payload", b"")
            socket.abort()
            return
        socket.setProperty("psi6Payload", bytes(buffer))
        if bytes(buffer) != self._payload:
            return
        socket.setProperty("psi6Accepted", True)
        self.activated.emit()
