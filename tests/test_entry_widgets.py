"""DropZone、分段开关、勾选清单、ContentDialog、ImageWell。"""

from __future__ import annotations

from pathlib import Path

from pytestqt.qtbot import QtBot
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QLabel

from psi6.ui.banner import Banner
from psi6.ui.buttons import ghost_button, link_button, text_button
from psi6.ui.check_list import CheckItem, CheckList
from psi6.ui.content_dialog import ContentDialog
from psi6.ui.drop_zone import DropZone
from psi6.ui.image_well import IconPreview, ImageWell
from psi6.ui.segmented import SegmentedControl


def test_drop_zone_filters_and_click(qtbot: QtBot, tmp_path: Path) -> None:
    script = tmp_path / "main.py"
    script.write_text("print(1)\n", encoding="utf-8")
    other = tmp_path / "note.txt"
    other.write_text("x", encoding="utf-8")
    zone = DropZone("拖入脚本", filters="Python (*.py)", browse_on_click=False, size="hero")
    qtbot.addWidget(zone)
    seen: list[list[Path]] = []
    clicks: list[int] = []
    zone.files_dropped.connect(seen.append)
    zone.clicked.connect(lambda: clicks.append(1))
    zone.ingest([script, other])
    assert seen == [[script]]
    assert zone.minimumHeight() >= 140
    qtbot.mouseClick(zone, Qt.MouseButton.LeftButton)
    assert clicks == [1]


def test_segmented_control_changes_index(qtbot: QtBot) -> None:
    control = SegmentedControl(("自己测试", "发给同事", "正式发布"))
    qtbot.addWidget(control)
    assert control.count() == 3
    assert control.index() == 0
    seen: list[int] = []
    control.changed.connect(seen.append)
    control.set_index(2)
    assert control.index() == 2
    assert control.label() == "正式发布"
    control._buttons[1].click()
    assert seen[-1] == 1


def test_segmented_requires_two_labels() -> None:
    try:
        SegmentedControl(("只有一项",))
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_banner_actions_fire(qtbot: QtBot) -> None:
    banner = Banner()
    qtbot.addWidget(banner)
    hits: list[str] = []
    banner.set_notice("缺解释器", tone="warning", actions=[("排除", lambda: hits.append("skip"))])
    assert banner.isVisible()
    assert len(banner._actions) == 1
    banner._actions[0].click()
    assert hits == ["skip"]
    banner.clear()
    assert not banner.isVisible()
    assert banner._actions == []


def test_check_list_toggle(qtbot: QtBot) -> None:
    listing = CheckList()
    qtbot.addWidget(listing)
    listing.set_items(
        [
            CheckItem("a", "main.py", "入口"),
            CheckItem("b", "secrets.env", "密钥", checked=False),
        ]
    )
    events: list[tuple[str, bool]] = []
    listing.toggled.connect(lambda key, on: events.append((key, on)))
    assert listing.checked_ids() == ["a"]
    listing.set_checked("b", True)
    assert ("b", True) in events
    assert set(listing.checked_ids()) == {"a", "b"}


def test_content_dialog_is_themed(qtbot: QtBot) -> None:
    body = QLabel("粘贴草稿")
    dialog = ContentDialog("帮助", body, primary="知道了", secondary="关闭")
    qtbot.addWidget(dialog)
    assert dialog.objectName() == "psi6ContentDialog"
    assert dialog._primary.objectName() == "psi6Primary"
    assert dialog._secondary is not None
    assert dialog._secondary.objectName() == "psi6Ghost"


def test_image_well_loads_png(qtbot: QtBot, tmp_path: Path) -> None:
    image = tmp_path / "app.png"
    canvas = QImage(8, 8, QImage.Format.Format_ARGB32)
    canvas.fill(0xFF35597A)
    assert canvas.save(str(image))
    well = ImageWell()
    qtbot.addWidget(well)
    assert IconPreview is ImageWell
    seen: list[Path | None] = []
    well.path_changed.connect(seen.append)
    well.set_path(image)
    assert well.path() == image
    assert seen[-1] == image
    well.clear()
    assert well.path() is None


def test_ghost_and_text_alias() -> None:
    assert ghost_button("返回").objectName() == "psi6Ghost"
    assert text_button("打开位置").objectName() == "psi6Link"
    assert link_button is text_button
