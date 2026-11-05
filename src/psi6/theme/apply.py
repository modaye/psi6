"""把 token 编译成 QApplication 样式。"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator
from contextlib import suppress
from inspect import Parameter, signature

from PySide6.QtCore import QEvent, QObject
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication, QLayout, QPushButton, QStyleFactory, QWidget

from psi6.theme.chrome import chrome_images
from psi6.theme.tokens import DEFAULT_TOKENS, Tokens

_FAMILY_RE = re.compile(r'"[^"]*"|\'[^\']*\'|[^,]+')

# 焦点环是可选能力：App(focus_ring=...) 决定是否绘制，默认关闭。
# 存成 QApplication 的 property，让逐控件重刷按钮的所有路径（restyle /
# PaletteChange 事件过滤器）都读到同一份开关。
_FOCUS_RING_KEY = "psi6FocusRingEnabled"

_FOCUS_SELECTORS: dict[str, str] = {
    "inputs": (
        "QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus,\n"
        "QPlainTextEdit:focus, QTextEdit:focus, QDateEdit:focus, QTimeEdit:focus,\n"
        'QDateTimeEdit:focus, QLineEdit[psi6State="focus"]'
    ),
    "buttons": 'QPushButton:focus, QPushButton[psi6State="focus"]',
    "dropzone": "QWidget#psi6DropZone:focus",
    "tabs": "QTabBar::tab:focus",
    "icon_button": "QToolButton#psi6IconButton:focus",
}


def _focus_rules(
    t: Tokens,
    *,
    focus_ring: bool,
    ring: int,
    focus_pad: int,
    focus_min_h: int,
) -> dict[str, str]:
    """生成全局 QSS 里的焦点规则片段。

    开启时用 ``border`` 画品牌色焦点环，并按差值收紧 padding / min-height，
    保证聚焦时外框尺寸不变、内容不位移。关闭时只留 ``outline: none`` 抑制 Qt
    原生焦点框：不画环，也不改边框 / 间距 / 高度，聚焦不产生任何视觉变化。
    选择器原样保留（含 ``psi6State`` 状态预览），所以开关只影响声明内容。
    """

    if focus_ring:
        declarations: dict[str, str] = {
            "inputs": (
                f"border: {ring}px solid {t.color_focus};\n"
                f"padding: 0 {focus_pad}px;\n"
                f"min-height: {focus_min_h}px;\n"
                "outline: none;"
            ),
            "buttons": (
                f"border: {ring}px solid {t.color_focus};\n"
                f"padding: 0 {focus_pad}px;\n"
                f"min-height: {focus_min_h}px;\n"
                "outline: none;"
            ),
            "dropzone": f"border: 2px solid {t.color_focus};",
            "tabs": (
                f"border: {ring}px solid {t.color_focus};\n"
                f"padding: {t.space_sm}px {focus_pad}px;\n"
                f"min-height: {focus_min_h}px;\n"
                "outline: none;"
            ),
            "icon_button": f"border: {ring}px solid {t.color_focus};\noutline: none;",
        }
    else:
        declarations = {key: "outline: none;" for key in _FOCUS_SELECTORS}
    rules: dict[str, str] = {}
    for key, selector in _FOCUS_SELECTORS.items():
        body = "\n".join(f"    {line}" for line in declarations[key].splitlines())
        rules[key] = f"{selector} {{\n{body}\n}}"
    return rules


def font_families(declaration: str) -> list[str]:
    """把 ``"A", "B", sans-serif`` 拆成 Qt 用的字体族回退列表。"""

    return [item.strip().strip("\"'") for item in _FAMILY_RE.findall(declaration) if item.strip()]


def build_font(tokens: Tokens) -> QFont:
    """由 ``font_family`` / ``font_size`` 造应用字体。``font_size`` 是像素，直接用 ``setPixelSize``。"""

    font = QFont()
    families = font_families(tokens.font_family)
    if families:
        font.setFamilies(families)
    font.setPixelSize(max(1, int(tokens.font_size)))
    return font


def _arrow_css(tokens: Tokens) -> str:
    """下拉/步进箭头用着色 chevron，不要 Fusion 默认三角。"""

    t = tokens
    images = chrome_images(t)
    arrow = max(12, min(t.icon_size, 16))
    slot = max(22, arrow + 10)
    spin = max(16, arrow + 4)
    return f"""
QComboBox, QDateEdit, QTimeEdit, QDateTimeEdit {{
    padding-right: {slot}px;
}}
QSpinBox, QDoubleSpinBox {{
    padding-right: {spin}px;
}}
QComboBox::drop-down, QDateEdit::drop-down, QTimeEdit::drop-down, QDateTimeEdit::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: {slot}px;
    border: none;
    background: transparent;
}}
QComboBox::down-arrow, QDateEdit::down-arrow, QTimeEdit::down-arrow, QDateTimeEdit::down-arrow {{
    image: url({images["down"]});
    width: {arrow}px;
    height: {arrow}px;
}}
QComboBox::down-arrow:on, QDateEdit::down-arrow:on, QTimeEdit::down-arrow:on, QDateTimeEdit::down-arrow:on {{
    image: url({images["down_on"]});
}}
QComboBox::down-arrow:disabled, QDateEdit::down-arrow:disabled,
QTimeEdit::down-arrow:disabled, QDateTimeEdit::down-arrow:disabled {{
    image: url({images["down_disabled"]});
}}
QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {{
    subcontrol-origin: border;
    width: {spin}px;
    border: none;
    background: transparent;
}}
QAbstractSpinBox::up-button {{
    subcontrol-position: top right;
}}
QAbstractSpinBox::down-button {{
    subcontrol-position: bottom right;
}}
QAbstractSpinBox::up-arrow {{
    image: url({images["up"]});
    width: {arrow}px;
    height: {arrow}px;
}}
QAbstractSpinBox::down-arrow {{
    image: url({images["down"]});
    width: {arrow}px;
    height: {arrow}px;
}}
QAbstractSpinBox::up-arrow:disabled {{
    image: url({images["up_disabled"]});
}}
QAbstractSpinBox::down-arrow:disabled {{
    image: url({images["down_disabled"]});
}}
"""


def _indicator_css(tokens: Tokens, *, focus_ring: bool = True) -> str:
    """勾选框与单选框的指示器：一旦控件沾了 QSS，指示器必须全部自己画。"""

    t = tokens
    images = chrome_images(t)
    box = max(14, t.icon_size)
    check_radius = max(2, t.radius - 2)
    ring = max(1, t.focus_ring_width)
    selector = "QCheckBox::indicator:focus, QRadioButton::indicator:focus"
    if focus_ring:
        indicator_focus = f"{selector} {{\n    border: {ring}px solid {t.color_focus};\n}}"
    else:
        indicator_focus = f"{selector} {{\n    outline: none;\n}}"
    return f"""
