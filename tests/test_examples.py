"""安装后示例只依赖公共导入，并且 --check 能退出。"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

from psi6.examples import task_job
from psi6.runtime.tasks import TaskRunner, TaskStatus


def test_examples_use_public_imports() -> None:
    root = Path(task_job.__file__).resolve().parent
    allowed = {"psi6", "psi6.ui.buttons", "psi6.ui.status_progress", "PySide6.QtCore", "PySide6.QtWidgets"}
    for name in ("minimal.py", "task_job.py", "custom_theme.py", "task_status.py"):
        tree = ast.parse((root / name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module == "__future__":
                    continue
                assert node.module in allowed or node.module.startswith("psi6.examples")
                assert "._" not in node.module


def test_example_checks_return_zero() -> None:
    """单独进程里跑 --check，避免 QApplication.quit 拆掉测试用的事件循环。"""

    for module in (
        "psi6.examples.minimal",
        "psi6.examples.task_job",
        "psi6.examples.custom_theme",
        "psi6.examples.task_status",
    ):
        completed = subprocess.run(
            [sys.executable, "-m", module, "--check"],
            check=False,
            timeout=30,
        )
        assert completed.returncode == 0, module


def test_task_job_failure_is_on_the_handle(qtbot) -> None:
    runner = TaskRunner()
    seen: list[str] = []
    handle = runner.submit(task_job.fail_read, on_failed=seen.append)
    qtbot.waitUntil(lambda: handle.status is TaskStatus.FAILED, timeout=3000)
    assert seen == ["读失败"]
    assert handle.error_message == "读失败"
    assert handle.result is None
