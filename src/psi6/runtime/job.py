"""后台任务返回给 UI 的标准结果。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any


@dataclass
class JobOutcome:
    """一次任务结束后的表格行与状态文案。"""

    rows: list[dict[str, Any]] = field(default_factory=list)
    message: str = "完成"

    @classmethod
    def from_raw(cls, raw: Any) -> JobOutcome:
        """接受 ``JobOutcome`` 或 ``{"rows", "message", "count"}`` 字典。"""

        if isinstance(raw, JobOutcome):
            return raw
        if isinstance(raw, Mapping):
            rows = _as_row_list(raw.get("rows"))
            message = str(raw.get("message") or "").strip()
            if not message:
                count = raw.get("count", len(rows))
                message = f"完成，共 {count} 项"
            return cls(rows=rows, message=message)
        return cls(rows=[], message="完成")


def _as_row_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    rows: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, Mapping):
            rows.append(dict(item))
    return rows
