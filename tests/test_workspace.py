"""工作区：省略空栏、记住分栏宽度、面包屑、面板显隐与布局持久化。"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import QLabel, QPushButton, QSplitter
from pytestqt.qtbot import QtBot

from psi6.runtime.config import ConfigStore
from psi6.ui.app_shell import AppShell, NavDestination
from psi6.ui.buttons import ghost_button, primary_button
from psi6.ui.workspace import Breadcrumb, Workspace


def test_set_pane_does_not_open_a_window(qtbot: QtBot) -> None:
    """分栏先挂进布局再显示。无父对象时的 show() 会先弹出独立窗口。"""

    flashed: list[QLabel] = []

    class _Spy(QObject):
        def eventFilter(self, obj, event) -> bool:  # type: ignore[override]
            if event.type() == QEvent.Type.Show and obj.isWindow() and obj.parentWidget() is None:
                flashed.append(obj)
            return False

    spy = _Spy()
    pane = QLabel("中")
    pane.installEventFilter(spy)
    work = Workspace()
    qtbot.addWidget(work)
    work.set_pane("center", pane)
    work.set_pane("right", QLabel("右"))
    assert flashed == []
    assert pane.parentWidget() is work._splitter
    assert not pane.isWindow()
    assert pane.windowHandle() is None


def test_workspace_omits_panes_that_were_not_set(qtbot: QtBot) -> None:
    work = Workspace()
    qtbot.addWidget(work)
    work.resize(640, 320)
    work.show()
    work.set_pane("center", QLabel("主区"))
    assert len(work.sizes()) == 1


def test_replacing_a_pane_detaches_the_old_widget(qtbot: QtBot) -> None:
    work = Workspace()
    qtbot.addWidget(work)
    first = QLabel("旧")
    work.set_pane("center", first)
    second = QLabel("新")
    work.set_pane("center", second)
    assert first.parent() is None
    assert not first.isVisible()
    assert second.parent() is not None


def test_splitter_keeps_the_width_after_it_moves(qtbot: QtBot) -> None:
    work = Workspace()
    qtbot.addWidget(work)
    work.resize(600, 300)
    work.show()
    qtbot.waitExposed(work)
    work.set_pane("left", QLabel("左"))
    work.set_pane("center", QLabel("中"))
    splitter = work.findChild(QSplitter)
    assert splitter is not None
    before = work.sizes()[0]
    splitter.setSizes([120, 480])
    qtbot.waitUntil(lambda: work.sizes()[0] < before)
    qtbot.mouseRelease(splitter.handle(1), Qt.MouseButton.LeftButton)
    remembered = work.sizes()
    work.set_pane("center", QLabel("中二"))
    assert work.sizes() == remembered


def test_workspace_spacing_follows_density(qtbot: QtBot, tmp_path: Path) -> None:
    from psi6 import App
    from psi6.theme.builtin import Compact

    app = App("psi6-ws-density", config_root=tmp_path, theme="light")
    work = Workspace()
    qtbot.addWidget(work)
    work.show()
    assert work.layout() is not None
    assert work.layout().contentsMargins().left() == app.tokens.space_lg
    app.set_theme(Compact)
    qtbot.waitUntil(
        lambda: work.layout() is not None and work.layout().contentsMargins().left() == 10
    )


def test_stretch_keeps_the_center_wider_until_the_user_drags(qtbot: QtBot) -> None:
    work = Workspace()
    qtbot.addWidget(work)
    work.resize(800, 320)
    work.set_pane("center", QLabel("中"))
    work.set_pane("right", QLabel("右"))
    work.set_stretch("center", 3)
    work.set_stretch("right", 1)
    work.show()
    qtbot.waitExposed(work)
    qtbot.waitUntil(lambda: work.sizes()[0] > work.sizes()[1] * 2)


def test_appshell_can_sit_in_the_center_pane(qtbot: QtBot) -> None:
    work = Workspace()
    qtbot.addWidget(work)
    shell = AppShell((NavDestination("home", "概览", "check"),))
    shell.add_page("home", QLabel("概览"))
    work.set_pane("center", shell)
    work.resize(640, 360)
    work.show()
    assert work.findChild(AppShell) is shell
    assert len(work.sizes()) == 1


def test_breadcrumb_marks_the_last_item_as_current(qtbot: QtBot) -> None:
    crumb = Breadcrumb(["文件", "索引", "结果"])
    qtbot.addWidget(crumb)
    assert crumb.crumbs() == ["文件", "索引", "结果"]
    current = [
        label
        for label in crumb.findChildren(QLabel)
        if label.objectName() == "psi6BreadcrumbCurrent"
    ]
    assert [label.text() for label in current] == ["结果"]


def test_toolbar_buttons_can_take_focus(qtbot: QtBot) -> None:
    work = Workspace()
    qtbot.addWidget(work)
    work.toolbar.add_primary(primary_button("开始"))
    work.toolbar.add_secondary(ghost_button("取消"))
    work.show()
    buttons = work.toolbar.findChildren(QPushButton)
    assert len(buttons) == 2
    buttons[0].setFocus(Qt.FocusReason.TabFocusReason)
    qtbot.keyClick(buttons[0], Qt.Key.Key_Tab)
    assert work.focusWidget() is buttons[1]

    shell = AppShell(
        (
            NavDestination("home", "概览", "check"),
            NavDestination("detail", "明细", "list"),
        )
    )
    qtbot.addWidget(shell)
    shell.add_page("home", QLabel("概览"))
    shell.add_page("detail", QLabel("明细"))
    shell.resize(640, 360)
    shell.show()
    qtbot.waitExposed(shell)
    nav = shell.sidebar.findChildren(QPushButton)
    assert len(nav) >= 2
    nav[0].setFocus(Qt.FocusReason.TabFocusReason)
    assert shell.focusWidget() is nav[0]


def _three_panes(qtbot: QtBot) -> tuple[Workspace, list[QLabel]]:
    work = Workspace()
    qtbot.addWidget(work)
    labels = [QLabel(text) for text in ("左", "中", "右")]
    for place, label in zip(("left", "center", "right"), labels, strict=True):
        work.set_pane(place, label)
    work.resize(900, 320)
    work.show()
    qtbot.waitExposed(work)
    return work, labels


def test_pane_visibility_hides_without_destroying(qtbot: QtBot) -> None:
    work, labels = _three_panes(qtbot)
    assert work.visible_panes() == ["left", "center", "right"]
    assert work.is_pane_visible("center") is True

    work.set_pane_visible("center", False)
    assert work.visible_panes() == ["left", "right"]
    assert work.is_pane_visible("center") is False
    assert len(work.sizes()) == 2
    # 隐藏只是摘下来，控件本体还在，随时能再显示。
    assert labels[1].parent() is None
    assert not labels[1].isVisible()

    work.set_pane_visible("center", True)
    assert work.visible_panes() == ["left", "center", "right"]
    assert labels[1].parent() is not None
    assert len(work.sizes()) == 3


def test_toggling_a_pane_emits_layout_changed_only_when_it_changes(qtbot: QtBot) -> None:
    work, _ = _three_panes(qtbot)
    changes: list[bool] = []
    work.layout_changed.connect(lambda: changes.append(True))

    work.set_pane_visible("right", False)
    work.set_pane_visible("right", False)
    work.set_pane_visible("right", True)
    assert len(changes) == 2


def test_unknown_place_is_rejected(qtbot: QtBot) -> None:
    work = Workspace()
    qtbot.addWidget(work)
    with pytest.raises(ValueError):
        work.set_pane_visible("top", False)
    with pytest.raises(ValueError):
        work.set_pane("top", QLabel("上"))


def test_state_records_hidden_and_sizes_by_place_name(qtbot: QtBot) -> None:
    work, _ = _three_panes(qtbot)
    work.set_stretch("center", 3)
    work.set_pane_visible("right", False)

    payload = work.state()
    assert payload["hidden"] == ["right"]
    assert set(payload["sizes"]) == {"left", "center"}
    assert all(isinstance(value, int) and value > 0 for value in payload["sizes"].values())
    assert payload["dragged"] is False
    assert set(payload["sizes"]) == set(work.visible_panes())


def test_set_state_restores_hidden_panes_and_keeps_widths_by_name(qtbot: QtBot) -> None:
    work, _ = _three_panes(qtbot)
    work.set_stretch("center", 3)
    saved = work.state()
    assert saved["sizes"]["center"] > saved["sizes"]["left"]

    payload = {"hidden": ["left"], "sizes": dict(saved["sizes"]), "dragged": True}
    work.set_state(payload)
    assert work.visible_panes() == ["center", "right"]
    # 宽度按栏名保存：隐藏 left 后 center / right 不会错拿 left 的值。
    assert work._pane_sizes["left"] == saved["sizes"]["left"]
    assert work._pane_sizes["center"] == saved["sizes"]["center"]
    assert work._pane_sizes["right"] == saved["sizes"]["right"]
    assert set(work.state()["sizes"]) == {"center", "right"}

    work.set_state({"hidden": [], "sizes": saved["sizes"], "dragged": True})
    assert work.visible_panes() == ["left", "center", "right"]
    assert work.sizes()[1] == max(work.sizes())


def test_set_state_ignores_invalid_fields(qtbot: QtBot) -> None:
    work, _ = _three_panes(qtbot)
    work.set_state(
        {
            "hidden": ["left", "ghost", 42],
            "sizes": {"left": -3, "center": "宽", "right": True, "ghost": 100},
            "dragged": True,
        }
    )
    assert work.visible_panes() == ["center", "right"]
    assert work._pane_sizes == {}
    # 没有有效宽度时 dragged 不生效，回落到按权重分配。
    assert work.state()["dragged"] is False


def test_empty_state_does_not_change_the_layout(qtbot: QtBot) -> None:
    work, _ = _three_panes(qtbot)
    before = work.state()
    work.set_state({})
    assert work.state() == before


def test_save_and_restore_state_via_config_store(qtbot: QtBot, tmp_path: Path) -> None:
    store = ConfigStore(tmp_path)
    work, _ = _three_panes(qtbot)
    work.set_stretch("center", 3)
    work.set_pane_visible("right", False)
    work.save_state(store, "wb")
    assert store.load_data("wb", "layout.json") == work.state()

    other, _ = _three_panes(qtbot)
    assert other.restore_state(store, "wb") is True
    assert other.visible_panes() == ["left", "center"]
    assert other.state()["hidden"] == ["right"]


def test_restore_state_without_file_is_a_noop(qtbot: QtBot, tmp_path: Path) -> None:
    store = ConfigStore(tmp_path)
    work, _ = _three_panes(qtbot)
    assert work.restore_state(store, "wb") is False
    assert work.visible_panes() == ["left", "center", "right"]


def test_state_file_can_be_overridden(qtbot: QtBot, tmp_path: Path) -> None:
    store = ConfigStore(tmp_path)
    work = Workspace(state_file="my-layout.json")
    qtbot.addWidget(work)
    work.set_pane("center", QLabel("中"))
    work.save_state(store, "wb")

    assert store.load_data("wb", "my-layout.json") is not None
    assert store.load_data("wb", "layout.json") is None


def test_dragging_keeps_the_width_of_a_hidden_pane(qtbot: QtBot) -> None:
    work, _ = _three_panes(qtbot)
    splitter = work.findChild(QSplitter)
    assert splitter is not None

    # 先在三栏都可见时拖一次，把 left 的宽度按名字记下来。
    splitter.setSizes([150, 500, 200])
    qtbot.mouseRelease(splitter.handle(1), Qt.MouseButton.LeftButton)
    assert set(work._pane_sizes) == {"left", "center", "right"}
    left_width = work._pane_sizes["left"]
    assert left_width > 0

    # 隐藏 left 后再拖：只更新可见栏，left 之前记下的宽度不能被抹掉。
    work.set_pane_visible("left", False)
    splitter.setSizes([300, 300])
    qtbot.mouseRelease(splitter.handle(1), Qt.MouseButton.LeftButton)
    assert work.state()["dragged"] is True
    assert work._pane_sizes["left"] == left_width


def test_custom_state_file_and_hidden_pane_survive_rebuild(qtbot: QtBot) -> None:
    work, labels = _three_panes(qtbot)
    work.set_pane_visible("left", False)
    work.set_pane("center", QLabel("新的中"))
    assert work.visible_panes() == ["center", "right"]
    assert labels[0].parent() is None
    work.set_state({"hidden": [], "sizes": {}, "dragged": False})
    assert work.visible_panes() == ["left", "center", "right"]
