"""未捕获异常必须回到界面线程再碰控件。"""

from __future__ import annotations

import sys
import threading

from PySide6.QtWidgets import QApplication


def test_worker_exception_is_reported_on_the_ui_thread(qtbot) -> None:
    import psi6.runtime.errors as errors

    seen: dict[str, object] = {}

    class FakeBox:
        class Icon:
            Critical = 0

        def __init__(self, parent: object = None) -> None:
            del parent
            seen["thread"] = threading.current_thread()

        def setIcon(self, *_args: object) -> None:
            return None

        def setWindowTitle(self, *_args: object) -> None:
            return None

        def setText(self, text: str) -> None:
            seen["text"] = text

        def setDetailedText(self, *_args: object) -> None:
            return None

        def exec(self) -> None:
            seen["shown"] = True

    previous = (sys.excepthook, threading.excepthook, sys.unraisablehook)
    original_box = errors.QMessageBox
    errors.QMessageBox = FakeBox  # type: ignore[misc]
    try:
        app = QApplication.instance()
        assert isinstance(app, QApplication)
        errors.install_exception_hooks(app)

        def boom() -> None:
            raise RuntimeError("worker-boom-psi6")

        threading.Thread(target=boom).start()
        qtbot.waitUntil(lambda: seen.get("shown") is True, timeout=3000)
        assert seen["thread"] is threading.current_thread()
        assert "worker-boom-psi6" in str(seen["text"])
        seen.clear()

        def report_unraisable() -> None:
            sys.unraisablehook(
                type("Unraisable", (), {"exc_value": RuntimeError("unraisable-boom-psi6")})()
            )

        threading.Thread(target=report_unraisable).start()
        qtbot.waitUntil(lambda: seen.get("shown") is True, timeout=3000)
        assert seen["thread"] is threading.current_thread()
        assert "unraisable-boom-psi6" in str(seen["text"])
    finally:
        errors.QMessageBox = original_box
        errors.uninstall_exception_hooks()
    assert (sys.excepthook, threading.excepthook, sys.unraisablehook) == previous


def test_uninstall_restores_original_hooks(qtbot) -> None:
    del qtbot
    import psi6.runtime.errors as errors

    previous = (sys.excepthook, threading.excepthook, sys.unraisablehook)
    app = QApplication.instance()
    assert isinstance(app, QApplication)
    errors.install_exception_hooks(app)
    assert sys.excepthook is errors._hook
    errors.uninstall_exception_hooks()
    assert (sys.excepthook, threading.excepthook, sys.unraisablehook) == previous
    assert errors._bridge is None


def test_uninstall_releases_only_its_owner(qtbot) -> None:
    del qtbot
    import psi6.runtime.errors as errors

    previous = (sys.excepthook, threading.excepthook, sys.unraisablehook)
    app = QApplication.instance()
    assert isinstance(app, QApplication)
    first, second = object(), object()
    try:
        errors.install_exception_hooks(app, owner=first)
        errors.install_exception_hooks(app, owner=second)
        errors.uninstall_exception_hooks(first)
        assert sys.excepthook is errors._hook
        assert errors._bridge is not None
        errors.uninstall_exception_hooks(second)
        assert (sys.excepthook, threading.excepthook, sys.unraisablehook) == previous
        assert errors._bridge is None
        assert errors._bindings == {}
    finally:
        errors.uninstall_exception_hooks()
