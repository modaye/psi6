"""示例画廊与其三个场景用例的冒烟测试。"""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QPushButton, QWidget

from psi6 import App
from psi6.examples import file_index, minimal, task_job, task_status
from psi6.examples.gallery import (
    GalleryWindow,
    build_chat,
    build_dashboard,
    build_settings,
)
from psi6.examples.kit import KitWindow
from psi6.ui.chat import Composer
from psi6.ui.tab_view import TabView
from psi6.ui.workspace import Workspace


@pytest.fixture
def app(qtbot):
    test_app = App("test-gallery", theme="light")
    _ = test_app.qt_app  # 确保 QApplication 与 token 就绪
    return test_app


def test_gallery_window_builds(app, qtbot) -> None:
    window = GalleryWindow(app)
    qtbot.add_widget(window)
    # 主题切换：深色 / 紧凑 / 浅色
    window._on_theme(1)
    window._on_theme(2)
    window._on_theme(0)


def test_examples_build(app, qtbot) -> None:
    for builder in (
        lambda: minimal.build(app),
        lambda: file_index.build(app),
        lambda: task_job.build(app),
        lambda: task_status.build(app)[0],
        lambda: KitWindow(app),
    ):
        window = builder()
        qtbot.add_widget(window)
        window.close()


def test_dashboard_builds(app, qtbot) -> None:
    qtbot.add_widget(build_dashboard(app))


def test_settings_builds(app, qtbot) -> None:
    qtbot.add_widget(build_settings(app))


def test_chat_send(app, qtbot) -> None:
    window = build_chat(app)
    qtbot.add_widget(window)
    composer = window.findChild(Composer)
    assert composer is not None
    composer.sent.emit("后台任务怎么接状态栏？")
    qtbot.wait(900)


def test_kit_density_buttons_switch_mode(app, qtbot) -> None:
    """组件目录主题页要有可用的手动密度入口，状态随信号更新。"""

    window = KitWindow(app)
    qtbot.add_widget(window)
    bar = window.findChild(QWidget, "psi6DensityModes")
    assert bar is not None
    buttons = {button.property("densityMode"): button for button in bar.findChildren(QPushButton)}
    assert set(buttons) == {"auto", "modern", "compact"}
    assert window._density_note is not None

    buttons["compact"].click()
    assert app.density_mode == "compact"
    assert app.tokens.control_height == 30
    assert "compact" in window._density_note.text()

    buttons["auto"].click()
    assert app.density_mode == "auto"
    assert "auto" in window._density_note.text()

    seen: list[str] = []
    app.density_changed.connect(seen.append)
    window.resize(500, 400)
    app._window = window
    app._bind_density()
    app._recompute_density()
    assert seen == ["compact"]
    assert "紧凑尺寸" in window._density_note.text()
    assert str(app.tokens.control_height) in window._density_note.text()


def test_kit_focus_ring_buttons_toggle(app, qtbot) -> None:
    """组件目录主题页提供焦点环开关，状态说明随切换更新。"""

    window = KitWindow(app)
    qtbot.add_widget(window)
    bar = window.findChild(QWidget, "psi6FocusRingModes")
    assert bar is not None
    buttons = {
        bool(button.property("focusRing")): button for button in bar.findChildren(QPushButton)
    }
    assert set(buttons) == {False, True}
    assert window._focus_note is not None

    buttons[True].click()
    assert app.focus_ring is True
    assert "开启" in window._focus_note.text()
    assert f"border: {app.tokens.focus_ring_width}px solid" in app.qt_app.styleSheet()

    buttons[False].click()
    assert app.focus_ring is False
    assert "关闭" in window._focus_note.text()
    assert f"border: {app.tokens.focus_ring_width}px solid" not in app.qt_app.styleSheet()


def test_kit_workbench_page_records_and_restores_layout(app, qtbot) -> None:
    """「多视图」页能增删文档、显隐分栏，并把标签顺序与布局恢复回来。"""

    window = KitWindow(app)
    qtbot.add_widget(window)
    window.show_page("workbench")

    tabs = window.findChild(TabView, "psi6KitTabs")
    work = window.findChild(Workspace, "psi6KitWorkbench")
    assert tabs is not None
    assert work is not None
    assert tabs.count() == 2
    assert work.visible_panes() == ["left", "center", "right"]

    bar = window.findChild(QWidget, "psi6WorkbenchActions")
    assert bar is not None
    buttons = {
        button.property("workbenchAction"): button for button in bar.findChildren(QPushButton)
    }
    assert set(buttons) == {"打开文档", "关闭当前", "显隐右栏", "记录布局", "恢复布局"}

    buttons["打开文档"].click()
    assert tabs.count() == 3
    buttons["记录布局"].click()
    saved_keys = tabs.keys()

    buttons["关闭当前"].click()
    assert tabs.count() == 2
    buttons["显隐右栏"].click()
    assert work.visible_panes() == ["left", "center"]

    buttons["恢复布局"].click()
    assert tabs.keys() == saved_keys
    assert tabs.count() == 3
    assert tabs.title(saved_keys[0]) == "文档 1"
    assert work.visible_panes() == ["left", "center", "right"]
