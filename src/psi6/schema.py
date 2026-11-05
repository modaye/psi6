"""Pydantic 字段 metadata。

这些工厂只往 ``json_schema_extra`` 里写标记，不导入 Qt，也不依赖 ``psi6.ui``。
任务层可以直接用同一份模型声明，界面再按标记选择控件。
"""

from __future__ import annotations

from typing import Any

from pydantic import Field

__all__ = [
    "field_advanced",
    "field_dir",
    "field_file",
    "field_secret",
    "field_switch",
]


def field_dir(*, group: str = "", **kwargs: Any) -> Any:
    """目录字段：生成 ``FolderInput``。"""

    extra = dict(kwargs.pop("json_schema_extra", {}) or {})
    extra["kind"] = "dir"
    if group:
        extra["group"] = group
    return Field(json_schema_extra=extra, **kwargs)


def field_file(
    *,
    filters: str = "All Files (*)",
    multiple: bool = False,
    group: str = "",
    **kwargs: Any,
) -> Any:
    """文件字段：生成 ``FileInput``。``multiple=True`` 对应 ``list[Path]``。"""

    extra = dict(kwargs.pop("json_schema_extra", {}) or {})
    extra.update({"kind": "file", "filters": filters, "multiple": multiple})
    if group:
        extra["group"] = group
    return Field(json_schema_extra=extra, **kwargs)


def field_advanced(*, group: str = "", **kwargs: Any) -> Any:
    """高级字段：生成表单时放进可折叠的「高级选项」。"""

    extra = dict(kwargs.pop("json_schema_extra", {}) or {})
    extra["advanced"] = True
    if group:
        extra["group"] = group
    return Field(json_schema_extra=extra, **kwargs)


def field_secret(*, group: str = "", **kwargs: Any) -> Any:
    """敏感字符串，输入框为密码模式。"""

    extra = dict(kwargs.pop("json_schema_extra", {}) or {})
    extra["secret"] = True
    if group:
        extra["group"] = group
    return Field(json_schema_extra=extra, **kwargs)


def field_switch(*, advanced: bool = False, group: str = "", hint: str = "", **kwargs: Any) -> Any:
    """布尔字段：生成 ``Switch``，适合设置项。``advanced=True`` 时放进高级选项。"""

    extra = dict(kwargs.pop("json_schema_extra", {}) or {})
    extra["kind"] = "switch"
    if advanced:
        extra["advanced"] = True
    if group:
        extra["group"] = group
    if hint:
        extra["hint"] = hint
    return Field(json_schema_extra=extra, **kwargs)
