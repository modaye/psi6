"""把 pytest 的失败行写成 GitHub Actions 注释。

公开仓库的任务日志需要登录才能看。注释会出现在 Check Run 上，接口可以直接读。
"""

from __future__ import annotations

import pathlib
import sys


def main() -> None:
    """读取日志，最多打出 30 条失败摘要。"""

    text = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
    lines = [line for line in text.splitlines() if line.startswith(("FAILED", "ERROR", "E ", "="))]
    picked = lines[-30:] or text.splitlines()[-30:]
    for line in picked:
        safe = line.replace("%", "%25").replace("\r", "")
        print(f"::error::{safe}", flush=True)


if __name__ == "__main__":
    main()
