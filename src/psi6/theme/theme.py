"""用 Python 类定义主题。色和尺寸走 ``Tokens`` 字段名，图标目录相对主题模块文件。"""

from __future__ import annotations

import inspect
import sys
from dataclasses import fields, replace
from pathlib import Path
from typing import Any, ClassVar

from psi6.theme.tokens import Tokens

_TOKEN_NAMES = {item.name for item in fields(Tokens)}
_META = {"name", "base"}


class Theme:
    """可导入的主题。

    子类把 token 写成类属性，名字必须是 ``Tokens`` 的字段（IDE 能补全、写错会在加载时抛错）。
    ``base`` 取 ``light`` 或 ``dark``。``icon_dir`` 为相对路径时，相对**定义该类的模块文件**，
    不相对进程当前工作目录。未写 ``icon_dir`` 时，若模块旁边有含 ``*.svg`` 的 ``icons/``，则采用它。
    """

    name: ClassVar[str] = "custom"
    base: ClassVar[str] = "light"

    def tokens(self) -> Tokens:
        """展开为可套用的 ``Tokens``。未知字段、错误的 ``base``、缺失的显式图标目录会抛错。"""

        base_name = str(self.base).strip().lower()
        if base_name not in {"light", "dark"}:
            raise ValueError(f"主题 base 只能是 light 或 dark，收到 {self.base!r}")
        base = Tokens.dark() if base_name == "dark" else Tokens.light()
        updates = dict(_class_overrides(type(self)))
        icon = _icon_directory(type(self), updates.pop("icon_dir", None))
        tokens = base.overlay(updates) if updates else base
        if icon is None:
            return tokens
        return replace(tokens, icon_dir=str(icon))


def _class_overrides(cls: type[Theme]) -> dict[str, Any]:
    found: dict[str, Any] = {}
    unknown: list[str] = []
    for klass in reversed(cls.__mro__):
        if klass is Theme or klass is object:
            continue
        for key, value in vars(klass).items():
            if key.startswith("_") or key in _META or callable(value):
                continue
            if key not in _TOKEN_NAMES:
                unknown.append(f"{klass.__name__}.{key}")
            else:
                found[key] = value
    if unknown:
        known = ", ".join(sorted(_TOKEN_NAMES))
        raise TypeError(f"未知 token：{', '.join(unknown)}。可用字段：{known}")
    return found


def _module_dir(cls: type) -> Path:
    """主题类所在模块的目录。用模块 ``__file__``，不看进程工作目录。"""

    module = sys.modules.get(cls.__module__)
    file = getattr(module, "__file__", None) if module is not None else None
    if not file:
        file = inspect.getfile(cls)
    return Path(file).resolve().parent


def _icon_directory(cls: type, explicit: Any) -> Path | None:
    if explicit not in (None, ""):
        path = Path(str(explicit)).expanduser()
        if not path.is_absolute():
            path = _module_dir(cls) / path
        path = path.resolve()
        if not path.is_dir():
            raise FileNotFoundError(f"主题图标目录不存在：{path}")
        return path
    folder = (_module_dir(cls) / "icons").resolve()
    if folder.is_dir() and any(folder.glob("*.svg")):
        return folder
    return None
