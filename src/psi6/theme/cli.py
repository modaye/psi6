"""主题检查命令。

``python -m psi6 theme`` 列出内置主题；``python -m psi6 theme obsidian`` 打印 token；
``--json`` 输出机器可读结果；``--check`` 只报告对比度诊断并用退出码表示结果
（0 无问题，1 有诊断，2 主题无法加载）。
"""

from __future__ import annotations

import importlib
import json
import sys
from dataclasses import asdict
from typing import Any

from psi6.theme.builtin import builtin_themes
from psi6.theme.diagnose import contrast_notes
from psi6.theme.theme import Theme
from psi6.theme.tokens import Tokens, resolve_tokens

__all__ = ["main"]

_ALIASES = {"light": "light", "dark": "dark", "auto": "auto", "system": "auto"}


def theme_report(spec: str) -> dict[str, Any]:
    """加载一个主题并返回名称、来源信息、全部 token 与诊断。"""

    name, base, style, tokens = _load_theme(spec)
    return {
        "name": name,
        "base": base,
        "style": style,
        "tokens": asdict(tokens),
        "notes": contrast_notes(tokens),
    }


def main(argv: list[str] | None = None) -> int:
    """``python -m psi6 theme [名称 ...] [--json] [--check]``。"""

    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    args = list(sys.argv[1:] if argv is None else argv)
    as_json = "--json" in args
    check = "--check" in args
    unknown = [arg for arg in args if arg.startswith("-") and arg not in {"--json", "--check"}]
    if unknown:
        sys.stderr.write(f"psi6: 未知参数：{', '.join(unknown)}\n")
        return 2
    names = [arg for arg in args if not arg.startswith("-")]
    if not names and not check:
        return _list_themes(as_json)
    if not names:
        names = ["light", "dark", *(theme.name for theme in builtin_themes())]
    reports: list[dict[str, Any]] = []
    for name in names:
        try:
            reports.append(theme_report(name))
        except (ValueError, TypeError, FileNotFoundError) as exc:
            sys.stderr.write(f"psi6: {exc}\n")
            return 2
    if as_json:
        payload: Any = reports[0] if len(reports) == 1 else reports
        sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    elif check:
        for report in reports:
            sys.stdout.write(_check_line(report) + "\n")
    else:
        sys.stdout.write("\n\n".join(_render(report) for report in reports) + "\n")
    if check and any(report["notes"] for report in reports):
        return 1
    return 0


def _load_theme(spec: str) -> tuple[str, str, str, Tokens]:
    text = spec.strip()
    key = text.lower()
    if key in _ALIASES:
        base = _ALIASES[key]
        return base, base, "modern", resolve_tokens(base)
    for theme in builtin_themes():
        if theme.name.lower() == key:
            return (
                theme.name,
                str(theme.base).lower(),
                str(theme.style).lower(),
                resolve_tokens(theme),
            )
    if ":" in text:
        module_name, _, attr = text.partition(":")
        try:
            module = importlib.import_module(module_name)
            candidate = getattr(module, attr)
        except (ImportError, AttributeError) as exc:
            raise ValueError(f"无法导入主题 {text}：{exc}") from exc
        if not (isinstance(candidate, type) and issubclass(candidate, Theme)):
            raise ValueError(f"{text} 不是 Theme 子类")
        return (
            str(candidate.name),
            str(candidate.base).lower(),
            str(candidate.style).lower(),
            resolve_tokens(candidate),
        )
    known = ", ".join(["light", "dark", "auto", *(theme.name for theme in builtin_themes())])
    raise ValueError(f"未知主题：{spec}。可用：{known}；自定义主题用 模块:类名")


def _list_themes(as_json: bool) -> int:
    rows = [
        {"name": "light", "base": "light", "style": "modern"},
        {"name": "dark", "base": "dark", "style": "modern"},
        {"name": "auto", "base": "auto", "style": "modern"},
    ]
    for theme in builtin_themes():
        rows.append(
            {
                "name": theme.name,
                "base": str(theme.base).lower(),
                "style": str(theme.style).lower(),
            }
        )
    if as_json:
        sys.stdout.write(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
        return 0
    for row in rows:
        sys.stdout.write(f"{row['name']:<20} base={row['base']:<7} style={row['style']}\n")
    return 0


def _render(report: dict[str, Any]) -> str:
    lines = [f"{report['name']}  base={report['base']}  style={report['style']}"]
    for field, value in report["tokens"].items():
        if field == "icons":
            continue
        lines.append(f"  {field}: {value}")
    lines.extend(_note_lines(report["notes"]))
    return "\n".join(lines)


def _check_line(report: dict[str, Any]) -> str:
    notes = report["notes"]
    if not notes:
        return f"{report['name']}: 无对比度问题"
    return "\n".join([f"{report['name']}:", *(f"  - {note}" for note in notes)])


def _note_lines(notes: list[str]) -> list[str]:
    if not notes:
        return ["诊断：无"]
    return ["诊断：", *(f"  - {note}" for note in notes)]
