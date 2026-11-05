"""主题 token 进入样式表，组件不写死 hex。"""

from __future__ import annotations

from pathlib import Path

import pytest
from pytestqt.qtbot import QtBot

from psi6.runtime.app import App
from psi6.theme.apply import build_stylesheet
from psi6.theme.colors import contrast_ratio
from psi6.theme.tokens import DEFAULT_TOKENS, Tokens


def test_selection_tint_stays_off_the_hover_color() -> None:
    """悬停用中性 color_hover，持久选中用强调色浅底。菜单高亮仍是悬停。"""

    from PySide6.QtGui import QColor

    from psi6.theme.paint import mix_color

    light = Tokens.light()
    tint = mix_color(light.color_primary, light.color_bg, 0.86).name(QColor.NameFormat.HexRgb)
    css = build_stylesheet(light)
    selected = css.split("QTableView::item:selected", 1)[1].split("}", 1)[0]
    hover = css.split("QListView::item:hover", 1)[1].split("}", 1)[0]
    menu = css.split("QMenu::item:selected", 1)[1].split("}", 1)[0]
    assert tint in selected
    assert light.color_hover not in selected
    assert light.color_hover in hover
    assert light.color_elevated not in hover
    assert tint not in hover
    assert light.color_hover in menu
    assert tint != light.color_primary
    dark = Tokens.dark()
    dark_tint = mix_color(dark.color_primary, dark.color_bg, 0.86).name(QColor.NameFormat.HexRgb)
    assert dark_tint in build_stylesheet(dark)
    assert dark_tint != dark.color_hover


def test_stylesheet_uses_tokens() -> None:
    css = build_stylesheet(DEFAULT_TOKENS)
    assert DEFAULT_TOKENS.color_primary in css
    assert DEFAULT_TOKENS.color_danger in css
    assert f"border-radius: {DEFAULT_TOKENS.window_radius}px" in css
    # Themed buttons are styled per-widget (see apply_psi6_button_style), so their
    # rules live in psi6_button_stylesheet, not the global sheet.
    from psi6.theme.apply import psi6_button_stylesheet

    primary = psi6_button_stylesheet("psi6Primary", DEFAULT_TOKENS)
    assert DEFAULT_TOKENS.color_primary in primary


def test_stylesheet_covers_native_widgets() -> None:
    css = build_stylesheet(Tokens.light())
    for selector in (
        "QScrollBar",
        "QTabBar",
        "QMenu",
        "QToolTip",
        "QSplitter",
        "QTreeView",
        "psi6Toast",
        "psi6BusyOverlay",
        "psi6DiffHost",
        "psi6DiffView",
        "psi6Switch",
        "psi6SettingRow",
        "QDateTimeEdit",
        "QDateEdit",
        "QComboBox::down-arrow",
        "QAbstractSpinBox::up-arrow",
        "psi6DropZone",
        "psi6Segmented",
        "psi6CheckList",
        "psi6ContentDialog",
        "psi6ImageWell",
    ):
        assert selector in css
    assert "padding: 0" in css
    assert "psi6icon:" in css
    # Themed buttons (Ghost/Link/...) are styled per-widget; every kind resolves.
    from psi6.theme.apply import KNOWN_KINDS, psi6_button_stylesheet

    for kind in KNOWN_KINDS:
        assert psi6_button_stylesheet(kind, Tokens.light())


def test_dark_stylesheet_does_not_use_light_canvas() -> None:
    dark = Tokens.dark()
    css = build_stylesheet(dark)
    assert dark.color_bg in css
    assert dark.color_primary in css
    assert Tokens.light().color_bg not in css


def test_qss_icons_are_logical_size_svg(tmp_path: Path) -> None:
    """QSS 里的图标用逻辑尺寸的 SVG：位图在高 DPI 下会被引擎二次缩放，裁切或起毛边。"""

    from psi6.theme.chrome import cache_dir, qss_icon_ref

    ref = qss_icon_ref("check", color="#ffffff", size=16)
    name = ref.split(":", 1)[1]
    assert name.endswith(".svg")
    markup = (cache_dir() / name).read_text(encoding="utf-8")
    assert 'width="16" height="16"' in markup
    assert "#ffffff" in markup


