"""设计 token：组件与 QSS 唯一允许出现色值与度量的地方。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields, replace
from pathlib import Path
from typing import Any, Mapping

_NESTED_FIELDS: dict[str, dict[str, str]] = {
    "button": {"radius": "button_radius", "height": "control_height"},
    "title_bar": {"height": "title_bar_height"},
    "switch": {"width": "switch_width", "height": "switch_height"},
}

_COMPACT_DEFAULTS: dict[str, int] = {
    "space_sm": 4,
    "space_md": 8,
    "space_lg": 12,
    "font_size": 12,
    "font_size_sm": 11,
    "icon_size": 14,
    "control_height": 28,
    "title_bar_height": 32,
    "switch_width": 38,
    "switch_height": 20,
    "sidebar_width": 188,
    "sidebar_compact_width": 52,
}


@dataclass(frozen=True)
class Tokens:
    """桌面工具视觉变量。

    面向 Windows 上的批处理/内部工具：冷灰底 + 钢蓝强调。
    用户自定义：在 light/dark 上覆盖 JSON / TOML / YAML，不要手写整份 QSS。
    动画只暴露时长：``motion_fast_ms`` / ``motion_ms``（毫秒，``0`` 关闭）。
    ``density`` 为 ``comfortable`` 或 ``compact``；紧凑会填未写出的尺寸键。
    组件级覆盖可用嵌套：``button.radius``、``title_bar.height``、``switch.width``。
    图标：主题旁 ``icons/search.svg`` 与 ``Icon("search")`` 同名即覆盖。
    """

    color_bg: str = "#eef1f5"
    color_surface: str = "#f7f8fb"
    color_sunken: str = "#ffffff"
    color_hover: str = "#e3e8ee"
    color_text: str = "#1f2a36"
    color_muted: str = "#5b6b7c"
    color_border: str = "#c5ced8"
    color_disabled: str = "#93a0ae"
    color_primary: str = "#35597a"
    color_on_primary: str = "#f4f7fa"
    color_danger: str = "#b42318"
    color_success: str = "#1f6b45"
    color_warning: str = "#9a4d0a"
    color_info: str = "#2b5f86"
    color_focus: str = "#35597a"
    color_overlay: str = "rgba(238, 241, 245, 210)"
    color_sidebar: str = "#e6eaef"
    color_sidebar_text: str = "#3d4c5c"
    color_user_bubble: str = "#35597a"
    color_user_on_bubble: str = "#f4f7fa"
    space_sm: int = 6
    space_md: int = 12
    space_lg: int = 16
    radius: int = 4
    button_radius: int = 4
    window_radius: int = 10
    sidebar_width: int = 212
    sidebar_compact_width: int = 56
    icon_size: int = 16
    control_height: int = 32
    title_bar_height: int = 36
    switch_width: int = 44
    switch_height: int = 24
    font_family: str = '"Segoe UI", "Microsoft YaHei UI", sans-serif'
    font_mono: str = '"Cascadia Mono", "Consolas", monospace'
    font_size: int = 13
    font_size_sm: int = 12
    motion_fast_ms: int = 160
    motion_ms: int = 220
    reduced_motion: int = 0
    density: str = "comfortable"
    icon_dir: str = ""
    icons: tuple[tuple[str, str], ...] = ()

    @classmethod
    def light(cls) -> Tokens:
        """浅色工作台。``App`` 默认主题。"""

        return cls()

    @classmethod
    def dark(cls) -> Tokens:
        """深色工作台：石板底 + 钢蓝，避免霓虹强调色。"""

        return cls(
            color_bg="#141a22",
            color_surface="#1c2430",
            color_sunken="#10151c",
            color_hover="#2a3442",
            color_text="#e6edf3",
            color_muted="#8b98a6",
            color_border="#3a4656",
            color_disabled="#6d7a88",
            color_primary="#7fa0bd",
            color_on_primary="#10151c",
            color_danger="#e07070",
            color_success="#6fbf93",
            color_warning="#d4a054",
            color_info="#7aa7c9",
            color_focus="#9bb6cd",
            color_overlay="rgba(20, 26, 34, 220)",
            color_sidebar="#10151c",
            color_sidebar_text="#b4c0cc",
            color_user_bubble="#3d5a73",
            color_user_on_bubble="#f4f7fa",
        )

    def overlay(self, data: Mapping[str, Any]) -> Tokens:
        """用字典覆盖部分字段。未知键忽略。"""

        allowed = {item.name: item for item in fields(self)}
        flat = _flatten_overlay(data)
        kwargs: dict[str, Any] = {}
        for key, value in flat.items():
            if key not in allowed:
                continue
            current = getattr(self, key)
            if key == "density":
                text = str(value).strip().lower()
                kwargs[key] = "compact" if text == "compact" else "comfortable"
            elif key == "icons":
                kwargs[key] = _as_icon_pairs(value)
            elif isinstance(current, int):
                kwargs[key] = int(value)
            elif isinstance(current, tuple):
                kwargs[key] = _as_icon_pairs(value)
            else:
                kwargs[key] = str(value)
        if "radius" in kwargs and "button_radius" not in kwargs:
            kwargs["button_radius"] = kwargs["radius"]
        density = str(kwargs.get("density", self.density))
        if density == "compact":
            for key, value in _COMPACT_DEFAULTS.items():
                kwargs.setdefault(key, value)
            kwargs["density"] = "compact"
        reduced = int(kwargs.get("reduced_motion", self.reduced_motion) or 0)
        if reduced:
            kwargs.setdefault("motion_fast_ms", 0)
            kwargs.setdefault("motion_ms", 0)
            kwargs["reduced_motion"] = 1
        return replace(self, **kwargs) if kwargs else self

    def to_dict(self) -> dict[str, Any]:
        """可写入 JSON 的扁平字典。``icons`` 写成对象。"""

        payload = asdict(self)
        icons = payload.pop("icons", ())
        if icons:
            payload["icons"] = {name: svg for name, svg in icons}
        if not payload.get("icon_dir"):
            payload.pop("icon_dir", None)
        return payload

    @classmethod
    def load(cls, path: str | Path, *, base: str | None = None) -> Tokens:
        """从 JSON / TOML / YAML 或主题目录读取。文件可含 ``base``: ``light`` / ``dark``。

        未写 ``icon_dir`` 时，自动使用旁边的 ``icons/``（或 ``icons/<文件名>/``）里
        与内置图标同名的 ``.svg``。
        """

        from psi6.theme.files import discover_icon_dir, read_theme_payload

        payload, source = read_theme_payload(path)
        root_name = base or str(payload.get("base") or "light")
        root = cls.dark() if root_name == "dark" else cls.light()
        tokens = root.overlay(payload)
        found = discover_icon_dir(source, explicit=tokens.icon_dir)
        if found is None:
            return tokens
        return replace(tokens, icon_dir=str(found))

    def dump(self, path: str | Path, *, base: str = "light") -> None:
        """按后缀写出可再 ``load`` 的主题（含 base）。支持 ``.json`` / ``.toml`` / ``.yaml``。"""

        from psi6.theme.files import write_theme_payload

        write_theme_payload(path, {"base": base, **self.to_dict()})


DEFAULT_TOKENS = Tokens.light()


def resolve_tokens(theme: str | Tokens | Path | None = None) -> Tokens:
    """``light`` / ``dark`` / ``auto`` / ``Tokens`` / JSON·TOML·YAML 路径 / 主题目录。"""

    from psi6.theme.files import is_theme_source
    from psi6.theme.system import system_prefers_dark

    if isinstance(theme, Tokens):
        return theme
    if isinstance(theme, str) and theme.lower() in {"auto", "system"}:
        return Tokens.dark() if system_prefers_dark() else Tokens.light()
    if theme == "dark":
        return Tokens.dark()
    if isinstance(theme, Path) or (isinstance(theme, str) and is_theme_source(theme)):
        return Tokens.load(theme)
    return Tokens.light()


def _flatten_overlay(data: Mapping[str, Any]) -> dict[str, Any]:
    """把 ``button.radius`` 这类嵌套键摊到 token 字段名。"""

    flat: dict[str, Any] = {}
    for key, value in data.items():
        if key in {"base"}:
            continue
        nested = _NESTED_FIELDS.get(key)
        if nested is not None and isinstance(value, Mapping):
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
