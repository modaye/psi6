"""用 Python 类定义主题。``python -m psi6.examples.custom_theme --check``。"""

from __future__ import annotations

import sys

from psi6 import App, DesktopWindow, Theme, contrast_notes


class Moss(Theme):
    """只覆盖强调色。其余字段来自 ``base``。"""

    name = "moss"
    base = "dark"
    color_primary = "#4d7c5a"


def build(app: App) -> DesktopWindow:
    """窗口标题带上主题名。对比度说明不参与加载。"""

    return DesktopWindow(title=f"{app.name} · {Moss.name}")


def main(argv: list[str] | None = None) -> int:
    """加载 ``Moss``。``--check`` 核对主色后退出。"""

    args = sys.argv[1:] if argv is None else argv
    app = App("psi6-theme", theme=Moss)
    if "--check" in args:
        if app.tokens.color_primary != "#4d7c5a":
            return 2
        contrast_notes(app.tokens)
        from PySide6.QtCore import QTimer

        QTimer.singleShot(0, app.qt_app.quit)
    return app.run(build(app))


if __name__ == "__main__":
    raise SystemExit(main())
