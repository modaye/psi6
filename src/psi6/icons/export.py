"""把 glyphs 写成独立 SVG，方便设计核对与替换单文件。"""

from __future__ import annotations

from pathlib import Path

from psi6.icons.glyphs import GLYPHS, svg_markup


def svg_dir() -> Path:
    return Path(__file__).resolve().parent / "svg"


def write_svg_files(target: Path | None = None) -> list[Path]:
    """把每个图标写成 ``*.svg``。"""

    folder = target or svg_dir()
    folder.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name in GLYPHS:
        path = folder / f"{name}.svg"
        path.write_text(svg_markup(name), encoding="utf-8")
        written.append(path)
    return written
