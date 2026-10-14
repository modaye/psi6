"""psi6 框架入口。控件从 ``psi6.ui`` 导入，批处理窗从 ``psi6.templates`` 导入。"""

from psi6.runtime.app import App
from psi6.runtime.job import JobOutcome
from psi6.runtime.tasks import TaskHandle, TaskRunner, TaskStatus
from psi6.theme.diagnose import contrast_notes
from psi6.theme.theme import Theme
from psi6.theme.tokens import Tokens
from psi6.ui.desktop_window import DesktopWindow
from psi6.ui.title_bar import TitleBar
from psi6.ui.tray import TrayIcon

__all__ = [
    "App",
    "DesktopWindow",
    "JobOutcome",
    "TaskHandle",
    "TaskRunner",
    "TaskStatus",
    "Theme",
    "TitleBar",
    "Tokens",
    "TrayIcon",
    "contrast_notes",
]
