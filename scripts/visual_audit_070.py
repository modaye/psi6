"""0.7.0 阶段一：在真实窗口里截 kit 与 gallery 的改前画面。

不改主题和控件。截图走当前屏幕的 ``QScreen.grabWindow``，窗口由 ``App.run`` 显示。
``--pass dpi`` 由主进程带着 ``QT_SCALE_FACTOR=1.5`` 拉起，用来看 150% 逻辑缩放。
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QEventLoop, Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QPushButton, QWidget

from psi6 import App
from psi6.examples.file_index import build as build_file_index
from psi6.examples.gallery import GalleryWindow, build_chat, build_dashboard, build_settings
from psi6.examples.kit import KitWindow
from psi6.examples.minimal import build as build_minimal
from psi6.examples.task_job import build as build_task

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "plans" / "audit-0.7.0" / "before"

THEMES = ("light", "modern-dark", "compact", "compact-dark")
KIT_PAGES = (
    "buttons",
    "inputs",
    "choice",
    "nav",
    "data",
    "shell",
    "formlab",
    "inspect",
    "dense",
    "feedback",
    "window",
    "states",
    "theme",
    "workbench",
    "compose",
)
NARROW_PAGES = ("buttons", "data", "formlab", "workbench")
DPI_PAGES = (
    "buttons",
    "inputs",
    "choice",
    "nav",
    "states",
    "data",
    "feedback",
    "formlab",
    "workbench",
    "compose",
)
DPI_THEMES = ("light", "modern-dark", "compact-dark")
SCENE_BUILDERS = (
    ("dashboard", build_dashboard),
    ("settings", build_settings),
    ("chat", build_chat),
    ("file-index", build_file_index),
    ("task", build_task),
    ("minimal", build_minimal),
)


@dataclass
class Shot:
    """一张已经落盘的截图。"""

    path: str
    theme: str
    target: str
    source: str
    width: int
    height: int
    focus_ring: bool
    control_height: int
    radius: int
    color_bg: str
    color_primary: str
    clipped: bool


class VisualAudit:
    """按主题和页面驱动已显示的窗口，并把屏幕上的窗口画下来。"""

    def __init__(self, app: App, out: Path, *, dpi_pass: bool, scenes: bool) -> None:
        self.app = app
        self.out = out
        self.dpi_pass = dpi_pass
        self.scenes = scenes
        self.shots: list[Shot] = []
        self.errors: list[str] = []
        self.kit: KitWindow | None = None

    def run_catalog(self, window: KitWindow) -> None:
        """截组件目录：四种组合、窄窗口，以及焦点环关闭时的按钮页。"""

        self.kit = window
        self._place(window)
        self._pump(320)
        pages = DPI_PAGES if self.dpi_pass else KIT_PAGES
        themes = DPI_THEMES if self.dpi_pass else THEMES
        folder = "dpi150/kit" if self.dpi_pass else "kit"
        for theme in themes:
            self._theme(theme)
            for page in pages:
                self._page(page)
                self._shoot(window, f"{folder}/{theme}/{page}.png", theme, page)
                if page == "buttons" and theme in {"light", "modern-dark"}:
                    self._focus_start()
                    self._pump(120)
                    self._shoot(window, f"{folder}/{theme}/buttons-focus.png", theme, "buttons-focus")
        if self.dpi_pass:
            return
        self._theme("light")
        self._narrow(True)
        for theme in THEMES:
            self._theme(theme)
            for page in NARROW_PAGES:
                self._page(page)
                self._shoot(window, f"kit-narrow/{theme}/{page}.png", theme, f"narrow-{page}")
        self._narrow(False)
        self._theme("light")
        self._page("buttons")
        self.app.set_focus_ring(False)
        self._focus_start()
        self._pump(180)
        self._shoot(window, "focus-off/light/buttons-focus.png", "light", "focus-off")
        self.app.set_focus_ring(True)

    def run_gallery(self) -> None:
        """截画廊首页和组合场景。画廊进程默认不画焦点环，这里保持关闭。"""

        self.app.set_focus_ring(False)
        if self.kit is not None:
            self.kit.hide()
        gallery = GalleryWindow(self.app)
        self._place(gallery)
        gallery.show()
        themes = DPI_THEMES if self.dpi_pass else THEMES
        folder = "dpi150/gallery" if self.dpi_pass else "gallery"
        for theme in themes:
            self._theme(theme)
            self._shoot(gallery, f"{folder}/{theme}/home.png", theme, "gallery")
        gallery.close()
        if not self.scenes:
            return
        scene_names = ("dashboard", "settings", "file-index") if self.dpi_pass else None
        builders = SCENE_BUILDERS
        if scene_names is not None:
            builders = tuple(item for item in SCENE_BUILDERS if item[0] in scene_names)
        scene_folder = "dpi150/scenes" if self.dpi_pass else "scenes"
        for theme in themes:
            self._theme(theme)
            for name, builder in builders:
                window = self._scene(name, builder)
                if window is None:
                    continue
                self._shoot(window, f"{scene_folder}/{theme}/{name}.png", theme, name)
                window.close()
                self._pump(40)

    def write_manifest(self, screen_info: dict[str, object]) -> None:
        """把截图清单和屏幕参数写到输出目录。"""

        self.out.mkdir(parents=True, exist_ok=True)
        name = "manifest-dpi.json" if self.dpi_pass else "manifest.json"
        path = self.out / name
        previous: list[dict[str, object]] = []
        if path.exists():
            loaded = json.loads(path.read_text(encoding="utf-8"))
            shots = loaded.get("shots")
            if isinstance(shots, list):
                previous = [item for item in shots if isinstance(item, dict)]
        by_path = {str(item["path"]): item for item in previous if "path" in item}
        for shot in self.shots:
            by_path[shot.path] = shot.__dict__
        payload = {
            "label": "before",
            "pass": "full",
            "screen": screen_info,
            "shots": [by_path[key] for key in sorted(by_path)],
            "errors": self.errors,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _theme(self, theme: str) -> None:
        self.app.set_theme(theme)
        self._pump(280)

    def _page(self, page_id: str) -> None:
        if self.kit is None:
            return
        self.kit.show_page(page_id)
        self._pump(80)

    def _narrow(self, enabled: bool) -> None:
        if self.kit is None:
            return
        if enabled:
            self.kit.setMinimumSize(640, 420)
            self.kit.resize(700, 520)
        else:
            self.kit.setMinimumSize(0, 0)
            self._place(self.kit)
        self._pump(360)

    def _focus_start(self) -> None:
        if self.kit is None:
            return
        for button in self.kit.findChildren(QPushButton):
            if button.text() == "开始" and button.isVisible():
                button.setFocus(Qt.FocusReason.TabFocusReason)
                return

    def _scene(self, name: str, builder: object) -> QWidget | None:
        try:
            built = builder(self.app)  # type: ignore[operator]
        except Exception as exc:  # 一个场景失败不应中断整批审计
            self.errors.append(f"{name}: {exc}")
            return None
        window = built[0] if isinstance(built, tuple) else built
        if not isinstance(window, QWidget):
            self.errors.append(f"{name}: 没有窗口")
            return None
        self._place(window)
        window.show()
        window.raise_()
        window.activateWindow()
        self._pump(240)
        return window

    def _place(self, window: QWidget) -> None:
        screen = window.screen() or QApplication.primaryScreen()
        if screen is None:
            return
        avail = screen.availableGeometry()
        width = min(max(window.width(), 960), max(640, avail.width() - 32))
        height = min(max(window.height(), 640), max(480, avail.height() - 48))
        if self.dpi_pass:
            width = min(width, 1040)
            height = min(height, 680)
        window.resize(width, height)
        window.move(avail.x() + 16, avail.y() + 16)

    def _shoot(self, window: QWidget, relative: str, theme: str, target: str) -> None:
        window.raise_()
        window.activateWindow()
        self._pump(60)
        path = self.out / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        source, pixmap = _grab(window)
        if not pixmap.save(str(path), "PNG"):
            self.errors.append(f"无法保存 {relative}")
            return
        tokens = self.app.tokens
        page = self.kit.shell.current_id() if self.kit is not None and window is self.kit else ""
        clipped = False
        if page and self.kit is not None:
            current = self.kit.shell._pages.get(page)  # 审计需要知道内容有没有被栈裁掉
            if current is not None:
                clipped = current.sizeHint().height() > current.height() + 24
        self.shots.append(
            Shot(
                path=relative.replace("\\", "/"),
                theme=theme,
                target=target,
                source=source,
                width=pixmap.width(),
                height=pixmap.height(),
                focus_ring=self.app.focus_ring,
                control_height=tokens.control_height,
                radius=tokens.radius,
                color_bg=tokens.color_bg,
                color_primary=tokens.color_primary,
                clipped=clipped,
            )
        )
        print(f"{source:6} {pixmap.width()}x{pixmap.height()} {relative}", flush=True)

    def _pump(self, milliseconds: int) -> None:
        loop = QEventLoop()
        QTimer.singleShot(milliseconds, loop.quit)
        loop.exec()


def _grab(window: QWidget) -> tuple[str, QPixmap]:
    """优先抓屏幕上的真实窗口。

    自绘标题栏窗口开了透明背景，``grabWindow`` 在 Windows 上会得到一张黑图。
    这种图作废，改抓已经显示出来的控件绘制结果，并在清单里写成 ``widget``。
    """

    screen = window.screen() or QApplication.primaryScreen()
    pixmap = QPixmap()
    if screen is not None:
        pixmap = screen.grabWindow(int(window.winId()))
    if pixmap.isNull() or pixmap.width() < 80 or pixmap.height() < 80 or _mostly_black(pixmap):
        painted = window.grab()
        return "widget", painted
    return "screen", pixmap


def _mostly_black(pixmap: QPixmap) -> bool:
    """采样判断抓图是不是失败的黑帧。正常深色主题不会整窗都接近纯黑。"""

    image = pixmap.toImage()
    if image.isNull():
        return True
    black = 0
    total = 0
    step_x = max(1, image.width() // 48)
    step_y = max(1, image.height() // 48)
    for y in range(0, image.height(), step_y):
        for x in range(0, image.width(), step_x):
            color = image.pixelColor(x, y)
            total += 1
            if color.alpha() > 240 and color.red() < 8 and color.green() < 8 and color.blue() < 8:
                black += 1
    return total == 0 or black / total > 0.9


def _screen_info() -> dict[str, object]:
    screen = QApplication.primaryScreen()
    geometry = screen.availableGeometry() if screen is not None else None
    return {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "qt_scale_factor": os.environ.get("QT_SCALE_FACTOR", ""),
        "device_pixel_ratio": screen.devicePixelRatio() if screen is not None else None,
        "available": [geometry.width(), geometry.height()] if geometry is not None else None,
        "logical_dpi": screen.logicalDotsPerInch() if screen is not None else None,
    }


def _launch_dpi_pass(*, scenes: bool) -> None:
    """另起进程做 150% 缩放。缩放因子必须在 QApplication 之前生效。"""

    env = os.environ.copy()
    env["QT_SCALE_FACTOR"] = "1.5"
    env.pop("QT_QPA_PLATFORM", None)
    command = [sys.executable, str(Path(__file__).resolve()), "--pass", "dpi"]
    if not scenes:
        command.append("--no-scenes")
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        check=False,
    )
    if completed.returncode != 0:
        print(f"150% 审计进程退出码 {completed.returncode}", flush=True)


def main(argv: list[str] | None = None) -> int:
    """打开真实窗口，截完后退出。"""

    parser = argparse.ArgumentParser(description="截 psi6 0.7.0 视觉审计的改前画面")
    parser.add_argument("--pass", dest="which", choices=("full", "dpi", "kit"), default="full")
    parser.add_argument("--no-scenes", action="store_true")
    args = parser.parse_args(argv)
    dpi_pass = args.which == "dpi"
    scenes = args.which != "kit" and not args.no_scenes
    config_root = Path(tempfile.mkdtemp(prefix="psi6-audit-"))
    app = App(
        "psi6-audit-dpi" if dpi_pass else "psi6-audit",
        theme="light",
        config_root=config_root,
        density="auto",
        focus_ring=True,
    )
    app.qt_app.setQuitOnLastWindowClosed(False)
    window = KitWindow(app)
    audit = VisualAudit(app, OUT, dpi_pass=dpi_pass, scenes=scenes)

    def start() -> None:
        try:
            audit.run_catalog(window)
            audit.run_gallery()
        except Exception as exc:  # 留下已截到的部分，便于看出停在哪一页
            audit.errors.append(repr(exc))
            print(f"审计中断: {exc}", flush=True)
        finally:
            audit.write_manifest(_screen_info())
            print(f"截图 {len(audit.shots)} 张，错误 {len(audit.errors)}", flush=True)
            app.qt_app.quit()

    QTimer.singleShot(0, start)
    code = app.run(window, tray=False, restore_geometry=False, float_ball=False)
    if args.which == "full":
        _launch_dpi_pass(scenes=True)
    elif args.which == "kit":
        _launch_dpi_pass(scenes=False)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
