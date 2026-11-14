"""设计 token：组件与 QSS 唯一允许出现色值与度量的地方。"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields, replace
from pathlib import Path
from typing import Any

from psi6.theme.colors import is_color, mix_hex

_STATE_FIELDS = {
    "color_pressed",
    "color_selected",
    "color_primary_hover",
    "color_primary_pressed",
    "color_danger_hover",
    "color_danger_pressed",
}
# 留空表示「跟着另一条 token 走」，不是非法颜色。控件描边默认等于 color_border。
_OPTIONAL_COLOR_FIELDS = _STATE_FIELDS | {"color_control_border"}
_HOVER_SHADE = "#ffffff"
_PRESS_SHADE = "#10151c"

_NESTED_FIELDS: dict[str, dict[str, str]] = {
    "button": {"radius": "button_radius", "height": "control_height"},
    "title_bar": {"height": "title_bar_height"},
    "switch": {"width": "switch_width", "height": "switch_height"},
}

_MODERN_METRICS: dict[str, int] = {
    "space_sm": 8,
    "space_md": 12,
    "space_lg": 16,
    "radius": 6,
    "button_radius": 6,
    "icon_size": 16,
    "control_height": 36,
    "control_height_sm": 28,
    "row_height": 32,
    "focus_ring_width": 2,
    "title_bar_height": 36,
    "switch_width": 44,
    "switch_height": 24,
    "sidebar_width": 212,
    "sidebar_compact_width": 56,
    "font_size": 13,
    "font_size_sm": 12,
    "font_size_title": 18,
}

_COMPACT_METRICS: dict[str, int] = {
    "space_sm": 4,
    "space_md": 8,
    "space_lg": 10,
    "radius": 4,
    "button_radius": 4,
    "icon_size": 14,
    "control_height": 30,
    "control_height_sm": 24,
    "row_height": 28,
    "focus_ring_width": 2,
    "title_bar_height": 32,
    "switch_width": 38,
    "switch_height": 20,
    "sidebar_width": 188,
    "sidebar_compact_width": 52,
    "font_size": 12,
    "font_size_sm": 11,
    "font_size_title": 16,
}


@dataclass(frozen=True)
class Tokens:
    """桌面工具视觉变量。

    浅色背景是纯白。面板、悬停和侧栏用中性灰，不带绿。蕨绿只留给主操作、焦点和选中浅底。
    默认浅色和深色不含蓝、紫。卡片仍用 ``color_surface``，避免和画布贴成一片。
    用户自定义：子类化 ``psi6.theme.Theme``，或 ``overlay`` 覆盖字段。不要手写整份 QSS，
    也不要再用 JSON / TOML / YAML 描述主题。
    动画只暴露时长：``motion_fast_ms`` / ``motion_ms``（毫秒，``0`` 关闭）。
    ``Theme.style`` 取 ``modern`` 或 ``compact``，只决定尺寸。``base`` 取 ``light``、``dark`` 或 ``auto``，只决定配色。
    字体只有正文（``font_family`` / ``font_size``）和等宽（``font_mono``）两族，标题只用字号和字重区分。
    文字只有标题、正文、辅助三档。表面是窗口、面板、输入、浮层四层。
    组件级覆盖可用嵌套：``button.radius``、``title_bar.height``、``switch.width``。
    状态色留空时按基础色推导：按下比悬停对比更强，选中是主色的浅底。写值即覆盖。
    ``color_control_border`` 是输入框、普通按钮、勾选框等交互控件的描边。留空时等于
    ``color_border``，因此浅色、深色和只改了 ``color_border`` 的自定义主题不用再写一份。
    分隔线、卡片、对话框仍用 ``color_border``。需要把控件边和结构边分开时再写值。
    图标：主题旁 ``icons/search.svg`` 与 ``Icon("search")`` 同名即覆盖。
    """

    color_bg: str = "#ffffff"
    color_surface: str = "#ffffff"
    color_elevated: str = "#ffffff"
    color_sunken: str = "#f3f4f4"
    color_hover: str = "#f0f1f1"
    color_pressed: str = ""
    color_selected: str = ""
    color_text: str = "#1c1f1e"
    color_muted: str = "#5f6863"
    color_border: str = "#e4e6e5"
    color_border_subtle: str = "#eeefef"
    color_control_border: str = ""
    color_disabled: str = "#aeb4b0"
    color_primary: str = "#1f7a4d"
    color_on_primary: str = "#f7fcf9"
    color_primary_hover: str = ""
    color_primary_pressed: str = ""
    color_danger: str = "#c93b32"
    color_danger_hover: str = ""
    color_danger_pressed: str = ""
    color_success: str = "#5c7010"
    color_warning: str = "#9a6408"
    color_info: str = "#6a6156"
    color_focus: str = "#0e5c38"
    color_overlay: str = "rgba(244, 245, 245, 210)"
    color_sidebar: str = "#f7f7f7"
    color_sidebar_text: str = "#3c4440"
    color_user_bubble: str = "#1f7a4d"
    color_user_on_bubble: str = "#f7fcf9"
    space_sm: int = 8
    space_md: int = 12
    space_lg: int = 16
    radius: int = 6
    button_radius: int = 6
    focus_ring_width: int = 2
    window_radius: int = 10
    sidebar_width: int = 212
    sidebar_compact_width: int = 56
    icon_size: int = 16
    control_height: int = 36
    control_height_sm: int = 28
    row_height: int = 32
    title_bar_height: int = 36
    switch_width: int = 44
    switch_height: int = 24
    font_family: str = '"Segoe UI Variable Text", "Segoe UI", "Microsoft YaHei UI", sans-serif'
    font_mono: str = '"Cascadia Mono", "Consolas", monospace'
    font_size: int = 13
    font_size_sm: int = 12
    font_size_title: int = 18
    font_weight_body: int = 400
    font_weight_title: int = 600
    motion_fast_ms: int = 160
    motion_ms: int = 220
    reduced_motion: int = 0
    icon_dir: str = ""
    icons: tuple[tuple[str, str], ...] = ()

    @classmethod
    def light(cls) -> Tokens:
        """浅色工作台。``App`` 默认主题。"""

        return cls()

    @classmethod
    def dark(cls) -> Tokens:
        """深色工作台：中性炭黑，浅蕨绿只做强调。"""

        return cls(
            color_bg="#161716",
            color_surface="#1c1d1c",
            color_elevated="#232423",
            color_sunken="#101110",
            color_hover="#2a2b2a",
            color_text="#f2f3f2",
            color_muted="#a0a6a2",
            color_border="#333533",
            color_border_subtle="#262726",
            color_disabled="#6e746f",
            color_primary="#86d0a4",
            color_on_primary="#102016",
            color_danger="#e99088",
            color_success="#d2d56a",
            color_warning="#e4b45e",
            color_info="#c9c1b6",
            color_focus="#d4f3e2",
            color_overlay="rgba(14, 15, 14, 210)",
            color_sidebar="#121312",
            color_sidebar_text="#c6ccc8",
            color_user_bubble="#173828",
            color_user_on_bubble="#e7f6ee",
        )

    def overlay(self, data: Mapping[str, Any]) -> Tokens:
        """用字典覆盖部分字段。未知键抛出 ``ValueError``，避免拼写错误被静默丢掉。"""

        allowed = {item.name: item for item in fields(self)}
        flat = _flatten_overlay(data)
        unknown = sorted(key for key in flat if key not in allowed)
        if unknown:
            raise ValueError(f"未知 token：{', '.join(unknown)}")
        kwargs: dict[str, Any] = {}
        for key, value in flat.items():
            if key not in allowed:
                continue
            current = getattr(self, key)
            if key == "icons":
                kwargs[key] = _as_icon_pairs(value)
            elif key.startswith("color_"):
                color = str(value).strip()
                if not color and key in _OPTIONAL_COLOR_FIELDS:
                    kwargs[key] = ""
                    continue
                if not is_color(color):
                    raise ValueError(f"{key} 不是有效颜色：{value!r}")
                kwargs[key] = color
            elif isinstance(current, int):
                try:
                    number = int(value)
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"{key} 必须是整数，收到 {value!r}") from exc
                if number < 0:
                    raise ValueError(f"{key} 不能为负数：{number}")
                kwargs[key] = number
            elif key == "icon_dir":
                folder = str(value).strip()
                if folder and not Path(folder).expanduser().is_dir():
                    raise ValueError(f"icon_dir 不存在：{folder}")
                kwargs[key] = folder
            elif isinstance(current, tuple):
                kwargs[key] = _as_icon_pairs(value)
            else:
                kwargs[key] = str(value)
        if "radius" in kwargs and "button_radius" not in kwargs:
            kwargs["button_radius"] = kwargs["radius"]
        reduced = int(kwargs.get("reduced_motion", self.reduced_motion) or 0)
        if reduced:
            kwargs.setdefault("motion_fast_ms", 0)
            kwargs.setdefault("motion_ms", 0)
            kwargs["reduced_motion"] = 1
        return replace(self, **kwargs) if kwargs else self

    def resolve_states(self) -> Tokens:
        """补齐空的状态色，并把空的控件描边收成 ``color_border``。显式值保留。"""

        updates: dict[str, Any] = {}
        if not self.color_pressed:
            updates["color_pressed"] = mix_hex(self.color_hover, self.color_text, 0.12)
        if not self.color_selected:
            updates["color_selected"] = mix_hex(self.color_primary, self.color_bg, 0.86)
        if not self.color_primary_hover:
            updates["color_primary_hover"] = mix_hex(self.color_primary, _HOVER_SHADE, 0.24)
        if not self.color_primary_pressed:
            updates["color_primary_pressed"] = mix_hex(self.color_primary, _PRESS_SHADE, 0.32)
        if not self.color_danger_hover:
            updates["color_danger_hover"] = mix_hex(self.color_danger, _HOVER_SHADE, 0.18)
        if not self.color_danger_pressed:
            updates["color_danger_pressed"] = mix_hex(self.color_danger, _PRESS_SHADE, 0.28)
        if not self.color_control_border:
            updates["color_control_border"] = self.color_border
        return replace(self, **updates) if updates else self


def merge_style(base: Tokens, style: str, updates: Mapping[str, Any]) -> Tokens:
    """把 ``modern`` / ``compact`` 度量套到配色上，再让 ``updates`` 覆盖。"""

    name = str(style).strip().lower()
    if name not in {"modern", "compact"}:
        raise ValueError(f"主题 style 只能是 modern 或 compact，收到 {style!r}")
    preset = dict(_COMPACT_METRICS if name == "compact" else _MODERN_METRICS)
    data = dict(updates)
    if "radius" in data and "button_radius" not in data:
        preset.pop("button_radius", None)
    return base.overlay({**preset, **data})


def style_metrics(style: str) -> dict[str, int]:
    """返回 ``modern`` / ``compact`` 的尺寸预设（控件高、间距、字号、圆角等）。

    供响应式密度（窗口变小 / 高 DPI 时自动收紧）按需覆盖用，只含度量字段，不动颜色。
    """

    name = str(style).strip().lower()
    if name == "compact":
        return dict(_COMPACT_METRICS)
    if name == "modern":
        return dict(_MODERN_METRICS)
    raise ValueError(f"style 只能是 modern 或 compact，收到 {style!r}")


DEFAULT_TOKENS = Tokens.light().resolve_states()


def resolve_tokens(theme: str | Tokens | Any | None = None) -> Tokens:
    """``light`` / ``dark`` / ``auto`` / ``Tokens`` / ``Theme`` 类或实例。

    主题文件路径会抛出 ``TypeError``。图标仍由主题类的模块目录解析。
    """

    from psi6.theme.system import system_prefers_dark
    from psi6.theme.theme import Theme

    if isinstance(theme, type) and issubclass(theme, Theme):
        theme = theme()
    if isinstance(theme, Theme):
        return theme.tokens()
    if isinstance(theme, Tokens):
        return theme.resolve_states()
    if isinstance(theme, str) and theme.lower() in {"auto", "system"}:
        return (Tokens.dark() if system_prefers_dark() else Tokens.light()).resolve_states()
    if theme == "dark":
        return Tokens.dark().resolve_states()
    if theme in {None, "light"}:
        return Tokens.light().resolve_states()
    if isinstance(theme, Path) or _looks_like_theme_file(theme):
        raise TypeError(
            "主题用 Python 类定义，例如 App(name, theme=MyTheme)。不再读取 JSON、TOML 或 YAML。"
        )
    raise TypeError(f"无法识别的主题：{theme!r}")


def _looks_like_theme_file(theme: Any) -> bool:
    if not isinstance(theme, str):
        return False
    suffix = Path(theme).suffix.lower()
    return suffix in {".json", ".toml", ".yaml", ".yml"}


def _flatten_overlay(data: Mapping[str, Any]) -> dict[str, Any]:
    """把 ``button.radius`` 这类嵌套键摊到 token 字段名。"""

    flat: dict[str, Any] = {}
    for key, value in data.items():
        if key in {"base"}:
            continue
        nested = _NESTED_FIELDS.get(key)
        if nested is not None and isinstance(value, Mapping):
            extra = sorted(set(value) - set(nested))
            if extra:
                joined = ", ".join(f"{key}.{item}" for item in extra)
                raise ValueError(f"未知 token：{joined}")
            for nested_key, field_name in nested.items():
                if nested_key in value:
                    flat[field_name] = value[nested_key]
            continue
        flat[key] = value
    return flat


def _as_icon_pairs(value: Any) -> tuple[tuple[str, str], ...]:
    if isinstance(value, Mapping):
        return tuple((str(name), str(markup)) for name, markup in value.items())
    if isinstance(value, (list, tuple)):
        pairs: list[tuple[str, str]] = []
        for item in value:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                pairs.append((str(item[0]), str(item[1])))
        return tuple(pairs)
    return ()
