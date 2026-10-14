"""设计 token：组件与 QSS 唯一允许出现色值与度量的地方。"""

from __future__ import annotations

from dataclasses import dataclass, fields, replace
from pathlib import Path
from typing import Any, Mapping

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

    浅色背景是纯白。卡片仍用 ``color_surface``，避免和画布贴成一片。
    用户自定义：子类化 ``psi6.theme.Theme``，或 ``overlay`` 覆盖字段。不要手写整份 QSS，
    也不要再用 JSON / TOML / YAML 描述主题。
    动画只暴露时长：``motion_fast_ms`` / ``motion_ms``（毫秒，``0`` 关闭）。
    ``Theme.style`` 取 ``modern`` 或 ``compact``，只决定尺寸。``base`` 只决定配色。
    文字只有标题、正文、辅助三档。表面是窗口、面板、输入、浮层四层。
    组件级覆盖可用嵌套：``button.radius``、``title_bar.height``、``switch.width``。
    图标：主题旁 ``icons/search.svg`` 与 ``Icon("search")`` 同名即覆盖。
    """

    color_bg: str = "#ffffff"
    color_surface: str = "#f6f8fa"
    color_elevated: str = "#ffffff"
    color_sunken: str = "#f3f5f8"
    color_hover: str = "#e9eef4"
    color_text: str = "#1c2431"
    color_muted: str = "#5a6675"
    color_border: str = "#d3dae3"
    color_border_subtle: str = "#e6eaf0"
    color_disabled: str = "#9ba5b2"
    color_primary: str = "#2b5cd7"
    color_on_primary: str = "#f6f9ff"
    color_danger: str = "#d0392e"
    color_success: str = "#1e7a4c"
    color_warning: str = "#9a5f08"
    color_info: str = "#0e7490"
    color_focus: str = "#2b5cd7"
    color_overlay: str = "rgba(233, 238, 244, 215)"
    color_sidebar: str = "#f1f3f6"
    color_sidebar_text: str = "#42505f"
    color_user_bubble: str = "#2b5cd7"
    color_user_on_bubble: str = "#f6f9ff"
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
        """深色工作台：深石板底 + 透亮蓝主色，避免霓虹强调色。"""

        return cls(
            color_bg="#0f141c",
            color_surface="#161c26",
            color_elevated="#1d2531",
            color_sunken="#0a0e14",
            color_hover="#222b3a",
            color_text="#e4e9f2",
            color_muted="#8b97a8",
            color_border="#2b3546",
            color_border_subtle="#202836",
            color_disabled="#5c6775",
            color_primary="#6e9ff2",
            color_on_primary="#0b1220",
            color_danger="#e26d66",
            color_success="#55b785",
            color_warning="#d9a24f",
            color_info="#67b0d8",
            color_focus="#86b3f5",
            color_overlay="rgba(15, 20, 28, 220)",
            color_sidebar="#0b0f16",
            color_sidebar_text="#a4b0c0",
            color_user_bubble="#2c4a7c",
            color_user_on_bubble="#eaf1fc",
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
            elif isinstance(current, int):
                kwargs[key] = int(value)
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


DEFAULT_TOKENS = Tokens.light()


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
        return theme
    if isinstance(theme, str) and theme.lower() in {"auto", "system"}:
        return Tokens.dark() if system_prefers_dark() else Tokens.light()
    if theme == "dark":
        return Tokens.dark()
    if theme in {None, "light"}:
        return Tokens.light()
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