QCheckBox::indicator, QRadioButton::indicator {{
    width: {box}px;
    height: {box}px;
    border: 1px solid {t.color_control_border};
    background: {t.color_sunken};
}}
QCheckBox::indicator {{
    border-radius: {check_radius}px;
}}
QRadioButton::indicator {{
    border-radius: {box // 2}px;
}}
QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
    border-color: {t.color_primary};
}}
{indicator_focus}
QCheckBox::indicator:checked {{
    background: {t.color_primary};
    border-color: {t.color_primary};
    image: url({images["check_on"]});
}}
QCheckBox::indicator:indeterminate {{
    background: {t.color_primary};
    border-color: {t.color_primary};
    image: url({images["minus_on"]});
}}
QRadioButton::indicator:checked {{
    background: {t.color_primary};
    border-color: {t.color_primary};
    image: url({images["dot_on"]});
}}
QCheckBox::indicator:disabled, QRadioButton::indicator:disabled {{
    background: {t.color_bg};
    border-color: {t.color_border_subtle};
}}
QCheckBox::indicator:checked:disabled, QCheckBox::indicator:indeterminate:disabled {{
    background: {t.color_border};
    border-color: {t.color_border_subtle};
    image: url({images["check_muted"]});
}}
QRadioButton::indicator:checked:disabled {{
    background: {t.color_border};
    border-color: {t.color_border_subtle};
    image: url({images["dot_muted"]});
}}
"""


def build_stylesheet(tokens: Tokens, *, focus_ring: bool = True) -> str:
    """由 token 生成全局 QSS。覆盖内部工具会碰到的原生控件。

    ``focus_ring=False`` 时不画焦点环，只抑制 Qt 原生焦点框；供 ``App`` 默认关闭
    焦点样式用。默认是 ``True``，保留键盘可见性能力与既有主题断言。
    """

    t = tokens.resolve_states()
    r = t.radius
    br = t.button_radius if t.button_radius > 0 else t.radius
    wr = t.window_radius
    ch = t.control_height
    ring = max(1, t.focus_ring_width)
    pressed = t.color_pressed
    selected = t.color_selected
    primary_hover = t.color_primary_hover
    danger_pressed = t.color_danger_pressed
    pad_x = t.space_md
    # 焦点环用 border 绘制：Qt 的 outline 会在内容矩形内画框（加 offset 还会向内
    # 收缩压住文字），不能用来画外圈。边框从 1px 加宽到 ring px 会挤动内容，这里
    # 按差值收紧 padding 与 min-height，保证聚焦时控件外框尺寸不变、内容不位移。
    focus_pad = max(0, pad_x - (ring - 1))
    focus_min_h = max(12, ch - 2 * (ring - 1))
    title_fs = t.font_size_title
    title_w = t.font_weight_title
    body_w = t.font_weight_body
    setting_h = max(ch + t.space_md, 36)
    arrows = _arrow_css(t)
    indicators = _indicator_css(t, focus_ring=focus_ring)
    icons = chrome_images(t)
    focus = _focus_rules(
        t,
        focus_ring=focus_ring,
        ring=ring,
        focus_pad=focus_pad,
        focus_min_h=focus_min_h,
    )
    return f"""
