"""绘制 0.7.0 阶段二的桌面参考稿。

使用现有 ``Tokens`` 的浅色、深色和现代、紧凑度量，离屏画到 PNG。
不调用 ``apply_theme``，也不修改控件外观。画面是设计原型，不是实现验收图。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QByteArray, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QGuiApplication, QImage, QPainter, QPen
from PySide6.QtSvg import QSvgRenderer

from psi6.icons.glyphs import svg_markup
from psi6.theme.colors import mix_hex
from psi6.theme.tokens import Tokens, merge_style

ROOT = Path(__file__).resolve().parents[1] / "docs" / "design" / "0.7.0" / "reference"
_RGBA = re.compile(r"rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)")

DESTINATIONS = (
    ("file-index", "文件", "folder"),
    ("task", "任务", "play"),
    ("workbench", "工作台", "sidebar"),
    ("components", "组件", "table"),
    ("chat", "对话", "message"),
    ("settings", "设置", "settings"),
)
THEMES = (
    ("light-modern", "light", "modern"),
    ("dark-modern", "dark", "modern"),
    ("light-compact", "light", "compact"),
    ("dark-compact", "dark", "compact"),
)
SIZES = (("wide", 1180, 760), ("medium", 960, 680), ("narrow", 640, 520))
PAGES = ("settings", "file-index", "task", "workbench", "components", "chat")


def qcolor(value: str) -> QColor:
    """把 token 色值转成 Qt 颜色，包括 ``rgba()`` 遮罩。"""

    match = _RGBA.fullmatch(value.strip())
    if match:
        red, green, blue, alpha = (int(part) for part in match.groups())
        return QColor(red, green, blue, alpha)
    return QColor(value)


@dataclass(frozen=True)
class Kit:
    """一种旗舰组合的绘制参数。"""

    name: str
    tokens: Tokens

    @classmethod
    def load(cls, name: str, base: str, style: str) -> Kit:
        raw = Tokens.dark() if base == "dark" else Tokens.light()
        return cls(name, merge_style(raw, style, {}).resolve_states())

    @property
    def control_gap(self) -> int:
        """可聚焦控件之间的间距。紧凑的 ``space_sm`` 只有 4，不够放焦点环。"""

        if self.tokens.space_sm >= 8:
            return self.tokens.space_sm
        return self.tokens.space_md


class Canvas:
    """一张参考稿的画布。坐标都是逻辑像素。"""

    def __init__(self, width: int, height: int, kit: Kit) -> None:
        self.kit = kit
        self.tokens = kit.tokens
        self.image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
        self.image.fill(qcolor(kit.tokens.color_bg))
        self.painter = QPainter(self.image)
        self.painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

    def close(self, path: Path) -> None:
        self.painter.end()
        path.parent.mkdir(parents=True, exist_ok=True)
        self.image.save(str(path))

    def font(self, size: int, weight: int = 400) -> QFont:
        face = QFont()
        face.setFamilies(["Segoe UI Variable Text", "Segoe UI", "Microsoft YaHei UI"])
        face.setPixelSize(size)
        face.setWeight(QFont.Weight.DemiBold if weight >= 600 else QFont.Weight.Normal)
        return face

    def mono(self, size: int) -> QFont:
        face = QFont()
        face.setFamilies(["Cascadia Mono", "Consolas"])
        face.setPixelSize(size)
        return face

    def fill(self, rect: QRect, color: str) -> None:
        self.painter.setPen(Qt.PenStyle.NoPen)
        self.painter.setBrush(qcolor(color))
        self.painter.drawRect(rect)

    def box(self, rect: QRect, fill: str, border: str, radius: int) -> None:
        self.painter.setRenderHint(QPainter.RenderHint.Antialiasing, radius > 0)
        self.painter.setPen(Qt.PenStyle.NoPen)
        self.painter.setBrush(qcolor(fill))
        if radius:
            self.painter.drawRoundedRect(rect, radius, radius)
        else:
            self.painter.drawRect(rect)
        pen = QPen(qcolor(border))
        pen.setWidth(1)
        self.painter.setPen(pen)
        self.painter.setBrush(Qt.BrushStyle.NoBrush)
        inner = rect.adjusted(0, 0, -1, -1)
        if radius:
            self.painter.drawRoundedRect(inner, radius, radius)
        else:
            self.painter.drawRect(inner)
        self.painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

    def line(self, x: int, y: int, width: int, color: str) -> None:
        pen = QPen(qcolor(color))
        pen.setWidth(1)
        self.painter.setPen(pen)
        self.painter.drawLine(x, y, x + width, y)

    def text(
        self,
        rect: QRect,
        value: str,
        color: str,
        size: int,
        weight: int = 400,
        align: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        *,
        elide: bool = False,
        mono: bool = False,
    ) -> None:
        face = self.mono(size) if mono else self.font(size, weight)
        self.painter.setFont(face)
        shown = value
        if elide:
            metrics = QFontMetrics(face)
            shown = metrics.elidedText(value, Qt.TextElideMode.ElideRight, max(0, rect.width()))
        self.painter.setPen(qcolor(color))
        self.painter.drawText(rect, int(align), shown)

    def width_of(self, value: str, size: int, weight: int = 400) -> int:
        return QFontMetrics(self.font(size, weight)).horizontalAdvance(value)

    def icon(self, x: int, y: int, name: str, size: int, color: str) -> None:
        markup = svg_markup(name).replace("currentColor", color)
        renderer = QSvgRenderer(QByteArray(markup.encode("utf-8")))
        renderer.render(self.painter, QRectF(x, y, size, size))

    def focus_ring(self, rect: QRect, *, surface: str = "") -> None:
        """在控件之下铺 2px 焦点色，并留出 2px 父级表面缝。

        直接描边会被抗锯齿吃进填充里，缝就看不见。先画大一圈的焦点色，
        再用父级表面盖住内圈，最后由控件盖住自己的矩形。
        """

        parent = surface or self.tokens.color_bg
        radius = self.tokens.radius
        self.painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.painter.setPen(Qt.PenStyle.NoPen)
        self.painter.setBrush(qcolor(self.tokens.color_focus))
        self.painter.drawRoundedRect(rect.adjusted(-4, -4, 4, 4), radius + 4, radius + 4)
        self.painter.setBrush(qcolor(parent))
        self.painter.drawRoundedRect(rect.adjusted(-2, -2, 2, 2), radius + 2, radius + 2)
        self.painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

    def button(
        self,
        x: int,
        y: int,
        label: str,
        kind: str = "secondary",
        *,
        focused: bool = False,
        enabled: bool = True,
        icon_name: str = "",
        state: str = "default",
        surface: str = "",
    ) -> QRect:
        tokens = self.tokens
        height = tokens.control_height
        pad = tokens.space_md
        icon_w = tokens.icon_size + tokens.space_sm if icon_name else 0
        width = self.width_of(label, tokens.font_size, 600) + pad * 2 + icon_w
        width = max(width, height * 2)
        rect = QRect(x, y, width, height)
        if not enabled:
            fill, border, fg = tokens.color_bg, tokens.color_border_subtle, tokens.color_disabled
        elif kind == "primary":
            fill = {"hover": tokens.color_primary_hover, "pressed": tokens.color_primary_pressed}.get(
                state, tokens.color_primary
            )
            border, fg = fill, tokens.color_on_primary
        elif kind == "danger":
            fill = {"hover": tokens.color_danger_hover, "pressed": tokens.color_danger_pressed}.get(
                state, tokens.color_danger
            )
            border, fg = fill, tokens.color_on_primary
        elif kind == "text":
            fill = tokens.color_hover if state in {"hover", "pressed"} else tokens.color_bg
            border, fg = fill, tokens.color_text
        else:
            fill = {"hover": tokens.color_hover, "pressed": tokens.color_pressed}.get(state, tokens.color_elevated)
            border, fg = tokens.color_border, tokens.color_text
        if focused and enabled:
            self.focus_ring(rect, surface=surface)
        self.box(rect, fill, border, tokens.button_radius)
        cursor = rect.left() + pad
        if icon_name:
            iy = rect.top() + (height - tokens.icon_size) // 2
            self.icon(cursor, iy, icon_name, tokens.icon_size, fg)
            cursor += tokens.icon_size + tokens.space_sm
        self.text(
            QRect(cursor, rect.top(), rect.right() - cursor - pad + 1, height),
            label,
            fg,
            tokens.font_size,
            600,
        )
        return rect

    def field(
        self,
        rect: QRect,
        value: str,
        *,
        error: bool = False,
        focused: bool = False,
        placeholder: bool = False,
        mono: bool = False,
        surface: str = "",
    ) -> None:
        tokens = self.tokens
        border = tokens.color_danger if error else tokens.color_control_border
        if focused:
            self.focus_ring(rect, surface=surface)
        self.box(rect, tokens.color_sunken, border, tokens.radius)
        color = tokens.color_muted if placeholder else tokens.color_text
        self.text(
            rect.adjusted(tokens.space_md, 0, -tokens.space_md, 0),
            value,
            color,
            tokens.font_size,
            mono=mono,
            elide=True,
        )

    def tag(self, x: int, y: int, label: str, tone: str) -> QRect:
        tokens = self.tokens
        color = {
            "success": tokens.color_success,
            "warning": tokens.color_warning,
            "danger": tokens.color_danger,
            "info": tokens.color_info,
        }[tone]
        fill = mix_hex(color, tokens.color_bg, 0.88)
        height = tokens.control_height_sm
        width = self.width_of(label, tokens.font_size_sm, 600) + tokens.space_md * 2
        rect = QRect(x, y, width, height)
        self.box(rect, fill, fill, tokens.radius)
        self.text(rect, label, color, tokens.font_size_sm, 600, Qt.AlignmentFlag.AlignCenter)
        return rect

    def icon_button(self, x: int, y: int, name: str, *, quiet: bool = True) -> QRect:
        tokens = self.tokens
        side = tokens.control_height_sm
        rect = QRect(x, y, side, side)
        if not quiet:
            self.box(rect, tokens.color_elevated, tokens.color_border, tokens.radius)
        iy = rect.top() + (side - tokens.icon_size) // 2
        ix = rect.left() + (side - tokens.icon_size) // 2
        self.icon(ix, iy, name, tokens.icon_size, tokens.color_muted)
        return rect

    def banner(self, rect: QRect, label: str, tone: str = "warning") -> None:
        tokens = self.tokens
        color = tokens.color_danger if tone == "danger" else tokens.color_warning
        fill = mix_hex(color, tokens.color_bg, 0.90)
        self.box(rect, fill, color, tokens.radius)
        self.icon(rect.left() + 10, rect.top() + 8, tone if tone == "warning" else "error", 16, color)
        self.text(
            rect.adjusted(32, 0, -36, 0),
            label,
            tokens.color_text,
            tokens.font_size,
        )
        self.icon_button(rect.right() - 30, rect.top() + 4, "x")


def paint_shell(canvas: Canvas, selected: str, caption: str) -> QRect:
    """画出标题栏和侧栏，返回内容列矩形。"""

    tokens = canvas.tokens
    width = canvas.image.width()
    height = canvas.image.height()
    bar = tokens.title_bar_height
    rail = width < 760
    side = tokens.sidebar_compact_width if rail else tokens.sidebar_width
    canvas.fill(QRect(0, 0, width, bar), tokens.color_surface)
    canvas.line(0, bar - 1, width, tokens.color_border_subtle)
    canvas.text(QRect(12, 0, width // 2, bar), caption, tokens.color_text, tokens.font_size, 600)
    for index, name in enumerate(("win-min", "win-max", "win-close")):
        canvas.icon(width - 28 - (2 - index) * 28, (bar - 14) // 2, name, 14, tokens.color_muted)
    canvas.fill(QRect(0, bar, side, height - bar), tokens.color_sidebar)
    y = bar + tokens.space_sm
    if rail:
        canvas.icon(side // 2 - 8, y, "command", 16, tokens.color_sidebar_text)
        y += 28
    else:
        canvas.text(
            QRect(tokens.space_md, y, side - tokens.space_md * 2, 24),
            "psi6",
            tokens.color_text,
            tokens.font_size,
            600,
        )
        y += 28
    for key, label, icon_name in DESTINATIONS:
        rect = QRect(6, y, side - 12, tokens.control_height)
        active = key == selected
        if active:
            canvas.fill(rect, tokens.color_selected)
            canvas.fill(
                QRect(rect.left(), rect.top() + 8, 2, rect.height() - 16),
                tokens.color_primary,
            )
        icon_color = tokens.color_primary if active else tokens.color_sidebar_text
        text_color = tokens.color_text if active else tokens.color_sidebar_text
        icon_x = rect.center().x() - tokens.icon_size // 2 if rail else rect.left() + 10
        canvas.icon(icon_x, rect.top() + (rect.height() - tokens.icon_size) // 2, icon_name, tokens.icon_size, icon_color)
        if not rail:
            canvas.text(
                QRect(rect.left() + 32, rect.top(), rect.width() - 40, rect.height()),
                label,
                text_color,
                tokens.font_size,
                600 if active else 400,
            )
        y += tokens.control_height + 2
    return QRect(side, bar, width - side, height - bar)


def _header(canvas: Canvas, rect: QRect, title: str, hint: str) -> int:
    tokens = canvas.tokens
    canvas.text(QRect(rect.left(), rect.top(), rect.width(), tokens.font_size_title + 4), title, tokens.color_text, tokens.font_size_title, 600)
    canvas.text(
        QRect(rect.left(), rect.top() + tokens.font_size_title + 4, rect.width(), tokens.font_size_sm + 6),
        hint,
        tokens.color_muted,
        tokens.font_size_sm,
    )
    return tokens.font_size_title + tokens.font_size_sm + tokens.space_md + 8


def _action_bar(canvas: Canvas, rect: QRect, status: str, buttons: list[tuple[str, str]], *, align_left: bool) -> None:
    tokens = canvas.tokens
    canvas.fill(rect, tokens.color_bg)
    canvas.line(rect.left(), rect.top(), rect.width(), tokens.color_border_subtle)
    gap = canvas.kit.control_gap
    if align_left:
        canvas.text(
            rect.adjusted(rect.width() // 2, 0, -tokens.space_lg, 0),
            status,
            tokens.color_muted,
            tokens.font_size_sm,
            align=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
    else:
        canvas.text(
            rect.adjusted(tokens.space_lg, 0, -rect.width() // 2, 0),
            status,
            tokens.color_muted,
            tokens.font_size_sm,
        )
    if align_left:
        x = rect.left() + tokens.space_lg
        y = rect.top() + tokens.space_sm
        for label, kind in buttons:
            drawn = canvas.button(x, y, label, kind)
            x = drawn.right() + 1 + gap
        return
    y = rect.top() + tokens.space_sm
    x = rect.right() - tokens.space_lg
    for label, kind in reversed(buttons):
        width = canvas.width_of(label, tokens.font_size, 600) + tokens.space_md * 2
        width = max(width, tokens.control_height * 2)
        x -= width
        canvas.button(x, y, label, kind)
        x -= gap


def _empty(canvas: Canvas, rect: QRect, title: str, hint: str) -> None:
    tokens = canvas.tokens
    size = tokens.icon_size * 2
    cx = rect.center().x()
    cy = rect.center().y() - 20
    canvas.icon(cx - size // 2, cy - size, "inbox", size, tokens.color_muted)
    canvas.text(QRect(rect.left(), cy + 8, rect.width(), 24), title, tokens.color_text, tokens.font_size, 600, Qt.AlignmentFlag.AlignHCenter)
    canvas.text(
        QRect(rect.left() + 24, cy + 32, rect.width() - 48, 40),
        hint,
        tokens.color_muted,
        tokens.font_size_sm,
        align=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
    )


def _overlay(canvas: Canvas, rect: QRect, caption: str) -> None:
    tokens = canvas.tokens
    canvas.fill(rect, tokens.color_overlay)
    canvas.text(rect, caption, tokens.color_text, tokens.font_size, 600, Qt.AlignmentFlag.AlignCenter)


def paint_settings(canvas: Canvas, content: QRect, mode: str) -> None:
    tokens = canvas.tokens
    pad = tokens.space_lg
    bar_h = tokens.control_height + tokens.space_sm * 2
    action = QRect(content.left(), content.bottom() - bar_h + 1, content.width(), bar_h)
    body = content.adjusted(pad, pad, -pad, -action.height() - pad)
    y = body.top() + _header(canvas, body, "设置", "工作区、外观和运行方式")
    column = QRect(body.left(), y, min(720, body.width()), body.bottom() - y)
    if mode == "empty":
        _empty(canvas, column, "没有可配置项", "这个工作区还没有暴露设置")
    else:
        _settings_form(canvas, column, stacked=body.width() < 560, error=mode == "error")
        if mode == "loading":
            _overlay(canvas, column, "正在读取设置")
    _action_bar(canvas, action, "尚未保存", [("取消", "secondary"), ("保存", "primary")], align_left=False)


def _settings_form(canvas: Canvas, column: QRect, *, stacked: bool, error: bool) -> None:
    tokens = canvas.tokens
    y = column.top()
    y = _section(canvas, column.left(), y, column.width(), "外观")
    y = _setting_choice(canvas, column, y, "主题", "浅色现代", stacked)
    y = _setting_choice(canvas, column, y, "密度", "自动", stacked)
    y += tokens.space_sm
    y = _section(canvas, column.left(), y, column.width(), "工作区")
    y = _setting_path(canvas, column, y, stacked, error)
    y += tokens.space_sm
    y = _section(canvas, column.left(), y, column.width(), "运行")
    _setting_switch(canvas, column, y, "完成后显示通知", stacked)


def _section(canvas: Canvas, x: int, y: int, width: int, title: str) -> int:
    tokens = canvas.tokens
    canvas.text(QRect(x, y, width, tokens.font_size + 8), title, tokens.color_text, tokens.font_size, 600)
    y += tokens.font_size + 10
    canvas.line(x, y, width, tokens.color_border_subtle)
    return y + tokens.space_md


def _setting_choice(canvas: Canvas, column: QRect, y: int, label: str, value: str, stacked: bool) -> int:
    tokens = canvas.tokens
    label_w = 168 if tokens.font_size <= 12 else 200
    if stacked:
        canvas.text(QRect(column.left(), y, column.width(), 20), label, tokens.color_text, tokens.font_size, 600)
        y += 22
        width = min(320, column.width())
        canvas.field(QRect(column.left(), y, width, tokens.control_height), value)
        return y + tokens.control_height + tokens.space_md
    canvas.text(QRect(column.left(), y, label_w, tokens.control_height), label, tokens.color_text, tokens.font_size, 600)
    canvas.field(QRect(column.left() + label_w, y, min(320, column.width() - label_w), tokens.control_height), value)
    return y + tokens.control_height + tokens.space_sm


def _setting_path(canvas: Canvas, column: QRect, y: int, stacked: bool, error: bool) -> int:
    tokens = canvas.tokens
    label_w = 168 if tokens.font_size <= 12 else 200
    label = "工作区"
    if stacked:
        canvas.text(QRect(column.left(), y, column.width(), 20), label, tokens.color_text, tokens.font_size, 600)
        y += 22
        x = column.left()
        avail = column.width()
    else:
        canvas.text(QRect(column.left(), y, label_w, tokens.control_height), label, tokens.color_text, tokens.font_size, 600)
        x = column.left() + label_w
        avail = column.width() - label_w
    button_w = canvas.width_of("浏览", tokens.font_size, 600) + tokens.space_md * 2
    button_w = max(button_w, tokens.control_height * 2)
    field_w = min(480, max(120, avail - button_w - canvas.kit.control_gap))
    canvas.field(
        QRect(x, y, field_w, tokens.control_height),
        "F:/work/psi6-demo" if not error else "F:/missing/demo",
        error=error,
        mono=True,
    )
    canvas.button(x + field_w + canvas.kit.control_gap, y, "浏览", "secondary")
    if error:
        canvas.text(
            QRect(x, y + tokens.control_height + 2, field_w, tokens.font_size_sm + 4),
            "目录不存在",
            tokens.color_danger,
            tokens.font_size_sm,
        )
        return y + tokens.control_height + tokens.font_size_sm + tokens.space_md
    return y + tokens.control_height + tokens.space_sm


def _setting_switch(canvas: Canvas, column: QRect, y: int, label: str, stacked: bool) -> None:
    tokens = canvas.tokens
    canvas.text(QRect(column.left(), y, column.width() - 60, tokens.control_height), label, tokens.color_text, tokens.font_size, 600)
    track = QRect(column.right() - 44, y + (tokens.control_height - tokens.switch_height) // 2, tokens.switch_width, tokens.switch_height)
    canvas.box(track, tokens.color_primary, tokens.color_primary, tokens.switch_height // 2)
    thumb = tokens.switch_height - 4
    canvas.box(
        QRect(track.right() - thumb - 2, track.top() + 2, thumb, thumb),
        tokens.color_on_primary,
        tokens.color_on_primary,
        thumb // 2,
    )


def paint_file_index(canvas: Canvas, content: QRect, mode: str) -> None:
    tokens = canvas.tokens
    pad = tokens.space_lg
    body = content.adjusted(pad, pad, -pad, -pad)
    y = body.top() + _header(canvas, body, "文件索引", "按后缀扫描工作区")
    gap = canvas.kit.control_gap
    start = canvas.button(body.left(), y, "开始", "primary", icon_name="play")
    cancel = canvas.button(start.right() + 1 + gap, y, "取消", "secondary")
    if body.width() >= 640:
        canvas.button(body.right() - _button_width(canvas, "刷新") + 1, y, "刷新", "secondary", icon_name="refresh")
    else:
        canvas.icon_button(cancel.right() + 1 + gap, y + 4, "more", quiet=False)
    y += tokens.control_height + tokens.space_md
    search_w = min(280, max(140, body.width() // 3))
    search = QRect(body.left(), y, search_w, tokens.control_height)
    canvas.field(search, "")
    canvas.icon(search.left() + 8, y + (tokens.control_height - tokens.icon_size) // 2, "search", tokens.icon_size, tokens.color_muted)
    canvas.text(search.adjusted(28, 0, -8, 0), "搜索名称", tokens.color_muted, tokens.font_size)
    canvas.field(QRect(body.left() + search_w + gap, y, min(120, body.width() // 5), tokens.control_height), ".py")
    canvas.text(
        QRect(body.right() - 180, y, 180, tokens.control_height),
        "12 个文件",
        tokens.color_muted,
        tokens.font_size_sm,
        align=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
    )
    y += tokens.control_height + tokens.space_sm
    if mode == "error":
        canvas.banner(QRect(body.left(), y, body.width(), tokens.control_height), "有 2 个路径无法读取", "danger")
        y += tokens.control_height + tokens.space_sm
    table = QRect(body.left(), y, body.width(), body.bottom() - y)
    show_path = body.width() >= 560
    _table(
        canvas,
        table,
        show_path,
        empty=mode == "empty",
        loading=mode == "loading",
    )


def _button_width(canvas: Canvas, label: str) -> int:
    tokens = canvas.tokens
    width = canvas.width_of(label, tokens.font_size, 600) + tokens.space_md * 2 + tokens.icon_size + tokens.space_sm
    return max(width, tokens.control_height * 2)


def _table(canvas: Canvas, rect: QRect, show_path: bool, *, empty: bool, loading: bool) -> None:
    tokens = canvas.tokens
    canvas.box(rect, tokens.color_surface, tokens.color_border, tokens.radius)
    header = QRect(rect.left(), rect.top(), rect.width(), tokens.row_height)
    canvas.text(header.adjusted(12, 0, -12, 0), "名称", tokens.color_muted, tokens.font_size_sm, 600)
    if show_path:
        canvas.text(QRect(rect.left() + 180, rect.top(), rect.width() - 280, tokens.row_height), "路径", tokens.color_muted, tokens.font_size_sm, 600)
    canvas.text(QRect(rect.right() - 88, rect.top(), 72, tokens.row_height), "状态", tokens.color_muted, tokens.font_size_sm, 600)
    canvas.line(rect.left(), rect.top() + tokens.row_height, rect.width(), tokens.color_border_subtle)
    rows = (
        ("app.py", "src/app.py", "success", "就绪"),
        ("scan.py", "src/jobs/scan.py", "warning", "等待"),
        ("missing.py", "src/missing.py", "danger", "失败"),
    )
    if empty:
        _empty(canvas, rect.adjusted(8, tokens.row_height, -8, -8), "没有文件", "选择目录后开始索引")
        return
    y = rect.top() + tokens.row_height
    for index, (name, path, tone, status) in enumerate(rows):
        row = QRect(rect.left() + 1, y, rect.width() - 2, tokens.row_height)
        if index == 0:
            canvas.fill(row, tokens.color_selected)
        canvas.text(row.adjusted(12, 0, -12, 0), name, tokens.color_text, tokens.font_size)
        if show_path:
            canvas.text(
                QRect(rect.left() + 180, y, rect.width() - 280, tokens.row_height),
                path,
                tokens.color_muted,
                tokens.font_size_sm,
                mono=True,
                elide=True,
            )
        canvas.tag(rect.right() - 78, y + (tokens.row_height - tokens.control_height_sm) // 2, status, tone)
        y += tokens.row_height
        if y + tokens.row_height > rect.bottom():
            break
    if loading:
        _overlay(canvas, rect.adjusted(1, tokens.row_height, -1, -1), "正在索引")


def paint_task(canvas: Canvas, content: QRect, mode: str) -> None:
    tokens = canvas.tokens
    pad = tokens.space_lg
    bar_h = tokens.control_height + tokens.space_sm * 2
    action = QRect(content.left(), content.bottom() - bar_h + 1, content.width(), bar_h)
    body = content.adjusted(pad, pad, -pad, -bar_h - pad)
    y = body.top() + _header(canvas, body, "索引任务", "扫描工作区并写入日志")
    work = QRect(body.left(), y, body.width(), body.bottom() - y)
    side_by_side = work.width() >= 720
    if side_by_side:
        form = QRect(work.left(), work.top(), min(480, work.width() // 2), work.height())
        log = QRect(form.right() + 8, work.top(), work.right() - form.right() - 8, work.height())
    else:
        form_h = min(int(work.height() * 0.42), tokens.control_height * 4 + 24)
        form = QRect(work.left(), work.top(), work.width(), form_h)
        log = QRect(work.left(), form.bottom() + 8, work.width(), work.bottom() - form.bottom() - 8)
    _task_form(canvas, form)
    _log(canvas, log, mode)
    running = mode == "loading"
    _action_bar(
        canvas,
        action,
        "正在扫描 40%" if running else "空闲",
        [("取消", "secondary"), ("开始", "primary")],
        align_left=True,
    )


def _task_form(canvas: Canvas, rect: QRect) -> None:
    tokens = canvas.tokens
    canvas.text(QRect(rect.left(), rect.top(), rect.width(), 20), "参数", tokens.color_text, tokens.font_size, 600)
    y = rect.top() + 24
    canvas.text(QRect(rect.left(), y, 80, tokens.control_height), "目录", tokens.color_text, tokens.font_size, 600)
    field_w = min(480, rect.width() - 88)
    canvas.field(QRect(rect.left() + 88, y, max(80, field_w - 70), tokens.control_height), "F:/work/psi6-demo", mono=True)
    y += tokens.control_height + tokens.space_sm
    canvas.text(QRect(rect.left(), y, 80, tokens.control_height), "后缀", tokens.color_text, tokens.font_size, 600)
    canvas.field(QRect(rect.left() + 88, y, min(160, rect.width() - 88), tokens.control_height), ".py")


def _log(canvas: Canvas, rect: QRect, mode: str) -> None:
    tokens = canvas.tokens
    canvas.box(rect, tokens.color_sunken, tokens.color_border, tokens.radius)
    canvas.text(
        QRect(rect.left() + 12, rect.top() + 8, rect.width() - 24, 18),
        "运行日志",
        tokens.color_muted,
        tokens.font_size_sm,
        600,
    )
    if mode == "empty" or rect.height() < 48:
        _empty(canvas, rect.adjusted(0, 20, 0, 0), "还没有运行", "设置目录后点击开始")
        return
    lines = (
        (tokens.color_text, "准备扫描"),
        (tokens.color_info, "读取 12 个文件"),
        (tokens.color_warning, "scan.py 仍在写入"),
        (tokens.color_danger, "missing.py 无法打开"),
    )
    if mode != "error":
        lines = lines[:3]
    y = rect.top() + 28
    for color, line in lines:
        canvas.text(QRect(rect.left() + 12, y, rect.width() - 24, tokens.row_height), line, color, tokens.font_size, mono=True)
        y += tokens.row_height
        if y > rect.bottom() - 8:
            break


def paint_workbench(canvas: Canvas, content: QRect, mode: str) -> None:
    tokens = canvas.tokens
    pad = tokens.space_lg
    body = content.adjusted(pad, pad, -pad, -pad)
    canvas.text(QRect(body.left(), body.top(), body.width() - 80, 22), "工作台  /  文档", tokens.color_text, tokens.font_size, 600)
    if body.width() < 700:
        canvas.icon_button(body.right() - 28, body.top(), "sidebar", quiet=False)
    elif body.width() < 792:
        canvas.icon_button(body.right() - 28, body.top(), "sliders", quiet=False)
    panes = QRect(body.left(), body.top() + 32, body.width(), body.height() - 32)
    gap = 6
    show_right = panes.width() >= 200 + 360 + 220 + gap * 2
    show_left = panes.width() >= 200 + 360 + gap
    if show_left and show_right:
        left = QRect(panes.left(), panes.top(), 200, panes.height())
        right = QRect(panes.right() - 219, panes.top(), 220, panes.height())
        center = QRect(left.right() + gap, panes.top(), right.left() - left.right() - gap * 2, panes.height())
    elif show_left:
        left = QRect(panes.left(), panes.top(), 200, panes.height())
        right = QRect()
        center = QRect(left.right() + gap, panes.top(), panes.right() - left.right() - gap, panes.height())
    else:
        left = QRect()
        right = QRect()
        center = panes
    if left.isValid():
        _pane_list(canvas, left)
    _pane_center(canvas, center, mode)
    if right.isValid():
        _pane_props(canvas, right)


def _pane_list(canvas: Canvas, rect: QRect) -> None:
    tokens = canvas.tokens
    canvas.box(rect, tokens.color_surface, tokens.color_border, tokens.radius)
    canvas.text(QRect(rect.left() + 12, rect.top() + 8, rect.width() - 24, 22), "文档列表", tokens.color_text, tokens.font_size, 600)
    y = rect.top() + 36
    for index, name in enumerate(("说明.md", "布局.md", "决策.md")):
        row = QRect(rect.left() + 8, y, rect.width() - 16, tokens.row_height)
        if index == 0:
            canvas.fill(row, tokens.color_selected)
        canvas.icon(row.left() + 6, row.top() + 8, "file", tokens.icon_size, tokens.color_primary if index == 0 else tokens.color_muted)
        canvas.text(row.adjusted(28, 0, -8, 0), name, tokens.color_text, tokens.font_size)
        y += tokens.row_height


def _pane_center(canvas: Canvas, rect: QRect, mode: str) -> None:
    tokens = canvas.tokens
    canvas.box(rect, tokens.color_surface, tokens.color_border, tokens.radius)
    tabs = ("文档", "预览")
    x = rect.left() + 12
    for index, name in enumerate(tabs):
        width = canvas.width_of(name, tokens.font_size, 600) + 16
        canvas.text(QRect(x, rect.top() + 8, width, 24), name, tokens.color_text if index == 0 else tokens.color_muted, tokens.font_size, 600 if index == 0 else 400)
        if index == 0:
            canvas.fill(QRect(x, rect.top() + 32, width, 2), tokens.color_primary)
        x += width + 12
    canvas.line(rect.left(), rect.top() + 36, rect.width(), tokens.color_border_subtle)
    inner = rect.adjusted(12, 48, -12, -12)
    if mode == "empty":
        _empty(canvas, inner, "没有打开的文档", "从左侧选择一篇文档")
        return
    if mode == "error":
        canvas.banner(QRect(inner.left(), inner.top(), inner.width(), tokens.control_height), "这篇文档无法解析", "danger")
        inner = inner.adjusted(0, tokens.control_height + 8, 0, 0)
    lines = ("工作台把列表、正文和属性放在同一层表面上。", "窄于最小栏宽时，先收起属性，再收起列表。")
    y = inner.top()
    for line in lines:
        canvas.text(QRect(inner.left(), y, inner.width(), 22), line, tokens.color_text, tokens.font_size)
        y += 24
    if mode == "loading":
        _overlay(canvas, rect.adjusted(1, 37, -1, -1), "正在打开")


def _pane_props(canvas: Canvas, rect: QRect) -> None:
    tokens = canvas.tokens
    canvas.box(rect, tokens.color_surface, tokens.color_border, tokens.radius)
    canvas.text(QRect(rect.left() + 12, rect.top() + 8, rect.width() - 24, 22), "属性", tokens.color_text, tokens.font_size, 600)
    y = rect.top() + 40
    for name, value in (("类型", "Markdown"), ("修改", "今天"), ("字数", "1 280")):
        canvas.text(QRect(rect.left() + 12, y, 48, 22), name, tokens.color_muted, tokens.font_size_sm)
        canvas.text(QRect(rect.left() + 64, y, rect.width() - 76, 22), value, tokens.color_text, tokens.font_size)
        y += 26


def paint_components(canvas: Canvas, content: QRect, mode: str) -> None:
    tokens = canvas.tokens
    pad = tokens.space_lg
    body = content.adjusted(pad, pad, -pad, -pad)
    y = body.top() + _header(canvas, body, "组件", "状态按族排列，列宽不拉伸")
    area = QRect(body.left(), y, body.width(), body.bottom() - y)
    if mode == "empty":
        _empty(canvas, area, "暂无数据", "空状态属于这块区域，而不是整页")
        return
    if mode == "loading":
        _component_matrix(canvas, area, error=False)
        _overlay(canvas, area, "正在刷新目录")
        return
    _component_matrix(canvas, area, error=mode == "error" or True)


def _component_matrix(canvas: Canvas, area: QRect, *, error: bool) -> None:
    tokens = canvas.tokens
    gap = canvas.kit.control_gap
    columns = 2 if area.width() >= 700 else 1
    col_w = (area.width() - gap * (columns - 1)) // columns
    blocks = (
        _block_buttons,
        _block_inputs,
        _block_choice,
        _block_data,
    )
    for index, block in enumerate(blocks):
        col = index % columns
        row = index // columns
        pitch = 280
        origin = QRect(area.left() + col * (col_w + gap), area.top() + row * pitch, col_w, pitch - 8)
        if origin.bottom() > area.bottom():
            canvas.fill(QRect(area.right() - 8, area.top(), 6, area.height()), tokens.color_sunken)
            canvas.fill(QRect(area.right() - 8, area.top() + 12, 6, 48), tokens.color_border)
            break
        block(canvas, origin, error=error)


def _block_buttons(canvas: Canvas, rect: QRect, *, error: bool) -> None:
    del error
    tokens = canvas.tokens
    canvas.text(QRect(rect.left(), rect.top(), rect.width(), 20), "按钮", tokens.color_text, tokens.font_size, 600)
    y = rect.top() + 28
    labels = (
        ("默认", False, True, "default"),
        ("悬停", False, True, "hover"),
        ("按下", False, True, "pressed"),
        ("焦点", True, True, "default"),
        ("禁用", False, False, "default"),
    )
    for caption, focused, enabled, state in labels:
        canvas.text(QRect(rect.left(), y, 36, tokens.control_height), caption, tokens.color_muted, tokens.font_size_sm)
        primary = canvas.button(
            rect.left() + 40, y, "开始", "primary", focused=focused, enabled=enabled, state=state
        )
        canvas.button(
            primary.right() + 1 + canvas.kit.control_gap,
            y,
            "取消",
            "secondary",
            enabled=enabled,
            state=state,
        )
        y += tokens.control_height + canvas.kit.control_gap


def _block_inputs(canvas: Canvas, rect: QRect, *, error: bool) -> None:
    tokens = canvas.tokens
    canvas.text(QRect(rect.left(), rect.top(), rect.width(), 20), "输入", tokens.color_text, tokens.font_size, 600)
    y = rect.top() + 28
    width = min(220, rect.width() - 48)
    canvas.text(QRect(rect.left(), y, 36, tokens.control_height), "焦点", tokens.color_muted, tokens.font_size_sm)
    canvas.field(QRect(rect.left() + 40, y, width, tokens.control_height), "名称", focused=True)
    y += tokens.control_height + canvas.kit.control_gap
    canvas.text(QRect(rect.left(), y, 36, tokens.control_height), "错误", tokens.color_muted, tokens.font_size_sm)
    canvas.field(QRect(rect.left() + 40, y, width, tokens.control_height), "0", error=error)
    canvas.text(
        QRect(rect.left() + 40, y + tokens.control_height + 1, width, tokens.font_size_sm + 2),
        "数值过小",
        tokens.color_danger,
        tokens.font_size_sm,
    )


def _block_choice(canvas: Canvas, rect: QRect, *, error: bool) -> None:
    del error
    tokens = canvas.tokens
    canvas.text(QRect(rect.left(), rect.top(), rect.width(), 20), "选择与页签", tokens.color_text, tokens.font_size, 600)
    y = rect.top() + 36
    box = QRect(rect.left(), y, 16, 16)
    canvas.box(box, tokens.color_primary, tokens.color_primary, max(2, tokens.radius - 2))
    canvas.icon(box.left(), box.top(), "check", 16, tokens.color_on_primary)
    canvas.text(QRect(rect.left() + 24, y - 6, 80, 28), "递归", tokens.color_text, tokens.font_size)
    slot = QRect(rect.left() + 120, y - 2, tokens.switch_width, tokens.switch_height)
    canvas.box(slot, tokens.color_border, tokens.color_border, tokens.switch_height // 2)
    thumb = tokens.switch_height - 4
    canvas.box(QRect(slot.left() + 2, slot.top() + 2, thumb, thumb), tokens.color_elevated, tokens.color_elevated, thumb // 2)
    y += 40
    x = rect.left()
    for index, name in enumerate(("文档", "预览")):
        width = canvas.width_of(name, tokens.font_size) + 12
        canvas.text(QRect(x, y, width, 22), name, tokens.color_text if index == 0 else tokens.color_muted, tokens.font_size, 600 if index == 0 else 400)
        if index == 0:
            canvas.fill(QRect(x, y + 22, width, 2), tokens.color_primary)
        x += width + 16


def _block_data(canvas: Canvas, rect: QRect, *, error: bool) -> None:
    tokens = canvas.tokens
    canvas.text(QRect(rect.left(), rect.top(), rect.width(), 20), "表格与横幅", tokens.color_text, tokens.font_size, 600)
    y = rect.top() + 28
    row = QRect(rect.left(), y, min(rect.width(), 280), tokens.row_height)
    canvas.box(row, tokens.color_surface, tokens.color_border, tokens.radius)
    canvas.fill(row.adjusted(1, 1, -1, -1), tokens.color_selected)
    canvas.text(row.adjusted(8, 0, -70, 0), "app.py", tokens.color_text, tokens.font_size)
    canvas.tag(row.right() - 64, y + 2, "失败" if error else "就绪", "danger" if error else "success")
    y += tokens.row_height + canvas.kit.control_gap
    banner = QRect(rect.left(), y, min(rect.width(), 300), tokens.control_height)
    canvas.banner(banner, "导出前先检查路径", "warning")


def paint_chat(canvas: Canvas, content: QRect, mode: str) -> None:
    tokens = canvas.tokens
    pad = tokens.space_lg
    body = content.adjusted(pad, pad, -pad, -pad)
    y = body.top() + _header(canvas, body, "对话", "记录区占满输入条以上的空间")
    composer_h = tokens.control_height + (tokens.font_size_sm + 8 if mode == "error" else 0)
    well = QRect(body.left(), y, body.width(), body.bottom() - y - composer_h - tokens.space_sm)
    canvas.box(well, tokens.color_sunken, tokens.color_border, tokens.radius)
    if mode == "empty":
        _empty(canvas, well, "从下面开始", "输入问题，发送后出现在右侧")
    else:
        _bubbles(canvas, well, loading=mode == "loading")
    input_y = well.bottom() + tokens.space_sm
    if mode == "error":
        canvas.text(QRect(body.left(), input_y, body.width(), tokens.font_size_sm + 4), "发送失败，请再试一次", tokens.color_danger, tokens.font_size_sm)
        input_y += tokens.font_size_sm + 4
    field_w = body.width() - _button_width(canvas, "发送") - canvas.kit.control_gap
    if field_w < 160:
        canvas.field(QRect(body.left(), input_y, body.width(), tokens.control_height), "写一条消息", placeholder=True)
        canvas.button(body.right() - _button_width(canvas, "发送") + 1, input_y + tokens.control_height + 4, "发送", "primary", enabled=mode != "loading")
        return
    canvas.field(QRect(body.left(), input_y, field_w, tokens.control_height), "写一条消息", placeholder=True)
    canvas.button(body.left() + field_w + canvas.kit.control_gap, input_y, "发送", "primary", enabled=mode != "loading", icon_name="send")


def _bubbles(canvas: Canvas, well: QRect, *, loading: bool) -> None:
    tokens = canvas.tokens
    max_w = min(640, well.width() - 48)
    y = well.top() + 16
    reply = QRect(well.left() + 16, y, max_w, 56)
    canvas.box(reply, tokens.color_surface, tokens.color_border, tokens.radius)
    canvas.text(reply.adjusted(12, 8, -12, -8), "索引已经完成，失败的两项在表里。", tokens.color_text, tokens.font_size)
    y = reply.bottom() + 12
    user_w = min(max_w, 280)
    user = QRect(well.right() - user_w - 16, y, user_w, 40)
    canvas.box(user, tokens.color_user_bubble, tokens.color_user_bubble, tokens.radius)
    canvas.text(user.adjusted(12, 0, -12, 0), "把失败的路径列出来", tokens.color_user_on_bubble, tokens.font_size)
    if loading:
        canvas.text(QRect(well.left() + 16, user.bottom() + 12, 160, 24), "正在回复", tokens.color_muted, tokens.font_size_sm)


def paint_dialog(canvas: Canvas) -> None:
    tokens = canvas.tokens
    canvas.fill(QRect(0, 0, canvas.image.width(), canvas.image.height()), tokens.color_overlay)
    width = min(440, canvas.image.width() - 48)
    height = 220
    rect = QRect((canvas.image.width() - width) // 2, (canvas.image.height() - height) // 2, width, height)
    canvas.box(rect, tokens.color_elevated, tokens.color_border, tokens.radius)
    inner = rect.adjusted(tokens.space_lg, tokens.space_lg, -tokens.space_lg, -tokens.space_lg)
    canvas.text(QRect(inner.left(), inner.top(), inner.width(), 24), "保存设置", tokens.color_text, tokens.font_size_title, 600)
    canvas.text(QRect(inner.left(), inner.top() + 32, inner.width(), 20), "工作区", tokens.color_text, tokens.font_size, 600)
    canvas.field(QRect(inner.left(), inner.top() + 54, inner.width(), tokens.control_height), "F:/missing/demo", error=True, mono=True)
    canvas.text(QRect(inner.left(), inner.top() + 92, inner.width(), 18), "目录不存在", tokens.color_danger, tokens.font_size_sm)
    y = inner.bottom() - tokens.control_height
    save_w = max(canvas.width_of("保存", tokens.font_size, 600) + tokens.space_md * 2, tokens.control_height * 2)
    canvas.button(
        inner.right() - save_w + 1,
        y,
        "保存",
        "primary",
        focused=True,
        surface=tokens.color_elevated,
    )
    cancel_w = max(canvas.width_of("取消", tokens.font_size, 600) + tokens.space_md * 2, tokens.control_height * 2)
    canvas.button(inner.right() - save_w - canvas.kit.control_gap - cancel_w, y, "取消", "secondary")


PAINTERS = {
    "settings": paint_settings,
    "file-index": paint_file_index,
    "task": paint_task,
    "workbench": paint_workbench,
    "components": paint_components,
    "chat": paint_chat,
}
CAPTIONS = {
    "settings": "设置",
    "file-index": "文件索引",
    "task": "索引任务",
    "workbench": "工作台",
    "components": "组件",
    "chat": "对话",
}


def render_page(kit: Kit, page: str, width: int, height: int, mode: str, path: Path) -> None:
    canvas = Canvas(width, height, kit)
    content = paint_shell(canvas, page, CAPTIONS[page])
    PAINTERS[page](canvas, content, mode)
    canvas.close(path)


def main() -> None:
    """生成六页、四种组合、三档宽度，以及状态和对话框。"""

    QGuiApplication([])
    shots: list[dict[str, str | int]] = []
    kits = {name: Kit.load(name, base, style) for name, base, style in THEMES}
    for page in PAGES:
        for theme, _base, _style in THEMES:
            for band, width, height in SIZES:
                path = ROOT / page / theme / f"{band}.png"
                render_page(kits[theme], page, width, height, "ready", path)
                shots.append({"page": page, "theme": theme, "band": band, "mode": "ready", "path": str(path.relative_to(ROOT))})
        for mode in ("empty", "loading", "error"):
            path = ROOT / "states" / f"{page}-{mode}.png"
            render_page(kits["light-modern"], page, 960, 680, mode, path)
            shots.append({"page": page, "theme": "light-modern", "band": "medium", "mode": mode, "path": str(path.relative_to(ROOT))})
    for theme in ("light-modern", "dark-modern"):
        canvas = Canvas(960, 680, kits[theme])
        content = paint_shell(canvas, "settings", "设置")
        paint_settings(canvas, content, "ready")
        paint_dialog(canvas)
        path = ROOT / "dialogs" / f"confirm-{theme}.png"
        canvas.close(path)
        shots.append({"page": "dialog", "theme": theme, "band": "medium", "mode": "error", "path": str(path.relative_to(ROOT))})
    (ROOT / "manifest.json").write_text(json.dumps({"shots": shots}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(shots)} shots to {ROOT}")


if __name__ == "__main__":
    main()
