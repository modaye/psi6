"""最小桌面窗口。``python -m psi6.examples.minimal --check`` 打开后立即退出。"""

from __future__ import annotations

import sys

from psi6 import App, DesktopWindow


def build(app: App) -> DesktopWindow:
    """用应用名做标题。不读取仓库内部模块。"""

    return DesktopWindow(title=app.name)


def main(argv: list[str] | None = None) -> int:
    """进入事件循环。``--check`` 在显示后立刻退出，供安装验证。"""

    args = sys.argv[1:] if argv is None else argv
    app = App("psi6-minimal")
    window = build(app)
    if "--check" in args:
        from PySide6.QtCore import QTimer

        QTimer.singleShot(0, app.qt_app.quit)
    return app.run(window)


if __name__ == "__main__":
    raise SystemExit(main())