QWidget {{
    font-family: {t.font_family};
    font-size: {t.font_size}px;
    font-weight: {body_w};
    color: {t.color_text};
}}
QMainWindow {{
    background: {t.color_bg};
}}
QMainWindow[frameless="true"] {{
    background: transparent;
}}
QWidget#psi6DesktopBody {{
    background: {t.color_bg};
}}
QDialog {{
    background: {t.color_elevated};
    border: 1px solid {t.color_border};
}}
QLabel {{
    background: transparent;
}}
QLabel#psi6Hint, QLabel#psi6SectionHint, QLabel#psi6EmptyHint, QLabel#psi6Breadcrumb {{
    color: {t.color_muted};
    font-size: {t.font_size_sm}px;
}}
QLabel#psi6Error {{
    color: {t.color_danger};
    font-size: {t.font_size_sm}px;
}}
QLabel#psi6SectionTitle, QLabel#psi6EmptyTitle, QLabel#psi6PageTitle, QLabel#psi6StatValue,
QLabel#psi6FormGroup, QLabel#psi6BreadcrumbCurrent {{
    font-weight: {title_w};
    font-size: {title_fs}px;
    color: {t.color_text};
}}
QLabel#psi6StatSuccess {{ color: {t.color_success}; font-weight: {title_w}; }}
QLabel#psi6StatWarning {{ color: {t.color_warning}; font-weight: {title_w}; }}
QLabel#psi6StatError {{ color: {t.color_danger}; font-weight: {title_w}; }}
/* 输入框、普通按钮、勾选框描边用 color_control_border，和分隔线 / 卡片的 color_border 分开。 */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit, QTextEdit,
QDateEdit, QTimeEdit, QDateTimeEdit {{
    border: 1px solid {t.color_control_border};
    border-radius: {r}px;
    padding: 0 {pad_x}px;
    background: {t.color_sunken};
    min-height: {ch}px;
    selection-background-color: {selected};
    selection-color: {t.color_text};
}}
QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover,
QPlainTextEdit:hover, QTextEdit:hover, QLineEdit[psi6State="hover"] {{
    border-color: {t.color_primary};
}}
QSplitter#psi6WorkspaceSplit::handle {{
    background: {t.color_border_subtle};
}}
QTextBrowser#psi6LogConsole, QTextEdit#psi6LogConsole {{
    font-family: {t.font_mono};
    font-size: {t.font_size_sm}px;
    background: {t.color_sunken};
    border: 1px solid {t.color_control_border};
    border-radius: {r}px;
    padding: {t.space_sm}px;
}}
{focus["inputs"]}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled,
QPlainTextEdit:disabled, QDateEdit:disabled, QTimeEdit:disabled, QDateTimeEdit:disabled {{
    color: {t.color_disabled};
    background: {t.color_bg};
    border: 1px solid {t.color_border_subtle};
}}
QLineEdit[invalid="true"], QWidget#psi6PathPicker[invalid="true"] QLineEdit {{
    border-color: {t.color_danger};
    background: {t.color_surface};
}}
QLineEdit#psi6SearchField {{
    min-width: 180px;
}}
{arrows}
{indicators}
QComboBox QAbstractItemView {{
    background: {t.color_surface};
    border: 1px solid {t.color_border};
    selection-background-color: {selected};
    selection-color: {t.color_text};
    outline: 0;
}}
QPushButton {{
    border: 1px solid {t.color_control_border};
    border-radius: {br}px;
    padding: 0 {pad_x}px;
    min-height: {ch}px;
    background: {t.color_surface};
    color: {t.color_text};
}}
QPushButton:hover, QPushButton[psi6State="hover"] {{
    background: {t.color_hover};
    border-color: {t.color_primary};
}}
QPushButton:pressed, QPushButton[psi6State="pressed"] {{
    background: {pressed};
    border-color: {t.color_primary};
}}
QPushButton:disabled, QPushButton[psi6State="disabled"] {{
    color: {t.color_disabled};
    background: {t.color_bg};
    border: 1px solid {t.color_border_subtle};
}}
{focus["buttons"]}
/* Themed buttons (Primary/Danger/Ghost/Link/Segment/Tag/CollapsibleHeader/NavItem)
   are styled per-widget via psi6.ui helpers (apply_psi6_button_style), not here:
   Qt's QSS engine silently drops QPushButton#psi6* rules that fall more than a few
   top-level rules after the generic QPushButton rule in a large sheet, so a single
   global sheet can never cover all eight groups. See apply_psi6_button_style. */
