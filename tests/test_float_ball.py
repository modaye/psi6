"""悬浮球：单击切换窗口、拖动留在屏幕内、右键菜单和宿主销毁。"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from pytestqt.qtbot import QtBot

from psi6.theme.runtime import token_int
from psi6.ui.desktop_window import DesktopWindow
from psi6.ui.float_ball import FloatBall
from psi6.ui.window_presence import toggle_window, window_is_presented


def _mouse(ball: FloatBall, kind: QEvent.Type, global_pos: QPoint, *, button, buttons) -> None:
    local = QPoint(ball.width() // 2, ball.height() // 2)
    event = QMouseEvent(
        kind,
        QPointF(local),
        QPointF(global_pos),
        button,
        buttons,
        Qt.KeyboardModifier.NoModifier,
    )
    if kind == QEvent.Type.MouseButtonPress:
        ball.mousePressEvent(event)
    elif kind == QEvent.Type.MouseMove:
        ball.mouseMoveEvent(event)
    else:
        ball.mouseReleaseEvent(event)


def _click(ball: FloatBall) -> None:
    origin = QPoint(400, 400)
    _mouse(
        ball,
        QEvent.Type.MouseButtonPress,
        origin,
        button=Qt.MouseButton.LeftButton,
        buttons=Qt.MouseButton.LeftButton,
    )
    _mouse(
        ball,
        QEvent.Type.MouseButtonRelease,
        origin,
        button=Qt.MouseButton.LeftButton,
        buttons=Qt.MouseButton.NoButton,
    )


def test_click_toggles_the_host_window(qtbot: QtBot) -> None:
    window = DesktopWindow(title="悬浮球")
    qtbot.addWidget(window)
    window.show()
    ball = FloatBall(window, tooltip="psi6", icon="grid")
    qtbot.addWidget(ball)
    assert window.close_to_tray is False
    _click(ball)
    assert not window.isVisible()
    _click(ball)
    assert window_is_presented(window)


def test_toggle_restores_a_minimized_window(qtbot: QtBot) -> None:
    window = DesktopWindow(title="最小化")
    qtbot.addWidget(window)
    window.show()
    window.setWindowState(Qt.WindowState.WindowMinimized)
    assert window.isMinimized()
    toggle_window(window)
    assert window_is_presented(window)


def test_drag_moves_then_stays_on_screen(qtbot: QtBot) -> None:
    window = DesktopWindow(title="拖动")
    qtbot.addWidget(window)
    window.show()
    ball = FloatBall(window, tooltip="psi6", icon="grid", resident=True)
    qtbot.addWidget(ball)
    ball.place_default()
    ball.show()
    assert window.close_to_tray is True
    start = ball.pos()
    press_at = QPoint(100, 100)
    _mouse(
        ball,
        QEvent.Type.MouseButtonPress,
        press_at,
        button=Qt.MouseButton.LeftButton,
        buttons=Qt.MouseButton.LeftButton,
    )
    _mouse(
        ball,
        QEvent.Type.MouseMove,
        press_at + QPoint(48, 12),
        button=Qt.MouseButton.NoButton,
        buttons=Qt.MouseButton.LeftButton,
    )
    assert ball.pos() == start + QPoint(48, 12)
    _mouse(
        ball,
        QEvent.Type.MouseButtonRelease,
        press_at + QPoint(48, 12),
        button=Qt.MouseButton.LeftButton,
        buttons=Qt.MouseButton.NoButton,
    )
    assert window.isVisible()
    _mouse(
        ball,
        QEvent.Type.MouseButtonPress,
        QPoint(0, 0),
        button=Qt.MouseButton.LeftButton,
        buttons=Qt.MouseButton.LeftButton,
    )
    _mouse(
        ball,
        QEvent.Type.MouseMove,
        QPoint(-4000, -4000),
        button=Qt.MouseButton.NoButton,
        buttons=Qt.MouseButton.LeftButton,
    )
    _mouse(
        ball,
        QEvent.Type.MouseButtonRelease,
        QPoint(-4000, -4000),
        button=Qt.MouseButton.LeftButton,
        buttons=Qt.MouseButton.NoButton,
    )
    screen = ball.screen() or window.screen()
    assert screen is not None
    assert screen.availableGeometry().contains(ball.geometry().center())
    side = max(token_int("control_height_sm", 28), token_int("control_height", 36))
    assert ball.width() == side
    assert ball.height() == side


def test_menu_and_status_follow_the_window(qtbot: QtBot, monkeypatch) -> None:
    window = DesktopWindow(title="菜单")
    qtbot.addWidget(window)
    window.show()
    ball = FloatBall(window, tooltip="psi6", icon="grid")
    qtbot.addWidget(ball)
    seen: list[str] = []
    ball.add_action("暂停", lambda: seen.append("pause"), icon="pause")
    labels = [item.label for item in ball.menu_actions()]
    assert labels == ["显示窗口", "隐藏窗口", "", "暂停", "", "退出"]
    hide = ball.menu_actions()[1]
    assert hide.enabled
    assert hide.callback is not None
    hide.callback()
    assert not window.isVisible()
    show = ball.menu_actions()[0]
    assert show.enabled
    assert show.callback is not None
    show.callback()
    assert window.isVisible()
    pause = next(item for item in ball.menu_actions() if item.label == "暂停")
    assert pause.callback is not None
    pause.callback()
    assert seen == ["pause"]
    ball.set_status("正在扫描")
    assert ball.status == "正在扫描"
    assert "正在扫描" in ball.toolTip()
    calls: list[object] = []
    monkeypatch.setattr("psi6.ui.float_ball.quit_application", lambda host: calls.append(host))
    ball.quit()
    assert not ball.isVisible()
    assert calls == [window]


def test_destroyed_host_hides_the_ball(qtbot: QtBot) -> None:
    window = DesktopWindow(title="销毁")
    qtbot.addWidget(window)
    ball = FloatBall(window, tooltip="psi6")
    qtbot.addWidget(ball)
    ball.show()
    window.deleteLater()
    qtbot.waitUntil(lambda: not ball.isVisible())
    _click(ball)
    assert not ball.isVisible()
