"""用 Python 类定义主题。色和尺寸走 ``Tokens`` 字段名，图标目录相对主题模块文件。"""

from __future__ import annotations

import inspect
import sys
from dataclasses import fields, replace
from pathlib import Path
from typing import Any, ClassVar

from psi6.theme.system import system_prefers_dark
from psi6.theme.tokens import Tokens, merge_style

_TOKEN_NAMES = {item.name for item in fields(Tokens)}
_META = {"name", "base", "style", "light", "dark"}


class Theme:
    """可导入的主题。

    子类把 token 写成类属性，名字必须是 ``Tokens`` 的字段（IDE 能补全、写错会在加载时抛错）。
    ``base`` 取 ``light``、``dark`` 或 ``auto``，只决定配色。``style`` 取 ``modern`` 或 ``compact``，只决定尺寸。
    ``auto`` 跟随系统浅色/深色：类上写了 ``light`` 与 ``dark`` 两个变体时，配色取当前方案那一份，
    本类显式写的 ``style`` 和 token 覆盖压在它上面；没写变体时，把本类的覆盖套到系统底色上。
    变体是 ``Theme`` 子类 / 实例或 ``Tokens``，自己的 ``base`` 不能再是 ``auto``。
    ``icon_dir`` 为相对路径时，相对**定义该类的模块文件**，
    不相对进程当前工作目录。未写 ``icon_dir`` 时，若模块旁边有含 ``*.svg`` 的 ``icons/``，则采用它。
    """

    name: ClassVar[str] = "custom"
    base: ClassVar[str] = "light"
    style: ClassVar[str] = "modern"
    light: ClassVar[Any] = None
    dark: ClassVar[Any] = None

    def tokens(self) -> Tokens:
        """展开为可套用的 ``Tokens``。未知字段、错误的 ``base`` / ``style``、缺失的显式图标目录会抛错。"""

        return self._compose().resolve_states()

    def _compose(self) -> Tokens:
        """合成但尚未补齐状态色的 token。auto 变体先叠加，再统一推导。"""

        cls = type(self)
        variant = _system_variant(cls)
        style_name = _resolve_style(cls, fallback=None if variant is not None else "modern")
        if variant is None:
            base = Tokens.dark() if _resolve_base(cls) == "dark" else Tokens.light()
        else:
            base = _unresolved_tokens(variant)
        updates = dict(_class_overrides(cls))
        icon = _icon_directory(cls, updates.pop("icon_dir", None))
        if style_name is None:
            tokens = base.overlay(updates)
        else:
            tokens = merge_style(base, style_name, updates)
        if icon is None:
            return tokens
        return replace(tokens, icon_dir=str(icon))


def follows_system(theme: str | Tokens | Theme | type[Theme]) -> bool:
    """这套主题会跟着系统浅色/深色变吗。``auto`` 字符串和 ``base = "auto"`` 的主题算跟随。"""

    if isinstance(theme, str):
        return theme.strip().lower() in {"auto", "system"}
    if isinstance(theme, type) and issubclass(theme, Theme):
        return _is_auto(theme)
    return _is_auto(theme) if isinstance(theme, Theme) else False


def theme_key(theme: str | Tokens | Theme | type[Theme]) -> str | None:
    """主题可以写进配置的标识。``Tokens`` 没有名字，返回 ``None``。"""

    if isinstance(theme, str):
        return theme.strip().lower() or None
    if isinstance(theme, type) and issubclass(theme, Theme):
        return str(theme.name).strip() or None
    if isinstance(theme, Theme):
        return str(theme.name).strip() or None
    return None


def _is_auto(cls: Theme | type[Theme]) -> bool:
    return str(cls.base).strip().lower() == "auto"


def _resolve_base(cls: type[Theme]) -> str:
    name = str(cls.base).strip().lower()
    if name == "auto":
        return "dark" if system_prefers_dark() else "light"
    if name not in {"light", "dark"}:
        raise ValueError(f"主题 base 只能是 light、dark 或 auto，收到 {cls.base!r}")
    return name


def _unresolved_tokens(variant: Any) -> Tokens:
    """变体自身的合成结果。状态色留给外层统一推导，避免覆盖主色后仍用旧推导值。"""

    if isinstance(variant, type) and issubclass(variant, Theme):
        variant = variant()
    if isinstance(variant, Theme):
        return variant._compose()
    return variant


def _system_variant(cls: type[Theme]) -> Any:
    """``base = "auto"`` 且声明了对应变体时返回变体，否则 ``None``。"""

    if not _is_auto(cls):
        return None
    attr = "dark" if system_prefers_dark() else "light"
    variant = _declared(cls, attr)
    if variant is None:
        return None
    _check_variant(cls, attr, variant)
    return variant


def _check_variant(cls: type[Theme], attr: str, variant: Any) -> None:
    if isinstance(variant, Tokens):
        return
    theme = variant if isinstance(variant, type) and issubclass(variant, Theme) else None
    if theme is None and isinstance(variant, Theme):
        theme = type(variant)
    if theme is None:
        raise TypeError(
            f"主题变体 {cls.__name__}.{attr} 只能是 Theme 子类、实例或 Tokens，收到 {variant!r}"
        )
    if _is_auto(theme):
        raise ValueError(f"主题变体 {cls.__name__}.{attr} 的 base 不能再是 auto")


def _declared(cls: type[Theme], name: str) -> Any:
    """子类显式写出的元数据。没写则返回 ``None``，不把基类默认值当成用户选择。"""

    for klass in cls.__mro__:
        if klass is Theme or klass is object:
            continue
        if name in vars(klass):
            return vars(klass)[name]
    return None


def _resolve_style(cls: type[Theme], *, fallback: str | None = "modern") -> str | None:
    """读取显式 ``style``。没写时用 ``fallback``。"""

    style_raw = _declared(cls, "style")
    if style_raw is None:
        return fallback
    style_name = str(style_raw).strip().lower()
    if style_name not in {"modern", "compact"}:
        raise ValueError(f"主题 style 只能是 modern 或 compact，收到 {style_raw!r}")
    return style_name


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