QWidget#psi6DropZone {{
    background: {t.color_surface};
    border: 2px dashed {t.color_border};
    border-radius: {max(r + 4, 8)}px;
}}
QWidget#psi6DropZone:hover, QWidget#psi6DropZone[dropHover="true"] {{
    border-color: {t.color_primary};
    background: {t.color_hover};
}}
QWidget#psi6DropZone[pressed="true"] {{
    background: {pressed};
    border-color: {t.color_focus};
    border-style: solid;
}}
{focus["dropzone"]}
QWidget#psi6DropZoneIcon {{
    background: {t.color_sunken};
    border: 1px solid {t.color_border};
    border-radius: {max(r + 6, 10)}px;
}}
QLabel#psi6DropZoneTitle {{
    color: {t.color_text};
    font-size: {title_fs}px;
    font-weight: {title_w};
}}
QLabel#psi6DropZoneHint {{
    color: {t.color_muted};
    font-size: {t.font_size_sm}px;
}}
QWidget#psi6Segmented {{
    background: {t.color_sunken};
    border: 1px solid {t.color_border};
    border-radius: {r}px;
}}
QWidget#psi6CheckList {{
    background: {t.color_surface};
    border: 1px solid {t.color_border};
    border-radius: {r}px;
}}
QWidget#psi6CheckRow {{
    background: transparent;
}}
QDialog#psi6ContentDialog {{
    background: {t.color_elevated};
}}
QLabel#psi6DialogTitle {{
    font-weight: {title_w};
    font-size: {title_fs}px;
}}
QWidget#psi6ImageWell {{
    background: {t.color_surface};
    border: 1px dashed {t.color_border};
    border-radius: {r}px;
}}
QWidget#psi6ImageWellThumb {{
    background: {t.color_sunken};
    border-radius: {r}px;
}}
QProgressBar {{
    border: 1px solid {t.color_control_border};
    border-radius: {r}px;
    background: {t.color_hover};
    text-align: center;
    min-height: {t.icon_size}px;
    max-height: {t.icon_size}px;
}}
QProgressBar::chunk {{
    background: {t.color_primary};
    border-radius: {max(r - 1, 1)}px;
}}
QTableWidget, QTableView, QTreeView, QListView {{
    border: 1px solid {t.color_border};
    border-radius: {r}px;
    background: {t.color_sunken};
    gridline-color: {t.color_border_subtle};
    selection-background-color: {selected};
    selection-color: {t.color_text};
    alternate-background-color: {t.color_surface};
    outline: 0;
}}
QTableWidget, QTableView {{
    font-family: {t.font_mono};
    font-size: {t.font_size_sm}px;
}}
QTableView::item, QTreeView::item, QListView::item {{
    min-height: {t.row_height}px;
    padding: 0 {t.space_sm}px;
}}
QTableView::item:hover, QTreeView::item:hover, QListView::item:hover {{
    background: {t.color_hover};
}}
QTableView::item:selected, QTreeView::item:selected, QListView::item:selected {{
    background: {selected};
    color: {t.color_text};
}}
QHeaderView::section {{
    background: {t.color_surface};
    min-height: {t.row_height}px;
    padding: {t.space_sm}px {t.space_md}px;
    border: none;
    border-bottom: 1px solid {t.color_border};
    border-right: 1px solid {t.color_border_subtle};
    font-weight: 600;
    color: {t.color_muted};
}}
QStatusBar {{
    background: {t.color_surface};
    border-top: 1px solid {t.color_border};
    color: {t.color_muted};
    min-height: {max(ch - 8, 20)}px;
}}
QCheckBox, QRadioButton {{
    spacing: {t.space_sm}px;
    background: transparent;
}}
QCheckBox:hover, QRadioButton:hover {{
    color: {t.color_text};
}}
QCheckBox:disabled, QRadioButton:disabled {{
    color: {t.color_disabled};
}}
QCheckBox:focus, QRadioButton:focus {{
    color: {t.color_text};
}}
QGroupBox, QWidget#psi6Section {{
    font-weight: 600;
    border: 1px solid {t.color_border};
    border-radius: {r}px;
    margin-top: {t.space_md + t.space_sm}px;
    padding: {t.space_lg}px;
    background: {t.color_surface};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: {t.space_md}px;
    padding: 0 {t.space_sm}px;
    color: {t.color_muted};
}}
QWidget#psi6EmptyState, QWidget#psi6Banner, QWidget#psi6ActionBar {{
    background: transparent;
}}
QWidget#psi6Banner {{
    border: 1px solid {t.color_border};
    border-radius: {r}px;
    padding: {t.space_sm}px {t.space_md}px;
    background: {t.color_surface};
}}
QWidget#psi6Banner[tone="success"] {{
    border-color: {t.color_success};
}}
QWidget#psi6Banner[tone="warning"] {{
    border-color: {t.color_warning};
}}
QWidget#psi6Banner[tone="error"] {{
    border-color: {t.color_danger};
}}
QWidget#psi6Banner[tone="info"] {{
    border-color: {t.color_info};
}}
QLabel#psi6Badge {{
    padding: 2px 8px;
    border-radius: 9px;
    font-size: {t.font_size_sm}px;
    font-weight: 600;
    background: {t.color_hover};
    color: {t.color_muted};
    max-height: 22px;
}}
QLabel#psi6Badge[tone="success"] {{
    background: {t.color_success};
    color: {t.color_on_primary};
}}
QLabel#psi6Badge[tone="warning"] {{
    background: {t.color_warning};
    color: {t.color_on_primary};
}}
QLabel#psi6Badge[tone="error"] {{
    background: {t.color_danger};
    color: {t.color_on_primary};
}}
QLabel#psi6Badge[tone="info"] {{
    background: {t.color_info};
    color: {t.color_on_primary};
}}
QWidget#psi6BusyOverlay {{
    background: {t.color_overlay};
}}
QWidget#psi6ToastHost {{
    background: transparent;
}}
QWidget#psi6Toast {{
    background: {t.color_surface};
    border: 1px solid {t.color_border};
    border-radius: {r}px;
}}
QWidget#psi6Toast[tone="success"] {{
    border-color: {t.color_success};
}}
QWidget#psi6Toast[tone="warning"] {{
    border-color: {t.color_warning};
}}
QWidget#psi6Toast[tone="error"] {{
    border-color: {t.color_danger};
}}
QWidget#psi6Toast[tone="info"] {{
    border-color: {t.color_info};
}}
QTabWidget::pane {{
    border: 1px solid {t.color_border};
    border-radius: {r}px;
    background: {t.color_surface};
    top: -1px;
}}
QTabBar::tab {{
    background: {t.color_bg};
    border: 1px solid {t.color_border};
    border-bottom: none;
    padding: {t.space_sm}px {pad_x}px;
    min-height: {ch}px;
    margin-right: 2px;
    color: {t.color_muted};
}}
QTabBar::tab:selected, QTabBar::tab[psi6State="selected"] {{
    background: {selected};
    color: {t.color_text};
    font-weight: {title_w};
}}
QTabBar::tab:hover {{
    color: {t.color_text};
    background: {t.color_hover};
}}
{focus["tabs"]}
QTabBar::tab:disabled {{
    color: {t.color_disabled};
    background: {t.color_bg};
}}
/* 关闭按钮：只要 QSS 写了 background / border / image，Qt 就不再画自带的叉号，
   所以图形自己提供；悬停用危险色提示这是「关掉」而不是普通图标。 */
