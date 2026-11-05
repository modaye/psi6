"""Toast 进出场动画与读屏播报的回归测试。"""

from __future__ import annotations

import types

import pytest
from PySide6.QtWidgets import QWidget

import psi6.ui.toast as toast_mod
from psi6.ui.toast import ToastCard, ToastHost


@pytest.fixture
def host(qtbot: object) -> ToastHost:
    window = QWidget()
    qtbot.addWidget(window)  # type: ignore[attr-defined]
    window.show()
    qtbot.waitExposed(window)  # type: ignore[attr-defined]
    return ToastHost(window)


def test_push_reveals_with_fade_animation(host: ToastHost, qtbot: object) -> None:
    """动效开启时，push 触发淡入动画，并最终完全不透明。"""

    card = host.push("已保存", timeout_ms=60000)
    assert card is not None
    qtbot.waitUntil(lambda: card._anim_timer is not None and card._anim_timer.isActive())  # type: ignore[attr-defined]
    qtbot.waitUntil(lambda: card.height() == card.sizeHint().height())  # type: ignore[attr-defined]
    assert card.isVisible()


def test_push_shows_instantly_when_reduced_motion(
    host: ToastHost, qtbot: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """reduced_motion 下不做动画，立刻完全显示。"""

    monkeypatch.setattr(toast_mod, "token_ms", lambda speed: 0)
    card = host.push("已保存", timeout_ms=60000)
    assert card is not None
    assert card._anim_timer is None  # type: ignore[attr-defined]
    assert card._current_h == card.sizeHint().height()  # type: ignore[attr-defined]
    assert card.isVisible()


def test_dismiss_fades_out_before_deletion(host: ToastHost, qtbot: object) -> None:
    """出场动画期间卡片仍可见，动画结束后才从控件树移除。"""

    card = host.push("扫描完成", timeout_ms=60000)
    qtbot.waitUntil(lambda: card.height() == card.sizeHint().height())  # type: ignore[attr-defined]
    assert card in host.findChildren(ToastCard)

    card.dismiss()
    # 出场动画刚开始，卡片仍在淡出、尚未删除
    assert card.isVisible()
    assert card._anim_timer is not None and card._anim_timer.isActive()  # type: ignore[attr-defined]
    assert card in host.findChildren(ToastCard)

    qtbot.waitUntil(lambda: card._gone)  # type: ignore[attr-defined]
    qtbot.waitUntil(lambda: card not in host.findChildren(ToastCard))


def test_dismiss_deletes_without_animation_when_reduced_motion(
    host: ToastHost, qtbot: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """reduced_motion 下出场直接隐藏删除，不启动淡出动画。"""

    monkeypatch.setattr(toast_mod, "token_ms", lambda speed: 0)
    card = host.push("扫描完成", timeout_ms=60000)

    card.dismiss()
    assert card._anim_timer is None  # type: ignore[attr-defined]
    assert not card.isVisible()
    qtbot.waitUntil(lambda: card not in host.findChildren(ToastCard))


def test_push_announces_to_screen_reader(
    host: ToastHost, qtbot: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """push 会设置无障碍名，并向读屏软件播报这条通知。"""

    calls: list[tuple[object, str]] = []
    monkeypatch.setattr(
        toast_mod,
        "QAccessibleAnnouncementEvent",
        lambda widget, message: calls.append((widget, message)),
    )
    monkeypatch.setattr(
        toast_mod,
        "QAccessible",
        types.SimpleNamespace(updateAccessibility=lambda event: None),
    )

    card = host.push("后台任务已完成", timeout_ms=60000)
    assert card is not None
    assert card.accessibleName() == "后台任务已完成"
    assert calls and calls[-1][1] == "后台任务已完成"


def test_announcement_is_safe_without_bridge(
    host: ToastHost, qtbot: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """读屏桥缺失（updateAccessibility 抛错）时，通知照常显示，不崩。"""

    monkeypatch.setattr(
        toast_mod,
        "QAccessible",
        types.SimpleNamespace(
            updateAccessibility=lambda event: (_ for _ in ()).throw(RuntimeError("no bridge"))
        ),
    )

    card = host.push("这条不会崩", timeout_ms=60000)
    assert card is not None
    assert card.isVisible()


def test_close_button_triggers_dismiss(host: ToastHost, qtbot: object) -> None:
    card = host.push("可关闭", timeout_ms=60000)
    qtbot.waitUntil(lambda: card.height() == card.sizeHint().height())  # type: ignore[attr-defined]
    card._close.click()
    qtbot.waitUntil(lambda: card not in host.findChildren(ToastCard))
