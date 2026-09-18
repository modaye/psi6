"""可运行参考工具：索引目录中的文件。"""

from __future__ import annotations

from psi6.jobs.file_index import FILE_INDEX_COLUMNS, FileIndexParams, run_file_index
from psi6.runtime.app import App
from psi6.templates.batch_tool import BatchToolWindow


def main() -> None:
    """启动文件索引窗口。上次使用的目录会写入配置。"""

    app = App("psi6-file-index")
    window = BatchToolWindow(
        title="psi6 文件索引",
        params=FileIndexParams(),
        job=run_file_index,
        app=app,
        result_columns=FILE_INDEX_COLUMNS,
        icon="folder",
        exclusive="batch",
    )
    raise SystemExit(app.run(window, tray=True, single_instance=True))
