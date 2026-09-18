"""描边图标路径。全部为 24×24、round cap，运行时把 currentColor 换成 token。"""

from __future__ import annotations

_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">{body}</svg>"""

# 几何自制，不依赖外部图标包。键名保持稳定，供 Icon(name=...) 使用。
_BODIES: dict[str, str] = {
    "search": '<circle cx="11" cy="11" r="6.25"/><path d="M16.2 16.2L21 21"/>',
    "folder": '<path d="M3 7.5A1.5 1.5 0 0 1 4.5 6h4.2l1.8 2H19.5A1.5 1.5 0 0 1 21 9.5v8A1.5 1.5 0 0 1 19.5 19h-15A1.5 1.5 0 0 1 3 17.5z"/>',
    "file": '<path d="M14 3H7.5A1.5 1.5 0 0 0 6 4.5v15A1.5 1.5 0 0 0 7.5 21h9A1.5 1.5 0 0 0 18 19.5V8z"/><path d="M14 3v5h5"/>',
    "inbox": '<path d="M4 13l2.2-8h11.6L20 13"/><path d="M4 13h4.2l1.3 2h5l1.3-2H20v6.5A1.5 1.5 0 0 1 18.5 21h-13A1.5 1.5 0 0 1 4 19.5z"/>',
    "x": '<path d="M6 6l12 12M18 6L6 18"/>',
    "check": '<path d="M5 12.5l4.5 4.5L19 7"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "minus": '<path d="M5 12h14"/>',
    "chevron-down": '<path d="M6 9l6 6 6-6"/>',
    "chevron-up": '<path d="M6 15l6-6 6 6"/>',
    "chevron-right": '<path d="M9 6l6 6-6 6"/>',
    "chevron-left": '<path d="M15 6l-6 6 6 6"/>',
    "settings": '<circle cx="12" cy="12" r="3"/><path d="M12 4.2v1.6M12 18.2v1.6M4.2 12h1.6M18.2 12h1.6M6.4 6.4l1.1 1.1M16.5 16.5l1.1 1.1M17.6 6.4l-1.1 1.1M7.5 16.5l-1.1 1.1"/>',
    "info": '<circle cx="12" cy="12" r="8.25"/><path d="M12 11v5M12 8h.01"/>',
    "warning": '<path d="M12 4.5L21 19H3z"/><path d="M12 10v4M12 16.5h.01"/>',
    "error": '<circle cx="12" cy="12" r="8.25"/><path d="M9 9l6 6M15 9l-6 6"/>',
    "success": '<circle cx="12" cy="12" r="8.25"/><path d="M8 12.2l2.6 2.6L16.5 9"/>',
    "play": '<path d="M8 6.5v11L18 12z" fill="currentColor" stroke="none"/>',
    "pause": '<path d="M8 6h2.8v12H8zM13.2 6H16v12h-2.8z" fill="currentColor" stroke="none"/>',
    "skip-back": '<path d="M11 12l8-5.5v11z" fill="currentColor" stroke="none"/><path d="M5 6.5v11"/>',
    "skip-forward": '<path d="M13 12L5 6.5v11z" fill="currentColor" stroke="none"/><path d="M19 6.5v11"/>',
    "volume": '<path d="M4 10h3.2L12 6.5v11L7.2 14H4z"/><path d="M16 9.2a3.2 3.2 0 0 1 0 5.6"/>',
    "send": '<path d="M4 11.5l16-7.5-7.2 16-2.2-6.4z"/>',
    "refresh": '<path d="M20 12a8 8 0 1 1-2.2-5.5"/><path d="M20 5v5h-5"/>',
    "download": '<path d="M12 4v11M7.5 11.5L12 16l4.5-4.5M5 20h14"/>',
    "copy": '<rect x="8" y="8" width="11" height="12" rx="1.5"/><path d="M5.5 16V4.8A1.8 1.8 0 0 1 7.3 3h8.2"/>',
    "trash": '<path d="M5 7h14M9 7V5h6v2M8 7l.8 12h6.4L16 7"/>',
    "layout-dashboard": '<rect x="4" y="4" width="7" height="7" rx="1"/><rect x="13" y="4" width="7" height="4" rx="1"/><rect x="13" y="10" width="7" height="10" rx="1"/><rect x="4" y="13" width="7" height="7" rx="1"/>',
    "wrench": '<path d="M15.2 6.2a3.4 3.4 0 0 1 3.2 5.5L10 20H5.5v-4.5z"/><circle cx="7.2" cy="16.8" r="0.8"/>',
    "film": '<rect x="4" y="5" width="16" height="14" rx="1.5"/><path d="M8 5v14M16 5v14M4 9h4M16 9h4M4 15h4M16 15h4"/>',
    "music": '<path d="M9 18a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z"/><path d="M11.5 15.5V6l8-1.5v8"/><path d="M19.5 12.5a2.5 2.5 0 1 0 0-5"/>',
    "bot": '<rect x="5" y="8" width="14" height="11" rx="3"/><path d="M12 8V5M9.5 13h.01M14.5 13h.01M9 16.2h6"/>',
    "git-branch": '<circle cx="6" cy="6" r="2"/><circle cx="6" cy="18" r="2"/><circle cx="18" cy="12" r="2"/><path d="M6 8v8M8 18h4.5A3.5 3.5 0 0 0 16 14.5V13"/>',
    "activity": '<path d="M3 12h4l2.5-6 4 12 2.5-6H21"/>',
    "grid": '<rect x="4" y="4" width="6" height="6" rx="1"/><rect x="14" y="4" width="6" height="6" rx="1"/><rect x="4" y="14" width="6" height="6" rx="1"/><rect x="14" y="14" width="6" height="6" rx="1"/>',
    "sun": '<circle cx="12" cy="12" r="3.5"/><path d="M12 3.5v2M12 18.5v2M3.5 12h2M18.5 12h2M5.8 5.8l1.4 1.4M16.8 16.8l1.4 1.4M18.2 5.8l-1.4 1.4M7.2 16.8l-1.4 1.4"/>',
    "moon": '<path d="M16.5 13.2A6.5 6.5 0 1 1 10.8 5.5 5 5 0 0 0 16.5 13.2z"/>',
    "sidebar": '<rect x="3.5" y="4.5" width="17" height="15" rx="1.5"/><path d="M9.5 4.5v15"/>',
    "message": '<path d="M5 6.5A1.5 1.5 0 0 1 6.5 5h11A1.5 1.5 0 0 1 19 6.5V14a1.5 1.5 0 0 1-1.5 1.5H9l-4 3.2z"/>',
    "sliders": '<path d="M5 6h8M17 6h2M5 12h2M11 12h8M5 18h10M19 18h0"/><circle cx="15" cy="6" r="1.7"/><circle cx="9" cy="12" r="1.7"/><circle cx="17" cy="18" r="1.7"/>',
    "terminal": '<rect x="3.5" y="5" width="17" height="14" rx="1.5"/><path d="M7 10l3 2-3 2M12 14h5"/>',
    "monitor": '<rect x="3.5" y="4.5" width="17" height="12" rx="1.5"/><path d="M8 20h8M12 16.5V20"/>',
    "table": '<rect x="4" y="5" width="16" height="14" rx="1"/><path d="M4 10h16M4 14h16M10 5v14"/>',
    "list": '<path d="M8 7h12M8 12h12M8 17h12M5 7h.01M5 12h.01M5 17h.01"/>',
    "clock": '<circle cx="12" cy="12" r="8.25"/><path d="M12 7.5V12l3 2"/>',
    "more": '<circle cx="6" cy="12" r="1.2"/><circle cx="12" cy="12" r="1.2"/><circle cx="18" cy="12" r="1.2"/>',
    "file-plus": '<path d="M14 3H7.5A1.5 1.5 0 0 0 6 4.5v15A1.5 1.5 0 0 0 7.5 21h9A1.5 1.5 0 0 0 18 19.5V8z"/><path d="M14 3v5h5M12 12v5M9.5 14.5h5"/>',
    "circle-dot": '<circle cx="12" cy="12" r="8.25"/><circle cx="12" cy="12" r="2.2"/>',
    "win-min": '<path d="M5 12h14" stroke-width="2"/>',
    "win-max": '<rect x="6" y="6" width="12" height="12" rx="1"/>',
    "win-restore": '<rect x="8" y="5" width="10" height="10" rx="1"/><path d="M6 9v9h9"/>',
    "win-close": '<path d="M7 7l10 10M17 7 7 17"/>',
    "volume-off": '<path d="M5 10v4h3l4 3V7l-4 3H5z"/><path d="M16.5 9.5l5 5M21.5 9.5l-5 5"/>',
    "command": '<rect x="4.5" y="4.5" width="15" height="15" rx="3"/><path d="M8 12h8M12 8v8"/>',
}

GLYPHS: dict[str, str] = {name: _SVG.format(body=body) for name, body in _BODIES.items()}

TONE_ICONS = {
    "info": "info",
    "success": "success",
    "warning": "warning",
    "error": "error",
    "neutral": "circle-dot",
}


def icon_names() -> tuple[str, ...]:
    """已绘制的图标名，按字母序。"""

    return tuple(sorted(GLYPHS))


def svg_markup(name: str) -> str:
    """返回 SVG 文本。未知名称回落到 ``circle-dot``。"""

    return GLYPHS.get(name, GLYPHS["circle-dot"])
