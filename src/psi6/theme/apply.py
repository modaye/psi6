"""把 token 编译成 QApplication 样式。"""

from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QStyleFactory

from psi6.theme.chrome import chrome_images
from psi6.theme.tokens import DEFAULT_TOKENS, Tokens


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


def build_stylesheet(tokens: Tokens) -> str:
    """由 token 生成全局 QSS。覆盖内部工具会碰到的原生控件。"""

    t = tokens
    r = t.radius
    br = t.button_radius if t.button_radius > 0 else t.radius
    wr = t.window_radius
    ch = t.control_height
    pad_x = t.space_md
    section_fs = t.font_size + 1
    page_fs = t.font_size + 3
    stat_fs = t.font_size + 9
    setting_h = max(ch + t.space_md, 36)
    arrows = _arrow_css(t)
    return f"""
QWidget {{
    font-family: {t.font_family};
    font-size: {t.font_size}px;
    color: {t.color_text};
}}
QMainWindow {{
    background: transparent;
}}
QDialog {{
    background: {t.color_bg};
}}
QLabel {{
    background: transparent;
}}
QLabel#psi6Hint, QLabel#psi6SectionHint, QLabel#psi6EmptyHint {{
    color: {t.color_muted};
    font-size: {t.font_size_sm}px;
}}
QLabel#psi6Error {{
    color: {t.color_danger};
    font-size: {t.font_size_sm}px;
}}
QLabel#psi6SectionTitle, QLabel#psi6EmptyTitle {{
    font-weight: 600;
    font-size: {section_fs}px;
    color: {t.color_text};
}}
QLabel#psi6StatSuccess {{ color: {t.color_success}; font-weight: 600; }}
QLabel#psi6StatWarning {{ color: {t.color_warning}; font-weight: 600; }}
QLabel#psi6StatError {{ color: {t.color_danger}; font-weight: 600; }}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit, QTextEdit,
QDateEdit, QTimeEdit, QDateTimeEdit {{
    border: 1px solid {t.color_border};
    border-radius: {r}px;
    padding: 0 {pad_x}px;
    background: {t.color_sunken};
    min-height: {ch}px;
    selection-background-color: {t.color_primary};
    selection-color: {t.color_on_primary};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QPlainTextEdit:focus, QTextEdit:focus, QDateEdit:focus, QTimeEdit:focus,
QDateTimeEdit:focus {{
    border: 1px solid {t.color_focus};
}}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled,
QPlainTextEdit:disabled, QDateEdit:disabled, QTimeEdit:disabled, QDateTimeEdit:disabled {{
    color: {t.color_disabled};
    background: {t.color_bg};
}}
QLineEdit[invalid="true"], QWidget#psi6PathPicker[invalid="true"] QLineEdit {{
    border: 1px solid {t.color_danger};
}}
QLineEdit#psi6SearchField {{
    min-width: 180px;
}}
{arrows}
QComboBox QAbstractItemView {{
    background: {t.color_surface};
    border: 1px solid {t.color_border};
    selection-background-color: {t.color_hover};
    selection-color: {t.color_text};
    outline: 0;
}}
QPushButton {{
    border: 1px solid {t.color_border};
    border-radius: {br}px;
    padding: 0 {pad_x}px;
    min-height: {ch}px;
    background: {t.color_surface};
    color: {t.color_text};
}}
QPushButton:hover {{
    background: {t.color_hover};
    border-color: {t.color_primary};
}}
QPushButton:pressed {{
    background: {t.color_bg};
}}
QPushButton:disabled {{
    color: {t.color_disabled};
    background: {t.color_bg};
}}
QPushButton:focus {{
    border: 1px solid {t.color_focus};
}}
QPushButton#psi6Primary {{
    background: {t.color_primary};
    color: {t.color_on_primary};
    border: none;
    font-weight: 600;
}}
QPushButton#psi6Primary:hover {{
    background: {t.color_focus};
}}
QPushButton#psi6Primary:disabled {{
    background: {t.color_border};
    color: {t.color_muted};
}}
QPushButton#psi6Danger {{
    color: {t.color_danger};
    border-color: {t.color_danger};
}}
QPushButton#psi6Danger:hover {{
    background: {t.color_hover};
}}
QPushButton#psi6Ghost {{
    background: transparent;
    border: 1px solid {t.color_border};
    color: {t.color_text};
}}
QPushButton#psi6Ghost:hover {{
    background: {t.color_hover};
    border-color: {t.color_primary};
}}
QPushButton#psi6Ghost:pressed {{
    background: {t.color_bg};
}}
QPushButton#psi6Link {{
    background: transparent;
    border: none;
    color: {t.color_primary};
    min-height: {max(ch - 8, 20)}px;
    padding: 0 {t.space_sm}px;
    font-weight: 600;
}}
QPushButton#psi6Link:hover {{
    background: transparent;
    border: none;
    color: {t.color_focus};
}}
QPushButton#psi6Link:pressed {{
    background: transparent;
}}
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
    background: {t.color_bg};
    border-color: {t.color_focus};
    border-style: solid;
}}
QWidget#psi6DropZone:focus {{
    border: 2px solid {t.color_focus};
}}
QWidget#psi6DropZoneIcon {{
    background: {t.color_sunken};
    border: 1px solid {t.color_border};
    border-radius: {max(r + 6, 10)}px;
}}
QLabel#psi6DropZoneTitle {{
    color: {t.color_text};
    font-size: {t.font_size + 2}px;
    font-weight: 600;
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
QPushButton#psi6Segment {{
    border: none;
    background: transparent;
    color: {t.color_muted};
    min-height: {ch}px;
    border-radius: {max(r - 1, 1)}px;
}}
QPushButton#psi6Segment:hover {{
    background: {t.color_hover};
    color: {t.color_text};
    border: none;
}}
QPushButton#psi6Segment:checked {{
    background: {t.color_surface};
    color: {t.color_text};
    font-weight: 600;
    border: none;
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
    background: {t.color_bg};
}}
QLabel#psi6DialogTitle {{
    font-weight: 650;
    font-size: {page_fs}px;
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
    border: 1px solid {t.color_border};
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
    gridline-color: {t.color_bg};
    selection-background-color: {t.color_hover};
    selection-color: {t.color_text};
    alternate-background-color: {t.color_surface};
    outline: 0;
}}
QTableWidget, QTableView {{
    font-family: {t.font_mono};
    font-size: {t.font_size_sm}px;
}}
QHeaderView::section {{
    background: {t.color_surface};
    padding: {t.space_sm}px {t.space_md}px;
    border: none;
    border-bottom: 1px solid {t.color_border};
    border-right: 1px solid {t.color_bg};
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
QCheckBox:disabled, QRadioButton:disabled {{
    color: {t.color_disabled};
}}
QGroupBox, QWidget#psi6Section {{
    font-weight: 600;
    border: 1px solid {t.color_border};
    border-radius: {r}px;
    margin-top: 12px;
    padding: {t.space_md}px;
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
QPushButton#psi6CollapsibleHeader {{
    text-align: left;
    font-weight: 600;
    background: transparent;
    border: none;
    padding: 4px 0;
    color: {t.color_muted};
}}
QPushButton#psi6CollapsibleHeader:hover {{
    color: {t.color_text};
    background: transparent;
    border: none;
}}
QWidget#psi6BusyOverlay {{
    background: {t.color_overlay};
}}
QPushButton#psi6Tag {{
    padding: 2px 10px;
    border-radius: 11px;
    font-size: {t.font_size_sm}px;
    font-weight: 600;
    background: {t.color_hover};
    color: {t.color_muted};
    border: 1px solid {t.color_border};
}}
QPushButton#psi6Tag:hover {{
    border-color: {t.color_primary};
    color: {t.color_text};
}}
QPushButton#psi6Tag:checked {{
    background: {t.color_info};
    color: {t.color_on_primary};
    border: none;
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
QTabBar::tab:selected {{
    background: {t.color_surface};
    color: {t.color_text};
    font-weight: 600;
}}
QTabBar::tab:hover {{
    color: {t.color_text};
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
    padding: 6px 18px;
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
QToolButton {{
    border: 1px solid transparent;
    border-radius: {r}px;
    padding: 4px 8px;
    background: transparent;
}}
QToolButton:hover {{
    background: {t.color_hover};
    border-color: {t.color_border};
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
    font-weight: 700;
    color: {t.color_text};
    padding: 4px 4px 12px 4px;
}}
QPushButton#psi6NavItem {{
    text-align: left;
    padding: 0 {t.space_sm}px;
    min-height: {ch}px;
    border: none;
    border-radius: {r}px;
    background: transparent;
    color: {t.color_sidebar_text};
}}
QPushButton#psi6NavItem:hover {{
    background: {t.color_hover};
    color: {t.color_text};
}}
QPushButton#psi6NavItem:checked {{
    background: {t.color_surface};
    color: {t.color_text};
    font-weight: 600;
}}
QPushButton#psi6NavItem[compact="true"] {{
    text-align: center;
    padding: 0;
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
    border-color: {t.color_border};
}}
QToolButton#psi6IconButton:pressed {{
    background: {t.color_bg};
}}
QLabel#psi6PageTitle {{
    font-size: {page_fs}px;
    font-weight: 650;
}}
QLabel#psi6PageHint {{
    color: {t.color_muted};
    font-size: {t.font_size_sm}px;
}}
QWidget#psi6StatCard {{
    background: {t.color_surface};
    border: 1px solid {t.color_border};
    border-radius: {r}px;
}}
QLabel#psi6StatValue {{
    font-size: {stat_fs}px;
    font-weight: 650;
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
    border: 1px solid {t.color_border};
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
    background: {t.color_hover};
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
    font-weight: 600;
}}
QToolButton#psi6TitleButton {{
    border: 1px solid transparent;
    background: transparent;
    padding: 0;
}}
QToolButton#psi6TitleButton:hover {{
    background: {t.color_hover};
    border-color: {t.color_border};
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


def apply_theme(app: QApplication, tokens: Tokens | None = None) -> None:
    """安装 Fusion、调色板与样式表，使未封装的原生控件也可直接使用。"""

    t = tokens or DEFAULT_TOKENS
    # Token 必须在 setPalette / setStyleSheet 之前写入：那些调用会触发
    # IconButton.changeEvent，若仍读到上一套 psi6Color*，深色里就会变成深色图标。
    from psi6.icons.registry import apply_theme_icons
    from psi6.theme.runtime import publish_tokens

    publish_tokens(app, t)
    apply_theme_icons(icon_dir=t.icon_dir, icons=t.icons)
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
    palette.setColor(QPalette.ColorRole.Highlight, QColor(t.color_primary))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(t.color_on_primary))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(t.color_muted))
    palette.setColor(QPalette.ColorRole.Link, QColor(t.color_primary))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(t.color_disabled))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(t.color_disabled))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(t.color_disabled))
    app.setPalette(palette)
    app.setStyleSheet(build_stylesheet(t))
    for widget in app.topLevelWidgets():
        sync = getattr(widget, "_sync_shape", None)
        if callable(sync):
            sync()