QTabBar::close-button {{
    image: url("{icons["tab_close"]}");
    subcontrol-position: right;
    margin: 0 0 0 2px;
    padding: 2px;
    border: none;
    border-radius: {br}px;
    background: transparent;
}}
QTabBar::close-button:hover {{
    image: url("{icons["tab_close_on"]}");
    background: {t.color_hover};
}}
QTabBar::close-button:pressed {{
    image: url("{icons["tab_close_on"]}");
    background: {pressed};
}}
QMenuBar {{
    background: {t.color_surface};
    border-bottom: 1px solid {t.color_border};
}}
QMenuBar::item:selected {{
    background: {t.color_hover};
}}
QMenu {{
    background: {t.color_surface};
    border: 1px solid {t.color_border};
    padding: 4px;
}}
QMenu::item {{
    padding: {t.space_sm}px {t.space_lg}px;
}}
QMenu::item:disabled {{
    color: {t.color_disabled};
}}
QMenu::item:selected {{
    background: {t.color_hover};
}}
QMenu::separator {{
    height: 1px;
    background: {t.color_border};
    margin: 4px 8px;
}}
QToolTip {{
    background: {t.color_surface};
    color: {t.color_text};
    border: 1px solid {t.color_border};
    padding: 4px 8px;
}}
QSplitter::handle {{
    background: {t.color_border};
}}
QSplitter::handle:horizontal {{
    width: 1px;
}}
QSplitter::handle:vertical {{
    height: 1px;
}}
QScrollBar:vertical {{
    background: {t.color_bg};
    width: 10px;
    margin: 0;
    border: none;
}}
QScrollBar::handle:vertical {{
    background: {t.color_border};
    min-height: 24px;
    border-radius: 4px;
}}
QScrollBar:horizontal {{
    background: {t.color_bg};
    height: 10px;
    margin: 0;
    border: none;
}}
QScrollBar::handle:horizontal {{
    background: {t.color_border};
    min-width: 24px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical:hover,
QScrollBar::handle:horizontal:hover {{
    background: {t.color_muted};
}}
QScrollBar::add-line, QScrollBar::sub-line {{
    width: 0;
    height: 0;
}}
QScrollBar::add-page, QScrollBar::sub-page {{
    background: none;
}}
QAbstractScrollArea::corner {{
    background: {t.color_bg};
}}
QSlider::groove:horizontal {{
    height: 4px;
    background: {t.color_border};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
    background: {t.color_primary};
}}
QSlider::handle:horizontal:hover {{
    background: {primary_hover};
}}
QToolButton {{
    border: 1px solid transparent;
    border-radius: {r}px;
    padding: 4px 8px;
    background: transparent;
}}
QToolButton:hover {{
    background: {t.color_hover};
    border-color: {t.color_control_border};
}}
QToolButton:pressed {{
    background: {pressed};
    border-color: {t.color_control_border};
}}
QMessageBox {{
    background: {t.color_bg};
}}
QFrame#psi6Rule {{
    color: {t.color_border};
    max-height: 1px;
}}
QWidget#psi6Sidebar {{
    background: {t.color_sidebar};
    border-right: 1px solid {t.color_border};
}}
QLabel#psi6SidebarTitle {{
    font-weight: {title_w};
    font-size: {title_fs}px;
    color: {t.color_text};
    padding: 4px 4px 12px 4px;
}}
QToolButton#psi6IconButton {{
    border: 1px solid transparent;
    border-radius: {r}px;
    background: transparent;
    padding: 0;
    color: {t.color_text};
}}
QToolButton#psi6IconButton:hover {{
    background: {t.color_hover};
    border-color: {t.color_control_border};
}}
QToolButton#psi6IconButton:pressed {{
    background: {pressed};
    border-color: {t.color_control_border};
}}
{focus["icon_button"]}
QToolButton#psi6IconButton:disabled {{
    color: {t.color_disabled};
    background: transparent;
    border: 1px solid transparent;
}}
QLabel#psi6PageHint {{
    color: {t.color_muted};
    font-size: {t.font_size_sm}px;
    font-weight: {body_w};
}}
QWidget#psi6StatCard {{
    background: {t.color_surface};
    border: 1px solid {t.color_border};
    border-radius: {r}px;
}}
QLabel#psi6StatValue {{
    font-size: {title_fs}px;
    font-weight: {title_w};
    font-family: {t.font_mono};
}}
QWidget#psi6ToolTile {{
    background: {t.color_surface};
    border: 1px solid {t.color_border};
    border-radius: {r}px;
}}
QWidget#psi6ToolTile:hover {{
    border-color: {t.color_primary};
    background: {t.color_hover};
}}

