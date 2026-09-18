"""主题文件：JSON / TOML / YAML，以及按同名 SVG 自动发现图标目录。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_FILE_SUFFIXES = {".json", ".toml", ".yaml", ".yml"}
_THEME_NAMES = (
    "theme.toml",
    "theme.yaml",
    "theme.yml",
    "theme.json",
    "tokens.toml",
    "tokens.yaml",
    "tokens.yml",
    "tokens.json",
)


def is_theme_source(value: str | Path) -> bool:
    """路径是主题文件，或含 ``theme.toml`` 等清单的主题目录。"""

    path = Path(value).expanduser()
    if path.suffix.lower() in _FILE_SUFFIXES:
        return True
    if not path.is_dir():
        return False
    return any((path / name).is_file() for name in _THEME_NAMES)


def read_theme_payload(path: str | Path) -> tuple[dict[str, Any], Path]:
    """读主题为字典，并返回实际文件路径（目录会落到 ``theme.toml`` 等）。"""

    source = _resolve_theme_file(Path(path).expanduser())
    text = source.read_text(encoding="utf-8")
    suffix = source.suffix.lower()
    if suffix == ".json":
        payload = json.loads(text)
    elif suffix == ".toml":
        import tomllib

        payload = tomllib.loads(text)
    elif suffix in {".yaml", ".yml"}:
        payload = _load_yaml(text)
    else:
        raise ValueError(f"不支持的主题格式：{source.suffix}")
    if not isinstance(payload, dict):
        raise ValueError("主题文件必须是对象")
    return payload, source


def write_theme_payload(path: str | Path, payload: dict[str, Any]) -> None:
    """按后缀写出主题。``.toml`` 不依赖第三方库。"""

    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    suffix = target.suffix.lower()
    if suffix == ".toml":
        text = dump_toml(payload)
    elif suffix in {".yaml", ".yml"}:
        text = _dump_yaml(payload)
    else:
        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    target.write_text(text, encoding="utf-8")


def discover_icon_dir(source: Path, *, explicit: str = "") -> Path | None:
    """图标目录：文件里的 ``icon_dir`` 优先，否则用固定约定。

    约定（存在且含 ``*.svg`` 才采用）：
    - 主题目录：``<pack>/icons/``
    - 主题文件：``<parent>/icons/<stem>/``，否则 ``<parent>/icons/``
    文件名与 ``Icon("search")`` 的 name 相同，例如 ``search.svg``。
    """

    origin = source.parent if source.is_file() else source
    if explicit:
        folder = Path(explicit).expanduser()
        if not folder.is_absolute():
            folder = (origin / folder).resolve()
        return folder if folder.is_dir() else None
    candidates: list[Path] = []
    if source.is_file():
        candidates.append(origin / "icons" / source.stem)
        candidates.append(origin / "icons")
    candidates.append(origin / "icons")
    seen: set[Path] = set()
    for folder in candidates:
        resolved = folder.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved.is_dir() and any(resolved.glob("*.svg")):
            return resolved
    return None


def dump_toml(payload: dict[str, Any]) -> str:
    """写出仅含标量与一层表的 TOML。"""

    lines: list[str] = []
    tables: list[tuple[str, dict[str, Any]]] = []
    for key, value in payload.items():
        if isinstance(value, dict):
            tables.append((str(key), value))
            continue
        lines.append(f"{key} = {_toml_scalar(value)}")
    for name, table in tables:
        lines.append("")
        lines.append(f"[{name}]")
        for key, value in table.items():
            lines.append(f"{key} = {_toml_scalar(value)}")
    return "\n".join(lines).rstrip() + "\n"


def _resolve_theme_file(path: Path) -> Path:
    if path.is_dir():
        for name in _THEME_NAMES:
            candidate = path / name
            if candidate.is_file():
                return candidate
        listed = ", ".join(_THEME_NAMES)
        raise FileNotFoundError(f"主题目录缺少 {listed}：{path}")
    if not path.is_file():
        raise FileNotFoundError(f"找不到主题文件：{path}")
    return path


def _toml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    return json.dumps(str(value), ensure_ascii=False)


def _load_yaml(text: str) -> Any:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("读取 YAML 主题需要 PyYAML：uv add pyyaml") from exc
    return yaml.safe_load(text)


def _dump_yaml(payload: dict[str, Any]) -> str:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("写出 YAML 主题需要 PyYAML：uv add pyyaml") from exc
    return yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)
