"""主按钮、危险、幽灵描边、文字链。业务不要再写 objectName。"""

from __future__ import annotations

from PySide6.QtCore import Property, QEvent, QObject, QRectF, Qt
from PySide6.QtGui import QKeyEvent, QPaintEvent, QPen
from PySide6.QtWidgets import QPushButton, QWidget

from psi6.theme.apply import apply_psi6_button_style
from psi6.theme.paint import as_color, create_painter
from psi6.theme.runtime import token_color, token_ms
from psi6.ui import motion


def primary_button(text: str, parent: QWidget | None = None) -> QPushButton:
    """主题中的主按钮。"""

    button = QPushButton(text, parent)
    button.setObjectName("psi6Primary")
    apply_psi6_button_style(button)
    return button


def danger_button(text: str, parent: QWidget | None = None) -> QPushButton:
    """主题中的危险/取消按钮。"""

    button = QPushButton(text, parent)
    button.setObjectName("psi6Danger")
    apply_psi6_button_style(button)
    return button


def ghost_button(text: str, parent: QWidget | None = None) -> QPushButton:
    """描边浅底：返回、停止、选择图标、查看详情。"""

    button = QPushButton(text, parent)
    button.setObjectName("psi6Ghost")
    apply_psi6_button_style(button)
    return button


def text_button(text: str, parent: QWidget | None = None) -> QPushButton:
    """无框文字链：粘贴代码、打开上次、打开位置。"""

    button = QPushButton(text, parent)
    button.setObjectName("psi6Link")
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setFlat(True)
    apply_psi6_button_style(button)
    return button


link_button = text_button

# 挂在按钮实例上，避免再包一层子类，工厂仍返回 QPushButton。
_MARK = "_psi6_load_mark"


class _LoadMark(QWidget):
    """按钮左侧的加载圆弧。

    文字和变体颜色保持原样。点击、双击、空格和回车在加载期间被丢掉。
    圆弧是 Qt 属性 ``spin``，由 ``motion`` 按线性循环转动；减少动效时停在起点。
    """

    def __init__(self, button: QPushButton) -> None:
        super().__init__(button)
        self._button = button
        self._angle = 0.0
        self._on = False
        self.setFixedSize(14, 14)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.hide()
        button.installEventFilter(self)

    def _get_spin(self) -> float:
        return self._angle

    def _set_spin(self, value: float) -> None:
        self._angle = float(value) % 360.0
        self.update()

    spin = Property(float, _get_spin, _set_spin)

    def active(self) -> bool:
        """当前是否正在加载。"""

        return self._on

    def start(self) -> None:
        """开始转圈并挡住激活。重复调用不会重启动画。"""

        if self._on:
            return
        self._on = True
        self._button.setProperty("psi6Loading", True)
        self._polish()
        self._place()
        self.show()
        self.raise_()
        motion.animate(
            self,
            "spin",
            0,
            360,
            duration=_spin_ms(),
            curve="linear",
            loop=-1,
        )

    def stop(self) -> None:
        """停掉圆弧，恢复点击。"""

        self._on = False
        motion.stop(self, "spin")
        self.hide()
        self._button.setProperty("psi6Loading", False)
        self._polish()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is not self._button:
            return False
        kind = event.type()
        if kind in (QEvent.Type.Resize, QEvent.Type.Show):
            self._place()
        if not self._on:
            return False
        if kind in (
            QEvent.Type.MouseButtonPress,
            QEvent.Type.MouseButtonRelease,
            QEvent.Type.MouseButtonDblClick,
        ):
            return True
        return bool(
            kind == QEvent.Type.KeyPress
            and isinstance(event, QKeyEvent)
            and event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter)
        )

    def paintEvent(self, _event: QPaintEvent) -> None:
        name = self._button.objectName()
        ink = (
            token_color("color_on_primary")
            if name in {"psi6Primary", "psi6Danger"}
            else token_color("color_text")
        )
        with create_painter(self, clear_pen=False) as painter:
            pen = QPen(as_color(ink))
            pen.setWidthF(2.0)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            rect = QRectF(self.rect()).adjusted(2, 2, -2, -2)
            painter.drawArc(rect, int(-self._angle * 16), 110 * 16)

    def _place(self) -> None:
        button = self._button
        self.move(10, max(0, (button.height() - self.height()) // 2))

    def _polish(self) -> None:
        style = self._button.style()
        style.unpolish(self._button)
        style.polish(self._button)
        self._button.update()


def _spin_ms() -> int:
    """一圈的时长。减少动效时为 0，圆弧停住。"""

    base = token_ms("normal")
    if base <= 0:
        return 0
    return base * 4


def set_loading(button: QPushButton, loading: bool) -> None:
    """让按钮进入或离开加载态。

    左侧出现圆弧，文字保留，变体颜色不变，点击不再触发。
    外框尺寸不因加载改变：多出来的左侧留白来自预留的内边距。
    """

    mark = getattr(button, _MARK, None)
    if mark is None:
        mark = _LoadMark(button)
        setattr(button, _MARK, mark)
    if loading:
        mark.start()
    else:
        mark.stop()


def is_loading(button: QPushButton) -> bool:
    """按钮是否处于加载态。"""

    mark = getattr(button, _MARK, None)
    return bool(mark is not None and mark.active())