/* 示例画廊：首屏与用例卡片 */
QWidget#psi6GalleryHeader {{
    background: {t.color_surface};
    border-bottom: 1px solid {t.color_border_subtle};
}}
QWidget#psi6GalleryBrand {{
    background: {t.color_primary};
    border-radius: 12px;
}}
QLabel#psi6GalleryTitle {{
    font-size: {title_fs + 8}px;
    font-weight: {title_w};
    color: {t.color_text};
}}
QLabel#psi6GallerySub {{
    color: {t.color_muted};
    font-size: {t.font_size}px;
}}
QLabel#psi6GalleryCat {{
    color: {t.color_text};
    font-size: {t.font_size + 1}px;
    font-weight: {title_w};
}}
QWidget#psi6Tile {{
    background: {t.color_surface};
    border: 1px solid {t.color_border};
    border-radius: {r}px;
}}
QWidget#psi6Tile:hover {{
    border-color: {t.color_primary};
    background: {t.color_hover};
}}
QLabel#psi6TileTitle {{
    font-weight: {title_w};
    color: {t.color_text};
    font-size: {t.font_size}px;
}}
QLabel#psi6TileDesc {{
    color: {t.color_muted};
    font-size: {t.font_size_sm}px;
}}
QLabel#psi6TileArrow {{
    color: {t.color_muted};
    font-size: {title_fs}px;
}}
QWidget#psi6Tile:hover QLabel#psi6TileArrow {{
    color: {t.color_primary};
}}
QLabel#psi6TileTag {{
    color: {t.color_muted};
    font-size: {t.font_size_sm - 1}px;
    background: {t.color_sunken};
    border: 1px solid {t.color_border_subtle};
    border-radius: {max(4, r - 2)}px;
    padding: 2px 8px;
}}
QWidget#psi6Bubble[role="assistant"] {{
    background: {t.color_surface};
    border: 1px solid {t.color_border};
    border-radius: 8px;
}}
QWidget#psi6Bubble[role="user"] {{
    background: {t.color_user_bubble};
    color: {t.color_user_on_bubble};
    border-radius: 8px;
}}
QWidget#psi6Bubble[role="user"] QLabel {{
    color: {t.color_user_on_bubble};
}}
QWidget#psi6Composer {{
    background: {t.color_surface};
    border: 1px solid {t.color_control_border};
    border-radius: {r}px;
}}
QWidget#psi6Transport {{
    background: {t.color_surface};
    border: 1px solid {t.color_border};
    border-radius: {r}px;
}}
QWidget#psi6ChangeRow {{
    background: {t.color_surface};
    border: 1px solid {t.color_border};
    border-radius: {r}px;
}}
QWidget#psi6ChangeRow[selected="true"] {{
    border-color: {t.color_primary};
    background: {selected};
}}
QWidget#psi6DesktopRoot {{
    background: {t.color_bg};
    border: 1px solid {t.color_border};
}}
QWidget#psi6EdgeGrip {{
    background: transparent;
}}
QWidget#psi6DesktopRoot[rounded="true"] {{
    border-radius: {wr}px;
}}
QWidget#psi6TitleBar {{
    background: {t.color_sidebar};
    border-bottom: 1px solid {t.color_border};
}}
QWidget#psi6TitleBar[rounded="true"] {{
    border-top-left-radius: {wr}px;
    border-top-right-radius: {wr}px;
}}
QStatusBar#psi6WindowStatus {{
    background: {t.color_surface};
    border-top: 1px solid {t.color_border};
    border-bottom-left-radius: 0;
    border-bottom-right-radius: 0;
}}
QStatusBar#psi6WindowStatus[rounded="true"] {{
    border-bottom-left-radius: {wr}px;
    border-bottom-right-radius: {wr}px;
}}
QLabel#psi6TitleText {{
    font-weight: {title_w};
}}
QToolButton#psi6TitleButton {{
    border: 1px solid transparent;
    background: transparent;
    padding: 0;
}}
QToolButton#psi6TitleButton:hover {{
    background: {t.color_hover};
    border-color: {t.color_control_border};
}}
QToolButton#psi6TitleButton:pressed {{
    background: {pressed};
    border-color: {t.color_control_border};
}}
QToolButton#psi6TitleClose {{
    border: 1px solid transparent;
    background: transparent;
    padding: 0;
}}
QToolButton#psi6TitleClose:hover {{
    background: {t.color_danger};
    border-color: {t.color_danger};
}}
QToolButton#psi6TitleClose:pressed {{
    background: {danger_pressed};
    border-color: {danger_pressed};
}}
QDialog#psi6CommandPalette {{
    background: {t.color_surface};
    border: 1px solid {t.color_border};
    border-radius: {r}px;
}}
QLabel#psi6Kbd {{
    font-family: {t.font_mono};
    font-size: {t.font_size_sm}px;
    padding: 1px 6px;
    border: 1px solid {t.color_border};
    border-radius: 3px;
    background: {t.color_sunken};
    color: {t.color_muted};
}}
QScrollArea#psi6DiffView {{
    background: {t.color_surface};
    border: 1px solid {t.color_border};
    border-radius: {r}px;
}}
QWidget#psi6DiffHost {{
    background: {t.color_surface};
}}
QLabel#psi6DiffAdd, QLabel#psi6DiffDel, QLabel#psi6DiffCtx {{
    font-family: {t.font_mono};
    font-size: {t.font_size_sm}px;
    background: transparent;
    padding: 2px 8px;
}}
QLabel#psi6DiffAdd {{
    color: {t.color_success};
}}
QLabel#psi6DiffDel {{
    color: {t.color_danger};
}}
QLabel#psi6DiffCtx {{
    color: {t.color_text};
}}
QLabel#psi6StepMark {{
    border-radius: 10px;
    background: {t.color_hover};
    color: {t.color_muted};
    font-size: {t.font_size_sm}px;
    font-weight: 600;
}}
QWidget#psi6StepNode[state="current"] QLabel#psi6StepMark {{
    background: {t.color_primary};
    color: {t.color_on_primary};
}}
QWidget#psi6Sparkline {{
    background: transparent;
}}
QAbstractButton#psi6Switch {{
    background: transparent;
    border: none;
}}
QWidget#psi6SettingRow {{
    background: transparent;
    min-height: {setting_h}px;
}}
QLabel#psi6SettingTitle {{
    font-weight: 600;
    color: {t.color_text};
}}
"""


def apply_theme(
    app: QApplication, tokens: Tokens | None = None, *, focus_ring: bool = True
) -> None:
    """安装字体、Fusion、调色板与样式表，使未封装的原生控件也可直接使用。

    ``focus_ring=False`` 关闭全局与逐控件按钮的焦点环（App 默认如此）。开关要写在
    ``setPalette`` 之前：PaletteChange 事件过滤器会立刻按它重刷主题化按钮。
    """

    t = (tokens or DEFAULT_TOKENS).resolve_states()
    app.setProperty(_FOCUS_RING_KEY, bool(focus_ring))
    # Token 必须在 setPalette / setStyleSheet 之前写入：那些调用会触发
    # IconButton.changeEvent，若仍读到上一套 psi6Color*，深色里就会变成深色图标。
    from psi6.icons.registry import apply_theme_icons
    from psi6.theme.runtime import publish_tokens

    publish_tokens(app, t)
    apply_theme_icons(icon_dir=t.icon_dir, icons=t.icons)
    app.setFont(build_font(t))
    fusion = QStyleFactory.create("Fusion")
    if fusion is not None:
        app.setStyle(fusion)
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(t.color_bg))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(t.color_text))
    palette.setColor(QPalette.ColorRole.Base, QColor(t.color_sunken))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(t.color_surface))
    palette.setColor(QPalette.ColorRole.Text, QColor(t.color_text))
    palette.setColor(QPalette.ColorRole.Button, QColor(t.color_surface))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(t.color_text))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(t.color_selected))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(t.color_text))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(t.color_muted))
    palette.setColor(QPalette.ColorRole.Link, QColor(t.color_primary))
    palette.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(t.color_disabled)
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(t.color_disabled)
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(t.color_disabled)
    )
    # 主题化按钮是逐控件设置样式表的（见 KNOWN_KINDS 注释），
    # 它们的样式表由 apply_psi6_button_style 依据这份 token 生成，
    # 所以 token 必须在 setPalette 之前写入：setPalette 会立刻派发 PaletteChange，
    # 过滤器读到旧 token 就会把按钮刷成上一套主题的颜色。
    app.setProperty(_RESOLVED_TOKENS_KEY, t)
    install_button_style_sync(app)
    app.setPalette(palette)
    app.setStyleSheet(build_stylesheet(t, focus_ring=focus_ring))
    restyle_themed_buttons(app)
    refresh_metrics(app)
    for widget in app.topLevelWidgets():
        sync = getattr(widget, "sync_shape", None)
        if callable(sync):
            sync()


# ---------------------------------------------------------------------------
# Themed buttons styled per-widget
# ---------------------------------------------------------------------------
# Qt's QSS engine silently drops ``QPushButton#psi6*`` ID rules that appear more
# than a handful of top-level rules after the generic ``QPushButton`` rule in a
# large global sheet (verified empirically: ~7-rule window, non-resettable even
# by repeating the type selector). With 8 themed button groups (~38 top-level
# rules) one global sheet can never satisfy that, so themed buttons are styled
# per-widget instead. A per-widget stylesheet is parsed standalone and is immune
# to the global cascade bug, so every themed button renders correctly.
KNOWN_KINDS = {
    "psi6Primary",
    "psi6Danger",
    "psi6Ghost",
    "psi6Link",
    "psi6Segment",
    "psi6Tag",
    "psi6CollapsibleHeader",
    "psi6NavItem",
}
_RESOLVED_TOKENS_KEY = "psi6ResolvedTokens"
_style_filter: QObject | None = None


def psi6_button_stylesheet(
    kind: str, tokens: Tokens | None = None, *, focus_ring: bool = True
) -> str:
    """Standalone QSS for a themed button kind, resolved to token colors.

    The widget styles itself, so selectors are plain ``QPushButton`` (plus
    attribute / pseudo-state variants). ``widget.setStyleSheet(result)`` applies
    reliably regardless of the global sheet's cascade bug.
    """

    t = (tokens or DEFAULT_TOKENS).resolve_states()
    r = t.radius
    ch = t.control_height
    ring = max(1, t.focus_ring_width)
    primary_hover = t.color_primary_hover
    primary_pressed = t.color_primary_pressed
    danger_hover = t.color_danger_hover
    danger_pressed = t.color_danger_pressed
    pad_x = t.space_md
    # 有边框按钮的焦点环：按差值收紧 padding 与 min-height，聚焦时外框尺寸不变
    focus_pad = max(0, pad_x - (ring - 1))
    focus_min_h = max(12, ch - 2 * (ring - 1))
    # 无边框按钮（主/危险/链接/导航/分段）基础边框为 0，焦点环要多扣 1px
    focus_pad_nb = max(0, pad_x - ring)
    focus_min_h_nb = max(12, ch - 2 * ring)
    nav_focus_pad = max(0, t.space_sm - ring)
    title_w = t.font_weight_title

    # 焦点环开关与全局 QSS 一致：关闭时只抑制原生焦点框，聚焦不改外观与尺寸。
    if focus_ring:
        primary_focus = (
            "QPushButton:focus {\n"
            f"    border: {ring}px solid {t.color_on_primary};\n"
            f"    padding: 0 {focus_pad_nb}px;\n"
            f"    min-height: {focus_min_h_nb}px;\n"
            "    outline: none;\n"
            "}"
        )
        danger_focus = primary_focus
        ghost_focus = (
            "QPushButton:focus {\n"
            f"    border: {ring}px solid {t.color_focus};\n"
            f"    padding: 0 {focus_pad}px;\n"
            f"    min-height: {focus_min_h}px;\n"
            "    outline: none;\n"
            "}"
        )
        link_focus = (
            "QPushButton:focus { border: none; text-decoration: underline; outline: none; }"
        )
        segment_focus = (
            f"QPushButton:focus {{ border: {ring}px solid {t.color_focus}; "
            f"min-height: {focus_min_h_nb}px; outline: none; }}"
        )
        nav_focus = (
            'QPushButton:focus, QPushButton[psi6State="focus"] {\n'
            f"    border: {ring}px solid {t.color_focus};\n"
            f"    padding: 0 {nav_focus_pad}px;\n"
            f"    min-height: {focus_min_h_nb}px;\n"
            "    outline: none;\n"
            "}"
        )
    else:
        neutral_focus = 'QPushButton:focus, QPushButton[psi6State="focus"] {\n    outline: none;\n}'
        primary_focus = danger_focus = ghost_focus = neutral_focus
        link_focus = segment_focus = nav_focus = neutral_focus

    if kind == "psi6Primary":
        return f"""\