def test_qss_icons_are_not_rewritten(monkeypatch) -> None:
    from psi6.theme.chrome import cache_dir, qss_icon_ref

    target = cache_dir() / "check_123456_16.svg"
    target.unlink(missing_ok=True)
    writes: list[Path] = []
    original = Path.write_text

    def spy(self: Path, data: str, *args, **kwargs):
        writes.append(self)
        return original(self, data, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", spy)
    qss_icon_ref("check", color="#123456", size=16)
    assert len(writes) == 1
    qss_icon_ref("check", color="#123456", size=16)
    assert len(writes) == 1
    target.unlink(missing_ok=True)


def test_qss_icon_names_are_filesystem_safe() -> None:
    from psi6.theme.chrome import cache_dir, qss_icon_ref

    ref = qss_icon_ref("check", color="rgba(255, 0, 0, 0.5)", size=16)
    name = ref.split(":", 1)[1]
    assert name.startswith("check_c")
    assert "/" not in name and "\\" not in name
    assert (cache_dir() / name).is_file()


def test_qss_icon_cache_prunes_stale_files() -> None:
    import os
    import time

    from psi6.theme.chrome import cache_dir, cleanup_cache

    stale = cache_dir() / "stale_psi6_test.svg"
    stale.write_text("<svg/>", encoding="utf-8")
    old = time.time() - 40 * 24 * 60 * 60
    os.utime(stale, (old, old))
    try:
        assert cleanup_cache() >= 1
        assert not stale.exists()
    finally:
        stale.unlink(missing_ok=True)


def test_check_and_radio_indicators_are_fully_drawn() -> None:
    """QSS 接管 QCheckBox 后，指示器的矩形框、勾选填充和勾选图都要由主题给出。"""

    light = Tokens.light()
    css = build_stylesheet(light)
    assert f"border: 1px solid {light.color_border}" in css
    for selector in (
        "QCheckBox::indicator",
        "QCheckBox::indicator:hover",
        "QCheckBox::indicator:focus",
        "QCheckBox::indicator:checked",
        "QCheckBox::indicator:indeterminate",
        "QCheckBox::indicator:disabled",
        "QCheckBox::indicator:checked:disabled",
        "QRadioButton::indicator",
        "QRadioButton::indicator:checked",
        "QRadioButton::indicator:checked:disabled",
    ):
        assert selector in css
    checked = css.split("QCheckBox::indicator:checked {", 1)[1].split("}", 1)[0]
    assert f"background: {light.color_primary}" in checked
    assert "image: url(psi6icon:" in checked


def test_control_border_follows_border_unless_overridden() -> None:
    """控件描边留空时等于 color_border，写了值才和结构边分开。"""

    from psi6.theme.builtin import Brass, Obsidian
    from psi6.theme.theme import Theme

    light = Tokens.light().resolve_states()
    dark = Tokens.dark().resolve_states()
    assert light.color_control_border == light.color_border == "#d3dae3"
    assert dark.color_control_border == dark.color_border == "#2b3546"
    assert light.resolve_states() == light
    # 只改了结构边的内置主题，控件边跟着走，不必在每个主题里再写一份。
    assert Obsidian().tokens().color_control_border == Obsidian.color_border
    assert Brass().tokens().color_control_border == Brass.color_border

    class Split(Theme):
        color_control_border = "#445566"

    tokens = Split().tokens()
    assert tokens.color_control_border == "#445566"
    assert tokens.color_border == Tokens.light().color_border
    css = build_stylesheet(tokens)
    inputs = css.split("QLineEdit, QComboBox", 1)[1].split("}", 1)[0]
    tables = css.split("QTableWidget, QTableView, QTreeView, QListView {", 1)[1].split("}", 1)[0]
    assert "border: 1px solid #445566" in inputs
    assert f"border: 1px solid {tokens.color_border}" in tables
    assert "#445566" not in tables

    cleared = Tokens.dark().overlay({"color_control_border": ""})
    assert cleared.color_control_border == ""
    assert cleared.resolve_states().color_control_border == Tokens.dark().color_border


def test_state_colors_derive_and_override() -> None:
    from psi6.theme.colors import mix_hex
    from psi6.theme.theme import Theme

    light = Tokens.light().resolve_states()
    assert light.color_pressed != light.color_hover
    assert light.color_selected == mix_hex(light.color_primary, light.color_bg, 0.86)
    assert light.color_selected != light.color_hover
    assert light.color_primary_hover == mix_hex(light.color_primary, "#ffffff", 0.24)
    assert light.resolve_states() == light

    overridden = Tokens.light().overlay({"color_pressed": "#123456", "color_selected": "#654321"})
    overridden = overridden.resolve_states()
    assert overridden.color_pressed == "#123456"
    assert overridden.color_selected == "#654321"

    class Custom(Theme):
        color_primary = "#ff0000"

    tokens = Custom().tokens()
    assert tokens.color_selected == mix_hex("#ff0000", tokens.color_bg, 0.86)
    assert tokens.color_primary_hover == mix_hex("#ff0000", "#ffffff", 0.24)


def test_auto_variant_states_follow_outer_primary(monkeypatch: pytest.MonkeyPatch) -> None:
    from psi6.theme.colors import mix_hex
    from psi6.theme.theme import Theme

    class Day(Theme):
        base = "light"
        color_primary = "#111111"

    class Adaptive(Theme):
        base = "auto"
        light = Day
        color_primary = "#ff0000"

    monkeypatch.setattr("psi6.theme.theme.system_prefers_dark", lambda: False)
    tokens = Adaptive().tokens()
    assert tokens.color_primary == "#ff0000"
    assert tokens.color_primary_hover == mix_hex("#ff0000", "#ffffff", 0.24)


def test_pressed_state_uses_dedicated_token() -> None:
    custom = Tokens.light().overlay({"color_pressed": "#123456"})
    css = build_stylesheet(custom)
    for selector in (
        "QPushButton:pressed",
        "QToolButton:pressed",
        "QToolButton#psi6IconButton:pressed",
        "QToolButton#psi6TitleButton:pressed",
        'QWidget#psi6DropZone[pressed="true"]',
    ):
        block = css.split(selector, 1)[1].split("{", 1)[1].split("}", 1)[0]
        assert "background: #123456" in block
    # Themed buttons read the dedicated pressed token from their per-widget sheet.
    from psi6.theme.apply import psi6_button_stylesheet

    ghost = psi6_button_stylesheet("psi6Ghost", custom)
    ghost_block = ghost.split("QPushButton:pressed", 1)[1].split("}", 1)[0]
    assert "background: #123456" in ghost_block
    nav = psi6_button_stylesheet("psi6NavItem", custom)
    nav_block = nav.split("QPushButton:pressed", 1)[1].split("}", 1)[0]
    assert "background: #123456" in nav_block
    # Primary uses its own primary_pressed token, not the generic color_pressed.
    primary = psi6_button_stylesheet("psi6Primary", custom)
    primary_pressed = primary.split("QPushButton:pressed", 1)[1].split("}", 1)[0]
    assert "background: #123456" not in primary_pressed


def test_app_tokens_include_resolved_states(qtbot: QtBot, tmp_path: Path) -> None:
    app = App("psi6-states", theme="dark", config_root=tmp_path)
    assert app.tokens.color_pressed
    assert app.qt_app.property("psi6ColorPressed") == app.tokens.color_pressed
    app.set_theme("light")
    assert app.tokens.color_pressed
    assert app.qt_app.property("psi6ColorPressed") == app.tokens.color_pressed


def test_theme_switch_restyles_themed_buttons(qtbot: QtBot, tmp_path: Path) -> None:
    """运行时换主题必须重刷主题化按钮。

    主题化按钮是逐控件设置样式表的（不随全局样式表级联），所以换肤后
    必须按新 token 重新写一次。曾经的三个坑叠加，导致深色主题下按钮仍用
    浅色主题的色值：``QPushButton`` 未导入使 isinstance 抛 NameError 被吞、
    token 写在 ``setPalette`` 之后使过滤器读到旧值、子控件收不到重刷。
    """

    from PySide6.QtWidgets import QVBoxLayout, QWidget

    from psi6.ui.buttons import danger_button, ghost_button, primary_button

    app = App("psi6-restyle", theme="light", config_root=tmp_path)
    host = QWidget()
    layout = QVBoxLayout(host)
    buttons = [primary_button("开始"), ghost_button("取消"), danger_button("删除")]
    for button in buttons:
        layout.addWidget(button)
    host.show()
    qtbot.wait(10)

    light_css = [button.styleSheet() for button in buttons]
    app.set_theme("dark")
    qtbot.wait(10)
    dark_css = [button.styleSheet() for button in buttons]

    assert light_css != dark_css, "换主题后主题化按钮的样式表必须更新"
    tokens = app.tokens
    expected = {
        "psi6Primary": tokens.color_primary,
        "psi6Ghost": tokens.color_control_border,
        "psi6Danger": tokens.color_danger,
    }
    for button, css in zip(buttons, dark_css, strict=True):
        assert expected[button.objectName()] in css, (
            f"{button.objectName()} 应使用深色主题色 {expected[button.objectName()]}"
        )
    # 幽灵按钮的文字也要换成深色主题的浅色，否则深底上读不出来
    assert tokens.color_text in dark_css[1]


def test_tokens_overlay_rejects_unknown_keys() -> None:
    dark = Tokens.dark().overlay({"color_primary": "#7a9e7e", "radius": 8, "motion_fast_ms": 80})
    assert dark.color_primary == "#7a9e7e"
    assert dark.radius == 8
    assert dark.button_radius == 8
    assert dark.motion_fast_ms == 80
    assert dark.color_bg == Tokens.dark().color_bg
    with pytest.raises(ValueError, match="未知 token"):
        Tokens.light().overlay({"color_primry": "#fff"})


def test_tokens_overlay_rejects_invalid_values(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="有效颜色"):
        Tokens.light().overlay({"color_primary": "blue"})
    with pytest.raises(ValueError, match="不能为负数"):
        Tokens.light().overlay({"radius": -1})
    with pytest.raises(ValueError, match="必须是整数"):
        Tokens.light().overlay({"font_size": "wide"})
    with pytest.raises(ValueError, match="icon_dir 不存在"):
        Tokens.light().overlay({"icon_dir": str(tmp_path / "missing")})


def test_stylesheet_parses_without_qt_warnings(qapp) -> None:
    from PySide6.QtCore import qInstallMessageHandler

    messages: list[str] = []
    previous_css = qapp.styleSheet()
    previous = qInstallMessageHandler(lambda _mode, _context, message: messages.append(message))
    try:
        qapp.setStyleSheet(build_stylesheet(Tokens.light()))
    finally:
        qInstallMessageHandler(previous)
        qapp.setStyleSheet(previous_css)
    assert not [item for item in messages if "stylesheet" in item.lower()]


def test_focus_ring_does_not_shift_content() -> None:
    """焦点环用 border 绘制 + 几何补偿，聚焦时外框尺寸不变、内容不位移。

    Qt 的 outline 会在控件内容矩形内画框（加 offset 向内收缩会压住文字），不能
    用来画外圈，因此改成把 1px 边框加宽到 ring px，并同步收紧 padding/min-height。
    这里断言：focus 边框宽度等于 ring 且用 color_focus；无边框按钮（主/危险/分段/
    导航）比有边框按钮多扣 1px（补偿基础那 1px 边框）；链接按钮用下划线而非方框。
    """

    light = Tokens.light().resolve_states()
    css = build_stylesheet(light)
    ring = light.focus_ring_width
    space_md = light.space_md
    space_sm = light.space_sm
    ch = light.control_height

    focus_pad = max(0, space_md - (ring - 1))
    focus_min_h = max(12, ch - 2 * (ring - 1))
    focus_pad_nb = max(0, space_md - ring)
    focus_min_h_nb = max(12, ch - 2 * ring)
    nav_focus_pad = max(0, space_sm - ring)

    from psi6.theme.apply import psi6_button_stylesheet

    # 全局：有边框按钮、输入框、页签用同一套补偿（在全局样式表内）
    for sel in ("QPushButton:focus", "QLineEdit:focus", "QTabBar::tab:focus"):
        block = css.split(sel, 1)[1].split("{", 1)[1].split("}", 1)[0]
        assert f"border: {ring}px solid" in block, (sel, "border width")

    plain_focus = css.split("QPushButton:focus", 1)[1].split("{", 1)[1].split("}", 1)[0]
    assert light.color_focus in plain_focus, ("plain", "focus color")
    assert f"padding: 0 {focus_pad}px" in plain_focus, ("plain", "pad")
    assert f"min-height: {focus_min_h}px" in plain_focus, ("plain", "min-h")
    inputs = css.split("QLineEdit:focus", 1)[1].split("{", 1)[1].split("}", 1)[0]
    assert f"padding: 0 {focus_pad}px" in inputs, ("inputs", "pad")
    assert f"min-height: {focus_min_h}px" in inputs, ("inputs", "min-h")
    tab = css.split("QTabBar::tab:focus", 1)[1].split("{", 1)[1].split("}", 1)[0]
    assert f"padding: {space_sm}px {focus_pad}px" in tab, ("tab", "pad")
    assert f"min-height: {focus_min_h}px" in tab, ("tab", "min-h")

    # 主题按钮：per-widget 样式表，选择器是普通 QPushButton
    ghost_focus = (
        psi6_button_stylesheet("psi6Ghost", light)
        .split("QPushButton:focus", 1)[1]
        .split("{", 1)[1]
        .split("}", 1)[0]
    )
    assert f"border: {ring}px solid" in ghost_focus, ("ghost", "border")
    assert light.color_focus in ghost_focus, ("ghost", "focus color")
    assert f"padding: 0 {focus_pad}px" in ghost_focus, ("ghost", "pad")
    assert f"min-height: {focus_min_h}px" in ghost_focus, ("ghost", "min-h")

    primary_focus = (
        psi6_button_stylesheet("psi6Primary", light)
        .split("QPushButton:focus", 1)[1]
        .split("{", 1)[1]
        .split("}", 1)[0]
    )
    assert f"padding: 0 {focus_pad_nb}px" in primary_focus, ("primary", "pad_nb")
    assert f"min-height: {focus_min_h_nb}px" in primary_focus, ("primary", "min_h_nb")
    assert light.color_on_primary in primary_focus, ("primary", "ring contrasts face")
    assert contrast_ratio(light.color_on_primary, light.color_primary) >= 3.0, (
        "primary",
        "ring vs face < 3:1",
    )

    danger_focus = (
        psi6_button_stylesheet("psi6Danger", light)
        .split("QPushButton:focus", 1)[1]
        .split("{", 1)[1]
        .split("}", 1)[0]
    )
    assert f"padding: 0 {focus_pad_nb}px" in danger_focus, ("danger", "pad_nb")
    assert f"min-height: {focus_min_h_nb}px" in danger_focus, ("danger", "min_h_nb")
    assert light.color_on_primary in danger_focus, ("danger", "ring contrasts face")
    assert contrast_ratio(light.color_on_primary, light.color_danger) >= 3.0, (
        "danger",
        "ring vs face < 3:1",
    )

    # 分段项：无横向 padding 可扣，只补偿高度
    segment_focus = (
        psi6_button_stylesheet("psi6Segment", light)
        .split("QPushButton:focus", 1)[1]
        .split("{", 1)[1]
        .split("}", 1)[0]
    )
    assert f"min-height: {focus_min_h_nb}px" in segment_focus, ("segment", "min_h_nb")
    assert "padding" not in segment_focus, ("segment", "no horizontal pad to lose")

    # 导航项：padding 基于 space_sm，用 nav 补偿
    nav_focus = (
        psi6_button_stylesheet("psi6NavItem", light)
        .split("QPushButton:focus", 1)[1]
        .split("{", 1)[1]
        .split("}", 1)[0]
    )
    assert f"padding: 0 {nav_focus_pad}px" in nav_focus, ("nav", "pad")
    assert f"min-height: {focus_min_h_nb}px" in nav_focus, ("nav", "min_h_nb")

    # 链接按钮：文字链用下划线，不套方框
    link_focus = (
        psi6_button_stylesheet("psi6Link", light)
        .split("QPushButton:focus", 1)[1]
        .split("{", 1)[1]
        .split("}", 1)[0]
    )
    assert "text-decoration: underline" in link_focus, ("link", "underline")
    assert "border: none" in link_focus, ("link", "no box")


def test_disabled_states_are_fully_styled() -> None:
    """ID 选择器优先级高于伪类，禁用态必须逐个写出来（per-widget 样式表内）。"""

    from psi6.theme.apply import psi6_button_stylesheet

    css = build_stylesheet(Tokens.light())
    assert "QMenu::item:disabled" in css
    for kind in ("psi6Ghost", "psi6Link", "psi6Segment", "psi6Tag"):
        sheet = psi6_button_stylesheet(kind, Tokens.light())
        assert "QPushButton:disabled" in sheet, kind
    scrollbar = css.split("QScrollBar::handle:vertical:hover", 1)[1].split("}", 1)[0]
    assert Tokens.light().color_muted in scrollbar


def test_style_metrics_and_nested_button_tokens() -> None:
    from psi6.theme.tokens import merge_style

    compact = merge_style(Tokens.light(), "compact", {})
    assert compact.control_height == 30
    assert compact.control_height_sm == 24
    assert compact.row_height == 28
    assert compact.icon_size == 14
    assert compact.space_lg == 10
    assert compact.font_size_title == 16
    assert compact.sidebar_compact_width == 52
    sized = merge_style(
        Tokens.light(),
        "compact",
        {"control_height": 36, "button": {"radius": 10}},
    )
    assert sized.control_height == 36
    assert sized.button_radius == 10
    reduced = Tokens.light().overlay({"reduced_motion": 1})
    assert reduced.motion_fast_ms == 0
    assert reduced.motion_ms == 0


def test_python_theme_overrides_and_rejects_typos() -> None:
    from psi6.theme.builtin import Brass, Compact
    from psi6.theme.theme import Theme
    from psi6.theme.tokens import resolve_tokens

    brass = resolve_tokens(Brass)
    assert brass.color_primary == "#6b542e"
    assert brass.color_bg == "#f3efe6"
    compact = Compact().tokens()
    assert compact.control_height == 30
    assert compact.color_bg == Tokens.light().color_bg

    class Midnight(Theme):
        name = "midnight"
        base = "dark"
        color_primary = "#4d7c5a"
        button_radius = 8

    loaded = resolve_tokens(Midnight)
    assert loaded.color_primary == "#4d7c5a"
    assert loaded.button_radius == 8
    assert loaded.color_bg == Tokens.dark().color_bg

    class Moss(Theme):
        base = "dark"
        color_primary = "#4d7c5a"

    class MossSoft(Moss):
        radius = 8

    child = MossSoft().tokens()
    assert child.color_primary == "#4d7c5a"
    assert child.radius == 8
    assert child.color_bg == Tokens.dark().color_bg

    with pytest.raises(TypeError, match="未知 token"):

        class Broken(Theme):
            color_primry = "#fff"

        Broken().tokens()

    class Desk(Theme):
        base = "dark"
        style = "compact"
        color_primary = "#4d7c5a"

    desk = Desk().tokens()
    again = Desk().tokens()
    assert desk == again
    assert desk.color_bg == Tokens.dark().color_bg
    assert desk.color_primary == "#4d7c5a"
    assert desk.control_height == 30
    assert desk.font_size == 12

    class Plain(Theme):
        color_primary = "#35597a"

    plain = Plain().tokens()
    assert plain.control_height == 36
    assert plain.radius == 6
    assert plain.font_size_title == 18

    with pytest.raises(TypeError, match="未知 token"):

        class Clash(Theme):
            style = "modern"
            density = "compact"

        Clash().tokens()

    with pytest.raises(ValueError, match="style"):

        class Odd(Theme):
            style = "fluent"

        Odd().tokens()


def test_theme_file_paths_are_rejected(tmp_path: Path) -> None:
    from psi6.theme.tokens import resolve_tokens

    path = tmp_path / "user.toml"
    path.write_text('base = "dark"\n', encoding="utf-8")
    with pytest.raises(TypeError, match="Python"):
        resolve_tokens(path)
    with pytest.raises(TypeError, match="Python"):
        resolve_tokens("theme.yaml")


def test_auto_theme_picks_declared_variant(monkeypatch: pytest.MonkeyPatch) -> None:
    from psi6.theme.theme import Theme

    class Day(Theme):
        base = "light"
        color_primary = "#111111"

    class Night(Theme):
        base = "dark"
        color_primary = "#eeeeee"

    class Adaptive(Theme):
        name = "adaptive"
        base = "auto"
        light = Day
        dark = Night

    monkeypatch.setattr("psi6.theme.theme.system_prefers_dark", lambda: False)
    assert Adaptive().tokens().color_primary == "#111111"
    monkeypatch.setattr("psi6.theme.theme.system_prefers_dark", lambda: True)
    night = Adaptive().tokens()
    assert night.color_primary == "#eeeeee"
    assert night.color_bg == Tokens.dark().color_bg

    class Dense(Adaptive):
        style = "compact"
        color_danger = "#ff0000"

    dense = Dense().tokens()
    assert dense.control_height == 30
    assert dense.color_danger == "#ff0000"
    assert dense.color_primary == "#eeeeee"


def test_auto_theme_without_variants_uses_system_base(monkeypatch: pytest.MonkeyPatch) -> None:
    from psi6.theme.theme import Theme

    class Blank(Theme):
        name = "blank"
        base = "auto"
        color_primary = "#654321"

    monkeypatch.setattr("psi6.theme.theme.system_prefers_dark", lambda: False)
    assert Blank().tokens().color_bg == Tokens.light().color_bg
    monkeypatch.setattr("psi6.theme.theme.system_prefers_dark", lambda: True)
    dark = Blank().tokens()
    assert dark.color_bg == Tokens.dark().color_bg
    assert dark.color_primary == "#654321"


def test_auto_theme_rejects_bad_variants(monkeypatch: pytest.MonkeyPatch) -> None:
    from psi6.theme.theme import Theme

    monkeypatch.setattr("psi6.theme.theme.system_prefers_dark", lambda: True)

    class Broken(Theme):
        base = "auto"
        dark = "#eeeeee"

    with pytest.raises(TypeError, match="dark"):
        Broken().tokens()

    class Loop(Theme):
        base = "auto"
        dark = Broken

    with pytest.raises(ValueError, match="不能再是 auto"):
        Loop().tokens()

    class SelfLoop(Theme):
        base = "auto"

    SelfLoop.dark = SelfLoop
    with pytest.raises(ValueError, match="auto"):
        SelfLoop().tokens()

    class Odd(Theme):
        base = "sepia"

    with pytest.raises(ValueError, match="base"):
        Odd().tokens()


def test_app_switches_light_and_dark_theme(qtbot: QtBot, tmp_path: Path) -> None:
    app = App("psi6-theme-switch", theme="dark", config_root=tmp_path)
    assert Tokens.dark().color_bg in app.qt_app.styleSheet()
    app.set_theme("light")
    assert Tokens.light().color_bg in app.qt_app.styleSheet()
    assert app.tokens.color_bg == Tokens.light().color_bg


def test_app_auto_theme_follows_system(qtbot: QtBot, tmp_path: Path) -> None:
    from psi6.theme.system import system_prefers_dark
    from psi6.theme.tokens import Tokens

    app = App("psi6-auto-theme", theme="auto", config_root=tmp_path)
    expected = Tokens.dark() if system_prefers_dark() else Tokens.light()
    assert app.tokens.color_bg == expected.color_bg


def test_object_theme_with_auto_base_reapplies_on_scheme_change(
    qtbot: QtBot,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``base = "auto"`` 的主题对象也要跟着系统方案重画，不再只有 ``"auto"`` 字符串会跟。"""

    from PySide6.QtCore import Qt

    from psi6.theme.theme import Theme

    class Day(Theme):
        base = "light"

    class Night(Theme):
        base = "dark"

    class Adaptive(Theme):
        name = "adaptive"
        base = "auto"
        light = Day
        dark = Night

    monkeypatch.setattr("psi6.theme.theme.system_prefers_dark", lambda: False)
    app = App("psi6-object-auto", theme=Adaptive, config_root=tmp_path)
    assert app.tokens.color_bg == Tokens.light().color_bg
    monkeypatch.setattr("psi6.theme.theme.system_prefers_dark", lambda: True)
    app.qt_app.styleHints().colorSchemeChanged.emit(Qt.ColorScheme.Dark)
    assert app.tokens.color_bg == Tokens.dark().color_bg
    assert Tokens.dark().color_bg in app.qt_app.styleSheet()
    monkeypatch.setattr("psi6.theme.theme.system_prefers_dark", lambda: False)
    app.qt_app.styleHints().colorSchemeChanged.emit(Qt.ColorScheme.Light)
    assert app.tokens.color_bg == Tokens.light().color_bg
    app.set_theme("light")


def test_fixed_object_theme_ignores_scheme_change(
    qtbot: QtBot,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from PySide6.QtCore import Qt

    from psi6.theme.builtin import Obsidian

    monkeypatch.setattr("psi6.theme.theme.system_prefers_dark", lambda: False)
    app = App("psi6-fixed-auto", theme=Obsidian, config_root=tmp_path)
    bg = app.tokens.color_bg
    monkeypatch.setattr("psi6.theme.theme.system_prefers_dark", lambda: True)
    app.qt_app.styleHints().colorSchemeChanged.emit(Qt.ColorScheme.Dark)
    assert app.tokens.color_bg == bg
    app.set_theme("light")


def test_app_selects_registered_theme_by_name(qtbot: QtBot, tmp_path: Path) -> None:
    from psi6.theme.builtin import Mono
    from psi6.theme.theme import Theme

    class Slate(Theme):
        name = "slate"
        base = "dark"
        color_primary = "#123456"

    app = App("psi6-named", theme="slate", theme_choices=[Slate], config_root=tmp_path)
    assert app.theme_name == "slate"
    assert app.tokens.color_primary == "#123456"
    app.set_theme("mono")
    assert app.tokens.color_surface == Mono().tokens().color_surface
    with pytest.raises(ValueError, match="未注册"):
        app.set_theme("granite")
    app.set_theme("light")


def test_app_remembers_theme_between_instances(qtbot: QtBot, tmp_path: Path) -> None:
    from psi6.theme.builtin import Obsidian

    app = App("psi6-remember", theme="light", config_root=tmp_path, remember_theme=True)
    app.set_theme(Obsidian)
    assert app.theme_name == "obsidian"
    assert (tmp_path / "psi6-remember" / "theme.json").is_file()
    again = App("psi6-remember", theme="light", config_root=tmp_path, remember_theme=True)
    assert again.theme_name == "obsidian"
    assert again.tokens.color_bg == Obsidian().tokens().color_bg
    ignored = App("psi6-remember", theme="light", config_root=tmp_path)
    assert ignored.theme_name == "light"
    assert again.store.load_data("psi6-remember", "theme.json") == {"theme": "obsidian"}
    app.set_theme("light")


def test_app_remembers_auto_scheme(qtbot: QtBot, tmp_path: Path) -> None:
    app = App("psi6-remember-scheme", theme="light", config_root=tmp_path, remember_theme=True)
    app.set_theme("auto")
    again = App("psi6-remember-scheme", theme="light", config_root=tmp_path, remember_theme=True)
    assert again.theme_name == "auto"
    app.set_theme("light")


def test_tokens_selection_is_not_remembered(qtbot: QtBot, tmp_path: Path) -> None:
    app = App("psi6-remember-tokens", theme="light", config_root=tmp_path, remember_theme=True)
    app.set_theme(Tokens.dark())
    assert app.theme_name == "custom"
    again = App("psi6-remember-tokens", theme="light", config_root=tmp_path, remember_theme=True)
    assert again.theme_name == "light"
    app.set_theme("light")


def test_unknown_stored_theme_falls_back_to_default(qtbot: QtBot, tmp_path: Path) -> None:
    app = App("psi6-stale-theme", theme="light", config_root=tmp_path, remember_theme=True)
    app.store.save_data("psi6-stale-theme", "theme.json", {"theme": "granite"})
    again = App("psi6-stale-theme", theme="light", config_root=tmp_path, remember_theme=True)
    assert again.theme_name == "light"
    assert again.tokens.color_bg == Tokens.light().color_bg


def test_apply_theme_sets_app_font(qtbot: QtBot, tmp_path: Path) -> None:
    from PySide6.QtWidgets import QLabel

    from psi6.theme.apply import font_families
    from psi6.theme.tokens import merge_style

    app = App("psi6-font-token", theme="light", config_root=tmp_path)
    assert app.qt_app.font().pixelSize() == app.tokens.font_size
    assert app.qt_app.font().families() == font_families(app.tokens.font_family)
    label = QLabel("正文")
    qtbot.addWidget(label)
    assert label.font().pixelSize() == app.tokens.font_size
    app.set_theme(merge_style(Tokens.light(), "compact", {}))
    assert app.tokens.font_size == 12
    assert app.qt_app.font().pixelSize() == 12
    assert label.font().pixelSize() == 12
    app.set_theme("light")


def test_icon_button_recolors_when_theme_switches(qtbot: QtBot, tmp_path: Path) -> None:
    from psi6.ui.icon import IconButton, token_color

    app = App("psi6-icon-theme", theme="light", config_root=tmp_path)
    button = IconButton("play", label="播放")
    qtbot.addWidget(button)
    assert token_color(button) == Tokens.light().color_text
    app.set_theme("dark")
    assert token_color(button) == Tokens.dark().color_text
    assert not button.icon().isNull()
    app.set_theme("light")


def test_combo_down_arrow_uses_themed_chevron(qtbot: QtBot, tmp_path: Path) -> None:
    from PySide6.QtWidgets import QComboBox

    app = App("psi6-combo-arrow", theme="light", config_root=tmp_path)
    css = app.qt_app.styleSheet()
    assert "QComboBox::down-arrow" in css
    assert "psi6icon:chevron-down" in css
    combo = QComboBox()
    combo.addItems(["浅色", "深色"])
    combo.setFixedSize(180, 32)
    qtbot.addWidget(combo)
    combo.show()
    qtbot.waitExposed(combo)
    image = combo.grab().toImage()
    mid = image.height() // 2
    ink = [
        image.pixelColor(x, mid)
        for x in range(max(0, image.width() - 22), max(0, image.width() - 6))
    ]
    assert any(pixel.alpha() > 50 and pixel.red() < 160 for pixel in ink)


def test_apply_theme_publishes_size_tokens(qtbot: QtBot, tmp_path: Path) -> None:
    from psi6.theme.runtime import token_int

    # 显式开启焦点环：App 默认关闭，这条用例仍要覆盖「开启时环按 token 生成」。
    app = App("psi6-size-tokens", theme="light", config_root=tmp_path, focus_ring=True)
    assert app.qt_app.property("psi6ControlHeight") == 36
    assert token_int("control_height") == 36
    from psi6.theme.tokens import merge_style

    app.set_theme(merge_style(Tokens.light(), "compact", {}))
    assert token_int("control_height") == 30
    assert token_int("icon_size") == 14
    css = app.qt_app.styleSheet()
    assert "min-height: 30px" in css
    # Themed buttons are styled per-widget; their pressed state lives in the
    # per-widget sheet built from the active (compact) resolved tokens.
    from psi6.theme.apply import psi6_button_stylesheet

    primary_sheet = psi6_button_stylesheet("psi6Primary", app.qt_app.property("psi6ResolvedTokens"))
    assert "QPushButton:pressed" in primary_sheet
    assert f"border: {app.tokens.focus_ring_width}px solid" in css
    app.set_theme("light")
