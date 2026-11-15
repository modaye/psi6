"""骨架屏：半宽渐变扫光，减少动效时只留底色。"""

from __future__ import annotations

from pathlib import Path

from pytestqt.qtbot import QtBot

from psi6 import App
from psi6.ui import motion
from psi6.ui.skeleton import Skeleton


def _pixel(image, widget, x: int, y: int):
    """按逻辑坐标取色。高分屏的 grab 比控件宽。"""

    scale = image.width() / widget.width()
    return image.pixelColor(int((x + 0.5) * scale), int((y + 0.5) * scale))


def test_shimmer_is_a_soft_band(qtbot: QtBot, tmp_path: Path) -> None:
    """高光中段比肩部亮，肩部比带外的底色亮。不是一根等亮的色条。"""

    app = App("psi6-skeleton-band", theme="graphite", config_root=tmp_path)
    del app
    bar = Skeleton(160, 14)
    qtbot.addWidget(bar)
    bar.show()
    motion.stop(bar, "shimmer")
    bar.setProperty("shimmer", 0.5)
    image = bar.grab().toImage()
    edge = _pixel(image, bar, 8, 7)
    shoulder = _pixel(image, bar, 52, 7)
    peak = _pixel(image, bar, 80, 7)
    assert peak.red() > shoulder.red() > edge.red()


def test_reduced_motion_leaves_the_base(qtbot: QtBot, tmp_path: Path) -> None:
    """减少动效时不启动循环，整条都是底色。"""

    app = App("psi6-skeleton-still", theme="light", config_root=tmp_path)
    app.set_reduced_motion(True)
    bar = Skeleton(160, 14)
    qtbot.addWidget(bar)
    bar.show()
    qtbot.wait(40)
    assert bar.property("shimmer") == 0.0
    image = bar.grab().toImage()
    left = _pixel(image, bar, 8, 7)
    middle = _pixel(image, bar, 80, 7)
    assert abs(left.red() - middle.red()) <= 2


def test_square_with_half_radius_is_a_circle(qtbot: QtBot, tmp_path: Path) -> None:
    """边长一半的半径把头像裁成圆，角上没有底色。"""

    app = App("psi6-skeleton-circle", theme="graphite", config_root=tmp_path)
    del app
    avatar = Skeleton(40, 40, radius=20)
    qtbot.addWidget(avatar)
    avatar.show()
    motion.stop(avatar, "shimmer")
    avatar.setProperty("shimmer", 0.0)
    image = avatar.grab().toImage()
    center = _pixel(image, avatar, 20, 20)
    corner = _pixel(image, avatar, 1, 1)
    assert center.alpha() > 200
    assert corner.alpha() < 40
