"""最小应用。复制本目录后执行 ``python app.py --check``。"""

from __future__ import annotations

import sys

from psi6 import App, DesktopWindow

from theme import Desk


def main(argv: list[str] | None = None) -> int:
    """显示主窗口。``--check`` 核对主题后退出。"""

    args = sys.argv[1:] if argv is None else argv
    app = App("desk", theme=Desk)
    window = DesktopWindow(title="Desk")
    if "--check" in args:
        if app.tokens.color_primary != "#4d7c5a":
            return 2
        from PySide6.QtCore import QTimer

        QTimer.singleShot(0, app.qt_app.quit)
    return app.run(window)


if __name__ == "__main__":
    raise SystemExit(main())
