"""离屏截取图库每一页，供目视验收默认 UI。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize

from psi6.examples.kit import _DESTINATIONS, _PRESET_COMPACT, KitWindow
from psi6.runtime.app import App
from psi6.runtime.qt_env import install_qt_message_filter, prepare_qt_environment
from psi6.ui.window_shape import grab_rounded


def capture(
    out_dir: str | Path,
    *,
    themes: tuple[str | Path, ...] | None = None,
) -> list[Path]:
    """把每个场景写成 PNG。返回写出的路径。"""

    selected = themes if themes is not None else ("light", "dark", _PRESET_COMPACT)
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    app = App("psi6-visual-qa")
    window = KitWindow(app)
    window.setFixedSize(QSize(1180, 760))
    window.show()
    qt = app.qt_app
    for theme in selected:
        app.set_theme(theme)
        window.shell.sidebar.apply_metrics()
        window.shell.sidebar.refresh_icons()
        qt.processEvents()
        label = theme if isinstance(theme, str) else theme.stem
        for item in _DESTINATIONS:
            window.show_page(item.page_id)
            qt.processEvents()
            path = target / f"{label}_{item.page_id}.png"
            grab_rounded(window).save(str(path), "PNG")
            written.append(path)
    window.close()
    return written


def main() -> None:
    import os
    import sys

    prepare_qt_environment()
    install_qt_message_filter()
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("artifacts/visual")
    paths = capture(out)
    print(f"wrote {len(paths)} screenshots to {out.resolve()}")


if __name__ == "__main__":
    main()
