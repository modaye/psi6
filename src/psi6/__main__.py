"""``python -m psi6`` 启动文件索引；``python -m psi6 kit`` 打开组件主题预览。"""

from __future__ import annotations

import os
import sys


def main() -> None:
    """按参数分发参考窗口。"""

    if len(sys.argv) > 1 and sys.argv[1] in {"kit", "--kit"}:
        from psi6.examples.kit import main as kit_main

        kit_main()
        return
    if len(sys.argv) > 1 and sys.argv[1] in {"shot", "--screenshot"}:
        from psi6.runtime.qt_env import install_qt_message_filter, prepare_qt_environment

        prepare_qt_environment()
        install_qt_message_filter()
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from psi6.examples.visual_qa import main as shot_main

        sys.argv = [sys.argv[0], *sys.argv[2:]]
        shot_main()
        return
    from psi6.examples.file_index import main as index_main

    index_main()


if __name__ == "__main__":
    main()
