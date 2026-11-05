"""规范检查器：绕开框架的写法要能被发现，干净的页面不能误报。"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from psi6.spec import check_paths, check_source, format_findings

_BAD = """\
from PySide6.QtCore import QThread
from PySide6.QtWidgets import QApplication, QFileDialog
from psi6.ui._path_picker import PathPicker

class Worker(QThread):
    pass

app = QApplication([])
app.processEvents()
worker = Worker()
worker.terminate()
QFileDialog.getOpenFileName(None, "打开")
widget.setStyleSheet("color: red")
"""

_CLEAN = """\
from psi6 import App
from psi6.ui.file_input import FileInput


def build(app: App) -> FileInput:
    field = FileInput()
    field.set_path("data.txt")
    return field
"""


def test_each_prohibition_is_reported() -> None:
    findings = check_source(_BAD, filename="bad.py")
    assert [item.rule for item in findings] == [
        "PSI005",
        "PSI002",
        "PSI001",
        "PSI006",
        "PSI002",
        "PSI003",
        "PSI004",
    ]
    assert {item.line for item in findings} == {3, 5, 8, 9, 11, 12, 13}
    assert all(item.path == "bad.py" for item in findings)
    assert all(item.hint for item in findings)


def test_public_pydantic_imports_are_clean() -> None:
    assert check_source(_CLEAN, filename="clean.py") == []


def test_qualified_qt_names_are_recognized() -> None:
    source = """\
from PySide6 import QtCore, QtWidgets

QtWidgets.QApplication([])
QtCore.QThread()
QtWidgets.QFileDialog.getOpenFileName(None, "x")
"""
    assert [item.rule for item in check_source(source)] == ["PSI001", "PSI002", "PSI003"]


def test_importing_qt_names_is_not_itself_a_finding() -> None:
    source = "from PySide6.QtWidgets import QApplication, QFileDialog\n"
    assert check_source(source) == []


def test_aliased_qt_names_are_resolved() -> None:
    source = """\
from PySide6.QtCore import QThread as Worker
from PySide6.QtWidgets import QApplication as QA, QFileDialog as Picker

class Job(Worker):
    pass

QA([])
Picker.getOpenFileName(None, "打开")
Job().terminate()
"""
    assert [item.rule for item in check_source(source)] == [
        "PSI002",
        "PSI001",
        "PSI003",
        "PSI002",
    ]


def test_aliased_modules_are_resolved() -> None:
    source = """\
import PySide6.QtCore as Core
from PySide6 import QtWidgets as Widgets

Widgets.QApplication([])
Core.QThread()
"""
    assert [item.rule for item in check_source(source)] == ["PSI001", "PSI002"]


def test_thread_identity_query_is_allowed() -> None:
    source = """\
from PySide6.QtCore import QThread

def on_ui_thread() -> bool:
    return QThread.currentThread() is app.thread()
"""
    assert check_source(source) == []


def test_syntax_error_becomes_finding() -> None:
    findings = check_source("def broken(:\n")
    assert len(findings) == 1
    assert findings[0].rule == "PSI000"
    assert "无法解析" in findings[0].message


def test_check_paths_skips_cache_and_excluded(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text(_CLEAN, encoding="utf-8")
    cache = tmp_path / "__pycache__"
    cache.mkdir()
    (cache / "stale.py").write_text(_BAD, encoding="utf-8")
    hidden = tmp_path / ".venv"
    hidden.mkdir()
    (hidden / "vendor.py").write_text(_BAD, encoding="utf-8")
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    (legacy / "old.py").write_text(_BAD, encoding="utf-8")

    found = {Path(item.path).name for item in check_paths([tmp_path])}
    assert found == {"old.py"}
    assert check_paths([tmp_path], exclude=[tmp_path / "legacy"]) == []
    assert check_paths([legacy])


def test_missing_and_non_python_paths_become_findings(tmp_path: Path) -> None:
    text = tmp_path / "notes.txt"
    text.write_text("hello", encoding="utf-8")
    missing = tmp_path / "missing"

    findings = check_paths([missing, text])
    assert [item.rule for item in findings] == ["PSI007", "PSI007"]
    assert {Path(item.path).name for item in findings} == {"missing", "notes.txt"}
    assert all(item.hint for item in findings)


def test_format_findings_includes_hint() -> None:
    text = format_findings(check_source(_BAD, filename="bad.py"))
    assert "bad.py:8:" in text
    assert "PSI001" in text
    assert "→" in text


def test_cli_exit_codes_and_output(tmp_path: Path) -> None:
    (tmp_path / "bad.py").write_text(_BAD, encoding="utf-8")
    env = os.environ.copy()
    env["QT_QPA_PLATFORM"] = "offscreen"
    completed = subprocess.run(
        [sys.executable, "-m", "psi6", "check", str(tmp_path)],
        env=env,
        check=False,
        capture_output=True,
        timeout=30,
    )
    assert completed.returncode == 2
    output = completed.stdout.decode("utf-8")
    assert "PSI004" in output
    assert "→" in output

    clean = tmp_path / "clean"
    clean.mkdir()
    (clean / "app.py").write_text(_CLEAN, encoding="utf-8")
    completed = subprocess.run(
        [sys.executable, "-m", "psi6", "check", str(clean)],
        env=env,
        check=False,
        capture_output=True,
        timeout=30,
    )
    assert completed.returncode == 0
    assert "未发现规范问题" in completed.stdout.decode("utf-8")


def test_cli_reports_a_missing_path(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["QT_QPA_PLATFORM"] = "offscreen"
    completed = subprocess.run(
        [sys.executable, "-m", "psi6", "check", str(tmp_path / "missing")],
        env=env,
        check=False,
        capture_output=True,
        timeout=30,
    )
    assert completed.returncode == 2
    assert "PSI007" in completed.stdout.decode("utf-8")
