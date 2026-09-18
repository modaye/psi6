"""文件索引：示范 ``run_job`` 合同（真实扫盘、可取消）。不是要发布的业务产品。"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path

from pydantic import BaseModel

from psi6.runtime.job import JobOutcome
from psi6.runtime.logs import LogLevel, LogRecord
from psi6.ui.data_table import TableColumn
from psi6.ui.form import field_advanced, field_dir, field_switch

FILE_INDEX_COLUMNS = [
    TableColumn("name", "文件名"),
    TableColumn("suffix", "类型"),
    TableColumn("size", "大小"),
    TableColumn("path", "路径", stretch=True),
]


class FileIndexParams(BaseModel):
    """扫描参数。"""

    input_dir: Path = field_dir(default_factory=Path.cwd, description="输入目录")
    recursive: bool = field_switch(default=True, description="包含子目录", advanced=True)
    suffix: str = field_advanced(default="", description="扩展名过滤，如 .txt（空则全部）")
    max_files: int = field_advanced(default=5000, ge=1, le=100_000, description="最多列出条数")


def _normalize_suffix(raw: str) -> str:
    text = raw.strip().lower()
    if not text:
        return ""
    return text if text.startswith(".") else f".{text}"


def iter_files(
    root: Path,
    *,
    recursive: bool,
    suffix: str,
) -> Iterator[Path]:
    """列出匹配文件。不可读的目录由调用方记日志。"""

    wanted = _normalize_suffix(suffix)
    if recursive:
        iterator = root.rglob("*")
    else:
        iterator = root.iterdir()
    for path in iterator:
        try:
            is_file = path.is_file()
        except OSError:
            continue
        if not is_file:
            continue
        if wanted and path.suffix.lower() != wanted:
            continue
        yield path


def run_file_index(
    params: FileIndexParams,
    *,
    on_progress: Callable[[int, int, str], None],
    on_log: Callable[[LogRecord], None],
    is_cancelled: Callable[[], bool],
) -> JobOutcome:
    """扫描目录，返回可放入 ``DataTable`` 的行。不修改磁盘。"""

    folder = params.input_dir
    if not folder.is_dir():
        on_log(LogRecord(LogLevel.ERROR, "输入目录不存在", extra={"path": str(folder)}))
        raise FileNotFoundError(str(folder))

    rows: list[dict[str, str | int]] = []
    for path in iter_files(
        folder,
        recursive=params.recursive,
        suffix=params.suffix,
    ):
        if is_cancelled():
            raise InterruptedError
        if len(rows) >= params.max_files:
            on_log(
                LogRecord(
                    LogLevel.WARNING,
                    f"已达到上限 {params.max_files}，其余文件未列入",
                )
            )
            break
        try:
            size = path.stat().st_size
        except OSError as exc:
            on_log(
                LogRecord(
                    LogLevel.ERROR,
                    f"无法读取 {path.name}",
                    detail=str(exc),
                    extra={"path": str(path)},
                )
            )
            continue
        rows.append(
            {
                "name": path.name,
                "suffix": path.suffix.lower(),
                "size": size,
                "path": str(path),
            }
        )
        on_progress(len(rows), max(len(rows), 1), f"索引 {path.name}")
        on_log(
            LogRecord(
                LogLevel.SUCCESS,
                f"已索引 {path.name}",
                extra={"path": str(path)},
            )
        )

    if not rows:
        on_log(LogRecord(LogLevel.WARNING, "没有匹配的文件"))
        return JobOutcome(rows=[], message="没有匹配的文件")
    return JobOutcome(rows=rows, message=f"完成，共 {len(rows)} 个文件")