QPushButton {{
    background: {t.color_primary};
    color: {t.color_on_primary};
    border: none;
    font-weight: {title_w};
}}
QPushButton:hover {{ background: {primary_hover}; }}
QPushButton:pressed {{ background: {primary_pressed}; }}
QPushButton:disabled {{ background: {t.color_border}; color: {t.color_muted}; border: none; }}
{primary_focus}"""
    if kind == "psi6Danger":
        return f"""\
QPushButton {{
    background: {t.color_danger};
    color: {t.color_on_primary};
    border: none;
    font-weight: {title_w};
}}
QPushButton:hover {{ background: {danger_hover}; }}
QPushButton:pressed {{ background: {danger_pressed}; }}
QPushButton:disabled {{ background: {t.color_border}; color: {t.color_muted}; border: none; }}
{danger_focus}"""
    if kind == "psi6Ghost":
        return f"""\
QPushButton {{
    background: transparent;
    border: 1px solid {t.color_control_border};
    color: {t.color_text};
}}
QPushButton:hover {{ background: {t.color_hover}; border-color: {t.color_primary}; }}
QPushButton:pressed {{ background: {t.color_pressed}; border-color: {t.color_primary}; }}
{ghost_focus}
QPushButton:disabled {{ color: {t.color_disabled}; background: transparent; border-color: {t.color_border_subtle}; }}"""
    if kind == "psi6Link":
        return f"""\
QPushButton {{
    background: transparent;
    border: none;
    color: {t.color_primary};
    min-height: {max(ch - 8, 20)}px;
    padding: 0 {t.space_sm}px;
    font-weight: {title_w};
}}
QPushButton:hover {{ background: transparent; border: none; color: {t.color_focus}; }}
QPushButton:pressed {{ background: transparent; }}
{link_focus}
QPushButton:disabled {{ color: {t.color_disabled}; }}"""
    if kind == "psi6Segment":
        return f"""\
QPushButton {{
    border: none;
    background: transparent;
    color: {t.color_muted};
    min-height: {ch}px;
    border-radius: {max(r - 1, 1)}px;
}}
QPushButton:hover {{ background: {t.color_hover}; color: {t.color_text}; border: none; }}
QPushButton:checked {{ background: {t.color_selected}; color: {t.color_text}; font-weight: {title_w}; border: none; }}
{segment_focus}
QPushButton:disabled {{ color: {t.color_disabled}; }}"""
    if kind == "psi6CollapsibleHeader":
        return f"""\
QPushButton {{
    text-align: left;
    font-weight: 600;
    background: transparent;
    border: none;
    padding: 4px 0;
    color: {t.color_muted};
}}
QPushButton:hover {{ color: {t.color_text}; background: transparent; border: none; }}"""
    if kind == "psi6Tag":
        return f"""\
