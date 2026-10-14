"""新项目模板：公开导入，并且 python app.py --check 能退出。"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

_TEMPLATE = Path(__file__).resolve().parents[1] / "skills" / "psi6-desktop" / "template"


def test_template_uses_public_imports() -> None:
    allowed = {
        "psi6",
        "psi6.runtime.logs",
        "psi6.ui.buttons",
        "psi6.ui.log_panel",
        "psi6.ui.status_progress",
        "PySide6.QtWidgets",
    }
    for path in sorted(_TEMPLATE.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or not node.module:
                continue
            if node.module in {"__future__", "job", "theme", "window"}:
                continue
            assert node.module in allowed, node.module
            assert "._" not in node.module


def test_template_check_returns_zero() -> None:
    """在模板目录用仓库解释器跑 --check，避免单独 uv sync 去装未发布的版本。"""

    env = os.environ.copy()
    env["QT_QPA_PLATFORM"] = "offscreen"
    completed = subprocess.run(
        [sys.executable, "app.py", "--check"],
        cwd=_TEMPLATE,
        env=env,
        check=False,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr
