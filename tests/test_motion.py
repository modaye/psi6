"""统一动画入口：减少动效旁路、不叠加、对象保活。"""

from __future__ import annotations

import pytest
from PySide6.QtCore import Property, QObject
from pytestqt.qtbot import QtBot

from psi6 import App
from psi6.theme.tokens import Tokens
from psi6.ui import motion


class _Probe(QObject):
    """一个带可动画属性的探针，避免为测试实例化真实控件。"""

    def __init__(self) -> None:
        super().__init__()
        self._value = 0.0

    def _get(self) -> float:
        return self._value

    def _set(self, value: float) -> None:
        self._value = float(value)

    value = Property(float, _get, _set)


@pytest.fixture
def app(qtbot: QtBot, tmp_path) -> App:
    return App("psi6-motion", theme="light", config_root=tmp_path)


def test_animate_reaches_end_value(app: App, qtbot: QtBot) -> None:
    probe = _Probe()
    motion.animate(probe, "value", 0.0, 1.0)
    qtbot.waitUntil(lambda: abs(probe._value - 1.0) < 0.001)


def test_reduced_motion_sets_value_immediately(app: App) -> None:
    """减少动效时不建动画，直接到终值并同步回调。"""

    app.set_theme(Tokens.light().overlay({"reduced_motion": 1}))
    probe = _Probe()
    calls: list[str] = []
    animation = motion.animate(probe, "value", 0.0, 1.0, on_finish=lambda: calls.append("done"))

    assert animation is None
    assert probe._value == 1.0
    assert calls == ["done"]


def test_zero_duration_sets_value_immediately(app: App) -> None:
    probe = _Probe()
    animation = motion.animate(probe, "value", 0.0, 1.0, duration=0)

    assert animation is None
    assert probe._value == 1.0


def test_same_property_does_not_stack(app: App, qtbot: QtBot) -> None:
    """同一对象同一属性连续启动时，旧动画先停，最终值是对的。"""

    probe = _Probe()
    motion.animate(probe, "value", 0.0, 1.0)
    motion.animate(probe, "value", probe._value, 0.25)
    qtbot.waitUntil(lambda: abs(probe._value - 0.25) < 0.001)
    # 只留一个有效动画，1.0 不会被后一个覆盖成最终状态。
    assert abs(probe._value - 0.25) < 0.001


def test_stop_removes_animation(app: App) -> None:
    probe = _Probe()
    motion.animate(probe, "value", 0.0, 1.0)
    motion.stop(probe, "value")
    assert all(
        not (item.targetObject() is probe and item.propertyName() == b"value")
        for item in motion._RUNNING
    )


def test_stop_all_clears_registry(app: App) -> None:
    first, second = _Probe(), _Probe()
    motion.animate(first, "value", 0.0, 1.0)
    motion.animate(second, "value", 0.0, 1.0)
    motion.stop_all()
    assert motion._RUNNING == []


def test_animate_value_reports_frames(app: App, qtbot: QtBot) -> None:
    seen: list[float] = []
    owner = QObject()
    motion.animate_value(owner, 0.0, 10.0, on_value=seen.append, duration=120, speed="fast")
    qtbot.waitUntil(lambda: bool(seen) and abs(seen[-1] - 10.0) < 0.001)
    assert len(seen) > 1, "应当逐帧回调，而不是只给终值"


def test_animate_value_with_reduced_motion_emits_once(app: App) -> None:
    app.set_theme(Tokens.light().overlay({"reduced_motion": 1}))
    seen: list[float] = []
    finished: list[bool] = []
    animation = motion.animate_value(
        QObject(),
        0.0,
        10.0,
        on_value=seen.append,
        on_finish=lambda: finished.append(True),
    )

    assert animation is None
    assert seen == [10.0]
    assert finished == [True]


def test_easing_falls_back_for_unknown_name(app: App) -> None:
    from PySide6.QtCore import QEasingCurve

    assert motion.easing("nope") == QEasingCurve.Type.OutCubic
    assert motion.easing("linear") == QEasingCurve.Type.Linear


def test_motion_enabled_follows_theme(app: App) -> None:
    assert motion.motion_enabled() is True
    app.set_theme(Tokens.light().overlay({"reduced_motion": 1}))
    assert motion.motion_enabled() is False