QPushButton {{
    padding: 2px 10px;
    border-radius: 11px;
    font-size: {t.font_size_sm}px;
    font-weight: 600;
    background: {t.color_hover};
    color: {t.color_muted};
    border: 1px solid {t.color_control_border};
}}
QPushButton:hover {{ border-color: {t.color_primary}; color: {t.color_text}; }}
QPushButton:checked {{ background: {t.color_info}; color: {t.color_on_primary}; border: none; }}
QPushButton:disabled {{ color: {t.color_disabled}; background: {t.color_bg}; border-color: {t.color_border_subtle}; }}"""
    if kind == "psi6NavItem":
        return f"""\
QPushButton {{
    text-align: left;
    padding: 0 {t.space_sm}px;
    min-height: {ch}px;
    border: none;
    border-radius: {r}px;
    background: transparent;
    color: {t.color_sidebar_text};
}}
QPushButton:hover, QPushButton[psi6State="hover"] {{ background: {t.color_hover}; color: {t.color_text}; }}
QPushButton:pressed, QPushButton[psi6State="pressed"] {{ background: {t.color_pressed}; color: {t.color_text}; }}
QPushButton:checked, QPushButton[psi6State="selected"] {{ background: {t.color_selected}; color: {t.color_text}; font-weight: {title_w}; }}
{nav_focus}
QPushButton:disabled {{ color: {t.color_disabled}; background: transparent; }}
QPushButton[compact="true"] {{ text-align: center; padding: 0; }}"""
    return ""


def apply_psi6_button_style(widget, kind: str | None = None) -> None:
    """Style ``widget`` as a themed psi6 button using the active resolved tokens."""

    kind = kind or widget.objectName()
    if kind not in KNOWN_KINDS:
        return
    app = QApplication.instance()
    tokens = app.property(_RESOLVED_TOKENS_KEY) if app is not None else None
    enabled = app.property(_FOCUS_RING_KEY) if app is not None else None
    focus_ring = True if enabled is None else bool(enabled)
    widget.setStyleSheet(psi6_button_stylesheet(kind, tokens, focus_ring=focus_ring))


def restyle_themed_buttons(app: QApplication) -> None:
    """按当前 token 重刷所有主题化按钮。

    主题化按钮的样式是逐控件设置的，不会随全局样式表级联更新，
    所以换肤后必须显式重刷一遍，否则按钮会留在上一套主题的颜色上。
    """

    for widget in app.allWidgets():
        if isinstance(widget, QPushButton) and widget.objectName() in KNOWN_KINDS:
            apply_psi6_button_style(widget)


# ---------------------------------------------------------------------------
# Metric hooks: QSS cannot resize geometry cached at construction time
# ---------------------------------------------------------------------------
def _metrics_hook(target: object) -> Callable[[], None] | None:
    """取无必填参数的 ``apply_metrics``；签名不合约定就跳过，不猜参数。"""

    hook = getattr(target, "apply_metrics", None)
    if not callable(hook):
        return None
    try:
        parameters = signature(hook).parameters
    except (TypeError, ValueError):
        return None
    for parameter in parameters.values():
        if parameter.default is Parameter.empty and parameter.kind not in (
            Parameter.VAR_POSITIONAL,
            Parameter.VAR_KEYWORD,
        ):
            return None
    return hook


def _widget_layouts(widget: QWidget) -> Iterator[QLayout]:
    """迭代控件的整棵布局树；自定义 ``QLayout`` 不是 widget，收不到 StyleChange。"""

    pending: list[QLayout] = []
    with suppress(Exception):
        root = widget.layout()
        if root is not None:
            pending.append(root)
    seen: set[int] = set()
    while pending:
        layout = pending.pop()
        key = id(layout)
        if key in seen:
            continue
        seen.add(key)
        yield layout
        try:
            for index in range(layout.count()):
                item = layout.itemAt(index)
                if item is None:
                    continue
                child = item.layout()
                if child is not None:
                    pending.append(child)
        except Exception:
            # 某个布局在遍历中失效（控件已 deleteLater）不应中断其余刷新。
            continue


def refresh_metrics(app: QApplication) -> int:
    """按当前 token 重算所有带 ``apply_metrics()`` 的控件与布局，返回刷新数量。

    ``apply_theme`` 只重设字体、调色板和样式表：构造时把间距 / 固定宽高缓存下来的
    组件不会因此重排，自定义 ``QLayout`` 更是连 ``StyleChange`` 都收不到。主题或
    响应式密度切换后显式刷一遍，这些控件才有机会按新尺寸重算。

    约定 ``apply_metrics`` 可无参调用；单个 hook 抛错（含 C++ 对象已销毁）只跳过它，
    不污染 Qt 事件派发，也不影响其余控件——沿用 Toast 段错误复盘的做法。
    """

    widgets: list[QWidget] = []
    with suppress(Exception):
        widgets = list(app.allWidgets())
    seen: set[int] = set()
    refreshed = 0
    for widget in widgets:
        targets: list[object] = [widget, *_widget_layouts(widget)]
        for target in targets:
            key = id(target)
            if key in seen:
                continue
            seen.add(key)
            hook = _metrics_hook(target)
            if hook is None:
                continue
            with suppress(Exception):
                hook()
                refreshed += 1
    return refreshed


class _Psi6ButtonStyleFilter(QObject):
    """Re-apply themed button styles when the palette (theme) changes."""

    def eventFilter(self, obj, event):
        try:
            # 只认 PaletteChange：setStyleSheet 自身也会发 StyleChange，
            # 若一并处理就会自触发成无限递归（栈溢出崩溃）。
            if (
                int(event.type()) == int(QEvent.Type.PaletteChange)
                and isinstance(obj, QPushButton)
                and obj.objectName() in KNOWN_KINDS
            ):
                apply_psi6_button_style(obj)
        except Exception:
            # Never let a styling hiccup corrupt Qt's event dispatch.
            pass
        return False


def install_button_style_sync(app: QApplication) -> None:
    """Install the palette-change hook that re-styles themed buttons."""

    global _style_filter
    if _style_filter is not None:
        return
    _style_filter = _Psi6ButtonStyleFilter(app)
    app.installEventFilter(_style_filter)
