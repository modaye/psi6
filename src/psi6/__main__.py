"""``python -m psi6`` 启动文件索引。

``python -m psi6 kit`` 打开样例工作台，``python -m psi6 kit --workbench`` 打开组件主题预览，
``python -m psi6 catalog`` 打印控件索引，
``python -m psi6 check`` 检查业务代码是否绕开框架。
"""

from __future__ import annotations

import os
import sys


def main() -> None:
    """按参数分发参考窗口、控件索引或规范检查。"""

    if len(sys.argv) > 1 and sys.argv[1] in {"check", "--check"}:
        from psi6.spec import main as check_main

        raise SystemExit(check_main(sys.argv[2:]))
    if len(sys.argv) > 1 and sys.argv[1] in {"catalog", "--catalog"}:
        from psi6.ui.catalog import main as catalog_main

        raise SystemExit(catalog_main(sys.argv[2:]))
    if len(sys.argv) > 1 and sys.argv[1] in {"theme", "--theme"}:
        from psi6.theme.cli import main as theme_main

        raise SystemExit(theme_main(sys.argv[2:]))
    if len(sys.argv) > 1 and sys.argv[1] in {"kit", "--kit"}:
        from psi6.examples.kit import main as kit_main

        kit_main()
        return
    if len(sys.argv) > 1 and sys.argv[1] in {"gallery", "--gallery"}:
        from psi6.examples.gallery import main as gallery_main

        raise SystemExit(gallery_main(sys.argv[2:]))
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
