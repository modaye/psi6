"""离屏截一张带 Toast 的窗口，核对它落在下角且四种语气可分辨。"""

from __future__ import annotations

import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QEventLoop
from PySide6.QtWidgets import QVBoxLayout, QWidget

from psi6 import App
from psi6.runtime.qt_env import install_qt_message_filter, prepare_qt_environment
from psi6.theme.runtime import token_ms
from psi6.ui.buttons import ghost_button, primary_button
from psi6.ui.tag import Tag
from psi6.ui.toast import ToastHost


def pump(ms: int) -> None:
    end = time.time() + ms / 1000.0
    while time.time() < end:
        QCoreApplication.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 20)
        time.sleep(0.01)


def main() -> None:
    prepare_qt_environment()
    install_qt_message_filter()
    # App 必须在整个截图期间活着：它持有 QApplication、已应用的 token 和样式表。
    app = App("psi6-toast-shot", theme="light")
    assert app.tokens.color_primary
    window = QWidget()
    window.resize(760, 460)
    column = QVBoxLayout(window)
    column.addWidget(primary_button("主要操作"))
    column.addWidget(ghost_button("次要操作"))
    row = QWidget()
    for text, tone in (
        ("成功", "success"),
        ("警告", "warning"),
        ("失败", "error"),
        ("信息", "info"),
    ):
        tag = Tag(text, tone=tone)
        tag.setParent(row)
        tag.move(10 + 90 * ["success", "warning", "error", "info"].index(tone), 10)
    column.addWidget(row)
    column.addStretch()
    window.show()
    pump(200)

    host = ToastHost(window)
    for text, tone in (
        ("保存成功，已同步。", "success"),
        ("磁盘空间不足，请清理。", "warning"),
        ("网络请求失败，请重试。", "error"),
    ):
        host.push(text, tone=tone, timeout_ms=60000)
        pump(60)
    pump(int(token_ms("normal")) + 120)

    print("toast host geometry:", host.geometry(), "window:", window.size())
    print("motion fast/normal:", token_ms("fast"), token_ms("normal"))
    window.grab().save("artifacts/after-atelier/toast_bottom_right.png", "PNG")
    window.close()


if __name__ == "__main__":
    main()
