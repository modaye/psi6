"""控件自己的样式。

页面在运行时指定字号、字重、字色和底色。颜色可以是字面色，也可以是主题 token 名。
token 名会在主题切换后重算；字面色保持调用时的值。业务代码不要自己写样式表。
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import QWidget

from psi6.theme.runtime import token_color

_PROP = "psi6Style"
_MARK = "psi6StylePaint"
_FILTER = "psi6StyleFilter"
# setStyleSheet 会同步再发 PaletteChange。正在写的控件记在这里，避免刷新器把自己叫进去。
_APPLYING: set[int] = set()


@dataclass
class Style:
    """贴在一个控件上的样式。``None`` 表示这次不改该字段。"""

    size: int | None = None
    weight: int | None = None
    color: str | None = None
    fill: str | None = None
    radius: int | None = None
    padding: int | None = None

    def apply(self, widget: QWidget) -> None:
        """贴到控件上，并与控件上已有的样式合并。"""

        set_style(
            widget,
            size=self.size,
            weight=self.weight,
            color=self.color,
            fill=self.fill,
            radius=self.radius,
            padding=self.padding,
        )


def set_style(
    widget: QWidget,
    *,
    size: int | None = None,
    weight: int | None = None,
    color: str | None = None,
    fill: str | None = None,
    radius: int | None = None,
    padding: int | None = None,
) -> None:
    """给这一个控件设置样式，立刻生效。

    再次调用只覆盖传入的字段。``color`` / ``fill`` 接受 ``#RRGGBB``、``rgb(...)`` /
    ``rgba(...)``，或 token 名（``primary``、``color_text``）。主题切换后 token 会重算。
    """

    stored = _stored(widget)
    incoming = {
        "size": size,
        "weight": weight,
        "color": color,
        "fill": fill,
        "radius": radius,
        "padding": padding,
    }
    for key, value in incoming.items():
        if value is not None:
            stored[key] = value
    _validate(stored)
    for key in ("color", "fill"):
        value = stored.get(key)
        if isinstance(value, str) and value:
            resolve_color(value)
    widget.setProperty(_PROP, stored)
    _ensure_filter(widget)
    _paint(widget, stored)


def clear_style(widget: QWidget) -> None:
    """去掉 ``set_style`` 写上的样式，控件回到主题默认。"""

    widget.setProperty(_PROP, {})
    widget.setProperty(_MARK, "")
    widget.setStyleSheet("")


def resolve_color(value: str) -> str:
    """把 token 名或字面色收成样式表能用的颜色。无法识别时抛出 ``ValueError``。"""

    text = value.strip()
    if not text:
        raise ValueError("颜色不能为空")
    if text.startswith("#") or text.startswith("rgb"):
        return text
    resolved = token_color(text)
    if not resolved:
        raise ValueError(f"无法识别的颜色：{value}")
    return resolved


def _stored(widget: QWidget) -> dict[str, object]:
    raw = widget.property(_PROP)
    if isinstance(raw, dict):
        return dict(raw)
    return {}


def _validate(stored: dict[str, object]) -> None:
    size = stored.get("size")
    weight = stored.get("weight")
    if size is not None and int(size) <= 0:
        raise ValueError(f"字号必须大于 0，收到 {size}")
    if weight is not None and not 1 <= int(weight) <= 1000:
        raise ValueError(f"字重必须在 1 到 1000 之间，收到 {weight}")


def _ensure_filter(widget: QWidget) -> None:
    if widget.property(_FILTER):
        return
    widget.installEventFilter(_StyleRefresher(widget))
    widget.setProperty(_FILTER, True)


def _tracks_theme(stored: dict[str, object]) -> bool:
    """字面色不随主题变。只有 token 名才需要在调色板变化后重算。"""

    for key in ("color", "fill"):
        value = stored.get(key)
        if isinstance(value, str) and value.strip() and not _literal_color(value):
            return True
    return False


def _literal_color(value: str) -> bool:
    text = value.strip()
    return text.startswith("#") or text.startswith("rgb")


def _sheet(stored: dict[str, object]) -> str:
    selector = f'QWidget[{_MARK}="1"]'
    rules: list[str] = []
    size = stored.get("size")
    weight = stored.get("weight")
    color = stored.get("color")
    fill = stored.get("fill")
    radius = stored.get("radius")
    padding = stored.get("padding")
    if size is not None:
        rules.append(f"font-size: {int(size)}px")
    if weight is not None:
        rules.append(f"font-weight: {int(weight)}")
    if isinstance(color, str) and color:
        rules.append(f"color: {resolve_color(color)}")
    if isinstance(fill, str) and fill:
        rules.append(f"background: {resolve_color(fill)}")
    if radius is not None:
        rules.append(f"border-radius: {int(radius)}px")
    if padding is not None:
        rules.append(f"padding: {int(padding)}px")
    body = "; ".join(rules)
    return f"{selector} {{ {body}; }}"


def _paint(widget: QWidget, stored: dict[str, object]) -> None:
    key = id(widget)
    if key in _APPLYING:
        return
    sheet = "" if not stored else _sheet(stored)
    if widget.styleSheet() == sheet:
        return
    _APPLYING.add(key)
    try:
        if stored.get("fill"):
            widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        if sheet:
            widget.setProperty(_MARK, "1")
        else:
            widget.setProperty(_MARK, "")
        widget.setStyleSheet(sheet)
    finally:
        _APPLYING.discard(key)


class _StyleRefresher(QObject):
    """主题切换后，用 token 名记下的颜色按新主题再画一次。"""

    def __init__(self, widget: QWidget) -> None:
        super().__init__(widget)
        self._widget = widget

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self._widget and event.type() in {
            QEvent.Type.PaletteChange,
            QEvent.Type.StyleChange,
        }:
            stored = _stored(self._widget)
            if stored and _tracks_theme(stored):
                _paint(self._widget, stored)
        return False
