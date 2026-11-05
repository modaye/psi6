"""一个窗口上一套快捷键。同一序列只登记一条命令。

右键菜单里的 ``shortcut`` 只负责把键显示出来。真正响应按键的地方是这里：
同一动作可以出现在表格、树和页签里，但键只在窗口上登记一次，不会互相覆盖。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QWidget

__all__ = ["ShortcutBook"]


@dataclass
class _Binding:
    shortcut: QShortcut
    canonical: str
    callback: Callable[[], Any]


class ShortcutBook:
    """挂在一个窗口上的快捷键表。

    默认只在这个窗口处于前台时生效，不会抢其它窗口的键。同一 ``command_id``
    再次 ``bind`` 会换掉原来的键和回调；把同一序列绑到另一条命令上会抛错，
    避免静默覆盖。空序列表示取消这条命令的键。
    """

    def __init__(self, host: QWidget) -> None:
        if host is None:
            raise ValueError("快捷键必须挂在窗口或页面上")
        self.host = host
        self._by_id: dict[str, _Binding] = {}
        self._by_key: dict[str, str] = {}

    def bind(self, command_id: str, sequence: str, callback: Callable[[], Any]) -> None:
        """登记或替换一条命令。``callback`` 不接收参数。"""

        command_id = str(command_id).strip()
        sequence = str(sequence).strip()
        if not command_id:
            raise ValueError("command_id 不能为空")
        if callback is None:
            raise ValueError("callback 不能为空")
        self.unbind(command_id)
        if not sequence:
            return
        key = QKeySequence(sequence)
        canonical = key.toString(QKeySequence.SequenceFormat.PortableText)
        # ``isEmpty()`` 对无法解析的字符串也会返回假，空的可移植写法才是认不出来。
        if key.isEmpty() or not canonical:
            raise ValueError(f"无法识别的快捷键：{sequence}")
        owner = self._by_key.get(canonical)
        if owner is not None and owner != command_id:
            raise ValueError(f"快捷键 {sequence} 已经绑在 {owner} 上")
        shortcut = QShortcut(key, self.host)
        shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        shortcut.setAutoRepeat(False)
        shortcut.activated.connect(lambda cid=command_id: self._invoke(cid))
        self._by_id[command_id] = _Binding(shortcut, canonical, callback)
        self._by_key[canonical] = command_id

    def unbind(self, command_id: str) -> None:
        """去掉一条命令。没有登记过就什么也不做。"""

        binding = self._by_id.pop(str(command_id).strip(), None)
        if binding is None:
            return
        self._by_key.pop(binding.canonical, None)
        binding.shortcut.setEnabled(False)
        binding.shortcut.deleteLater()

    def sequence_for(self, command_id: str) -> str:
        """这条命令当前的键，没有则是空串。格式与 ``QKeySequence`` 的可移植写法一致。"""

        binding = self._by_id.get(str(command_id).strip())
        return "" if binding is None else binding.canonical

    def clear(self) -> None:
        """去掉这本表上的全部键。"""

        for command_id in list(self._by_id):
            self.unbind(command_id)

    def _invoke(self, command_id: str) -> None:
        binding = self._by_id.get(command_id)
        if binding is not None:
            binding.callback()
