"""pytest-qt 在无显示器环境下使用 offscreen，并先指定系统字体目录。"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from psi6.runtime.qt_env import install_high_dpi_policy

install_high_dpi_policy()

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_windir = os.environ.get("WINDIR")
if _windir:
    _fonts = Path(_windir) / "Fonts"
    if _fonts.is_dir():
        os.environ.setdefault("QT_QPA_FONTDIR", str(_fonts))


@pytest.fixture(autouse=True)
def _default_theme(qapp):
    """每个测试从同一套默认 token 起步，不继承上一个测试留下的主题。"""

    from psi6.theme.apply import apply_theme

    apply_theme(qapp)


@pytest.fixture(autouse=True)
def _reset_framework_globals():
    """异常钩子和图标缓存都是进程级的，测试之间不能串。"""

    yield
    from psi6.icons.registry import clear_icon_overrides
    from psi6.icons.render import clear_icon_cache
    from psi6.runtime.errors import uninstall_exception_hooks

    uninstall_exception_hooks()
    clear_icon_cache()
    clear_icon_overrides()
