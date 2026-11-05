"""响应式密度：auto 按窗口尺寸 / DPI 收紧，manual 固定，切换与 resize 即时重套。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from PySide6.QtCore import QEvent, QSize
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QApplication, QHBoxLayout, QVBoxLayout, QWidget
from pytestqt.qtbot import QtBot

from psi6.runtime.app import App
from psi6.theme import Theme, Tokens, style_metrics
from psi6.theme.apply import refresh_metrics
from psi6.theme.runtime import metrics_scale, token_int
from psi6.ui.chat import Composer
from psi6.ui.drop_zone import DropZone
from psi6.ui.flow_layout import FlowLayout

COMPACT_H = style_metrics("compact")["control_height"]
MODERN_H = style_metrics("modern")["control_height"]


class _CompactTheme(Theme):
    """显式紧凑主题，用来验证 auto 不会反向放宽主题自己的选择。"""

    name = "compact-probe"
    style = "compact"


def _make_app(tmp_path: Path, **kwargs: Any) -> App:
    return App("psi6-density", config_root=tmp_path, **kwargs)


def _window(width: int, height: int) -> QWidget:
    widget = QWidget()
    widget.resize(width, height)
    return widget


def test_style_metrics_exposes_only_size_presets() -> None:
    """预设只含尺寸字段、不含颜色，且每次返回副本。"""

    compact = style_metrics("compact")
    modern = style_metrics("modern")
    assert set(compact) == set(modern)
    assert not any(key.startswith("color_") for key in compact)
    assert compact["control_height"] == 30
    assert modern["control_height"] == 36
    assert compact["space_md"] < modern["space_md"]
    compact["control_height"] = 999
    assert style_metrics("compact")["control_height"] == 30
    with pytest.raises(ValueError, match="style"):
        style_metrics("roomy")


def test_default_density_is_auto_and_no_window_keeps_theme(qtbot: QtBot, tmp_path: Path) -> None:
    """还没开窗口时无法测量空间，auto 不覆盖主题自带尺寸。"""

    app = _make_app(tmp_path)
    assert app.density_mode == "auto"
    assert app.tokens.control_height == MODERN_H


def test_invalid_density_rejected_without_changing_state(qtbot: QtBot, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="density"):
        _make_app(tmp_path, density="roomy")
    app = _make_app(tmp_path)
    with pytest.raises(ValueError, match="density"):
        app.set_density_mode("roomy")
    assert app.density_mode == "auto"
    assert app.tokens.control_height == MODERN_H


def test_manual_compact_tightens_sizes_but_not_colors(qtbot: QtBot, tmp_path: Path) -> None:
    app = _make_app(tmp_path, density="compact")
    assert app.density_mode == "compact"
    assert app.tokens.control_height == COMPACT_H
    assert app.tokens.space_md == style_metrics("compact")["space_md"]
    assert app.tokens.color_bg == Tokens.light().color_bg


def test_manual_modern_overrides_an_explicit_compact_theme(qtbot: QtBot, tmp_path: Path) -> None:
    """手动 modern 是显式选择，可以放宽紧凑主题。"""

    app = _make_app(tmp_path, theme=_CompactTheme, density="modern")
    assert app.tokens.control_height == MODERN_H


def test_auto_never_loosens_an_explicit_compact_theme(qtbot: QtBot, tmp_path: Path) -> None:
    """auto 只在空间不足时收紧，空间充足时沿用主题自己的紧凑选择。"""

    app = _make_app(tmp_path, theme=_CompactTheme, density="auto")
    large = _window(1200, 800)
    app._window = large
    assert app._target_density() == "modern"
    assert app._effective_style() is None
    assert app.tokens.control_height == COMPACT_H


def test_set_density_mode_reapplies_in_both_directions(qtbot: QtBot, tmp_path: Path) -> None:
    """从 compact 切回 auto 要能还原，不能留着上一次的收紧结果。"""

    app = _make_app(tmp_path)
    assert app.tokens.control_height == MODERN_H
    app.set_density_mode("compact")
    assert app.tokens.control_height == COMPACT_H
    app.set_density_mode(" AUTO ")
    assert app.density_mode == "auto"
    assert app.tokens.control_height == MODERN_H


def test_density_survives_theme_switch(qtbot: QtBot, tmp_path: Path) -> None:
    """密度是 app 级策略，换主题后仍生效（_resolve_current 会重新叠加）。"""

    app = _make_app(tmp_path, density="compact")
    app.set_theme("dark")
    assert app.tokens.color_bg == Tokens.dark().color_bg
    assert app.tokens.control_height == COMPACT_H


def test_target_density_follows_window_size(qtbot: QtBot, tmp_path: Path) -> None:
    app = _make_app(tmp_path, compact_max_width=760, compact_max_height=540)
    window = _window(1200, 800)
    app._window = window
    assert app._target_density() == "modern"
    assert app._effective_style() is None

    window.resize(500, 400)
    assert app._target_density() == "compact"
    assert app._effective_style() == "compact"
    window.resize(1200, 400)  # 只高度不足也收紧
    assert app._target_density() == "compact"
    window.resize(500, 800)  # 只宽度不足也收紧
    assert app._target_density() == "compact"


def test_high_dpi_widens_the_tightening_threshold(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """高 DPI 下阈值放宽一档，同样的逻辑尺寸更容易判定为紧凑。"""

    app = _make_app(tmp_path, compact_max_width=760, compact_max_height=540)
    app._window = _window(800, 600)
    assert app._target_density() == "modern"
    monkeypatch.setattr(app, "_window_dpr", lambda: 2.0)
    assert app._target_density() == "compact"


def test_auto_reapplies_on_window_resize(qtbot: QtBot, tmp_path: Path) -> None:
    """Resize 事件过滤器 → 去抖 → 密度翻转 → 重套主题，两个方向都验证。"""

    app = _make_app(tmp_path, compact_max_width=760, compact_max_height=540)
    window = _window(1200, 800)
    app._window = window
    app._bind_density()
    app._recompute_density()
    assert app.tokens.control_height == MODERN_H

    window.resize(500, 400)
    QApplication.sendEvent(window, QResizeEvent(QSize(500, 400), QSize(1200, 800)))
    qtbot.waitUntil(lambda: app.tokens.control_height == COMPACT_H, timeout=3000)
    assert app._applied_style == "compact"

    window.resize(1200, 800)
    QApplication.sendEvent(window, QResizeEvent(QSize(1200, 800), QSize(500, 400)))
    qtbot.waitUntil(lambda: app.tokens.control_height == MODERN_H, timeout=3000)
    assert app._applied_style is None


def test_same_size_resize_does_not_reapply(qtbot: QtBot, tmp_path: Path) -> None:
    """密度没翻转时 _recompute_density 直接返回，不重套整张样式表。"""

    app = _make_app(tmp_path, compact_max_width=760, compact_max_height=540)
    app._window = _window(1200, 800)
    baseline = app._tokens
    app._on_window_resized()
    app._recompute_density()
    assert app._tokens is baseline


def test_manual_density_ignores_window_resize(qtbot: QtBot, tmp_path: Path) -> None:
    app = _make_app(tmp_path, density="modern")
    app._window = _window(300, 200)
    app._bind_density()
    app._on_window_resized()
    assert app._density_timer is None
    assert app.tokens.control_height == MODERN_H


def test_resize_watcher_only_fires_on_resize_and_swallows_errors(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """事件过滤器只认 Resize；回调抛错被吞掉，不污染 Qt 的事件派发。"""

    app = _make_app(tmp_path)
    window = _window(1200, 800)
    app._window = window
    app._bind_density()
    watcher = app._geo_watcher
    assert watcher is not None

    calls: list[int] = []

    def boom() -> None:
        calls.append(1)
        raise RuntimeError("boom")

    watcher._on_resize = boom
    assert watcher.eventFilter(window, QEvent(QEvent.Type.Show)) is False
    assert calls == []
    assert watcher.eventFilter(window, QResizeEvent(QSize(300, 200), QSize(100, 100))) is False
    assert calls == [1]


# ---------------------------------------------------------------------------
# 补齐：密度信号、尺寸重排广播、构造时缓存尺寸的组件
# ---------------------------------------------------------------------------
class _HookWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def apply_metrics(self) -> None:
        self.calls += 1


class _NeedsArgWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def apply_metrics(self, value: int) -> None:
        del value
        self.calls += 1


class _BoomWidget(QWidget):
    def apply_metrics(self) -> None:
        raise RuntimeError("boom")


class _HookLayout(QVBoxLayout):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def apply_metrics(self) -> None:
        self.calls += 1


def test_metrics_scale_tracks_control_height(qtbot: QtBot, tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    assert metrics_scale() == pytest.approx(1.0)
    app.set_density_mode("compact")
    assert metrics_scale() == pytest.approx(COMPACT_H / MODERN_H)


def test_density_changed_fires_on_manual_switch_but_not_theme_switch(
    qtbot: QtBot, tmp_path: Path
) -> None:
    app = _make_app(tmp_path)
    seen: list[str] = []
    app.density_changed.connect(seen.append)
    app.set_density_mode("compact")
    assert seen == ["compact"]
    app.set_density_mode("auto")  # 无窗口时沿用主题自带尺寸
    assert seen == ["compact", "theme"]
    app.set_theme("dark")
    assert seen == ["compact", "theme"]


def test_density_changed_fires_on_auto_flip(qtbot: QtBot, tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    seen: list[str] = []
    app.density_changed.connect(seen.append)
    window = _window(1200, 800)
    app._window = window
    app._bind_density()
    app._recompute_density()
    assert seen == []

    window.resize(500, 400)
    QApplication.sendEvent(window, QResizeEvent(QSize(500, 400), QSize(1200, 800)))
    qtbot.waitUntil(lambda: seen == ["compact"], timeout=3000)
    window.resize(1200, 800)
    QApplication.sendEvent(window, QResizeEvent(QSize(1200, 800), QSize(500, 400)))
    qtbot.waitUntil(lambda: seen == ["compact", "theme"], timeout=3000)


def test_refresh_metrics_covers_widgets_and_layout_trees(qtbot: QtBot) -> None:
    """广播要覆盖普通控件与嵌套布局，跳过签名不合的 hook，坏 hook 不拖垮其余。"""

    host = QWidget()
    qtbot.addWidget(host)
    outer = QHBoxLayout(host)
    nested = _HookLayout()
    outer.addLayout(nested)
    good = _HookWidget()
    needs_arg = _NeedsArgWidget()
    boom = _BoomWidget()
    for widget in (good, needs_arg, boom):
        outer.addWidget(widget)
    app = QApplication.instance()
    assert app is not None

    count = refresh_metrics(app)
    assert good.calls == 1
    assert nested.calls == 1
    assert needs_arg.calls == 0  # 有必填参数，不猜参数
    assert count >= 2


def test_cached_size_widgets_follow_density(qtbot: QtBot, tmp_path: Path) -> None:
    """构造时缓存的间距 / 固定尺寸在切密度后要真正重排。"""

    host = QWidget()
    qtbot.addWidget(host)
    flow = FlowLayout(host)
    composer = Composer()
    qtbot.addWidget(composer)
    zone = DropZone(size="comfortable")
    qtbot.addWidget(zone)
    app = _make_app(tmp_path)

    modern_gap = token_int("space_sm", 8)
    modern_pad = zone._root.contentsMargins().left()
    modern_icon = zone._icon._size
    assert flow.spacing() == modern_gap
    assert composer._edit.minimumHeight() == MODERN_H * 2
    assert composer._send.minimumHeight() == MODERN_H
    assert zone.minimumHeight() == max(140, MODERN_H * 6)

    app.set_density_mode("compact")
    assert flow.spacing() == style_metrics("compact")["space_sm"]
    assert composer._row.contentsMargins().left() == style_metrics("compact")["space_sm"]
    assert composer._edit.minimumHeight() == COMPACT_H * 2
    assert composer._send.minimumHeight() == 32  # max(32, control_height)
    assert zone.minimumHeight() == max(140, COMPACT_H * 6)
    assert zone._root.contentsMargins().left() < modern_pad
    assert zone._icon._size < modern_icon
    assert zone._icon_host.minimumWidth() < modern_icon + modern_pad


def test_explicit_flow_spacing_is_not_overridden_by_density(qtbot: QtBot, tmp_path: Path) -> None:
    host = QWidget()
    qtbot.addWidget(host)
    flow = FlowLayout(host, spacing=4)
    assert flow.spacing() == 4
    _make_app(tmp_path, density="compact")
    assert flow.spacing() == 4
