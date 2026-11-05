"""表单的模型层：字段绑定、校验和错误展示。表单页与设置页共用。"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import UnionType
from typing import Any, Union, get_args, get_origin

from pydantic import BaseModel, ValidationError
from pydantic.fields import FieldInfo
from PySide6.QtCore import QObject
from PySide6.QtWidgets import QLabel, QWidget


class FormError(Exception):
    """表单校验失败。``field_errors`` 为字段名到中文说明。"""

    def __init__(self, message: str, field_errors: dict[str, str] | None = None) -> None:
        super().__init__(message)
        self.field_errors = field_errors or {}


class _Unset:
    """控件里没有值，且模型自己有默认值可用的标记。"""

    def __repr__(self) -> str:
        return "UNSET"


UNSET = _Unset()


def field_default(field: FieldInfo) -> Any:
    """字段默认值。``default_factory`` 也要执行，否则列表和字典字段是空的。"""

    if field.is_required():
        return None
    return field.get_default(call_default_factory=True)


def union_args(annotation: Any) -> tuple[Any, ...] | None:
    origin = get_origin(annotation)
    if origin is Union or origin is UnionType:
        return get_args(annotation)
    return None


def unwrap_annotation(annotation: Any) -> Any:
    """去掉 ``X | None`` 里的 ``None``，只留实际类型。"""

    args = union_args(annotation)
    if args is None:
        return annotation
    nonempty = [item for item in args if item is not type(None)]
    if len(nonempty) == 1:
        return nonempty[0]
    return annotation


def is_optional(annotation: Any) -> bool:
    args = union_args(annotation)
    return args is not None and type(None) in args


def field_extra(field: FieldInfo) -> dict[str, Any]:
    raw = field.json_schema_extra
    return dict(raw) if isinstance(raw, dict) else {}


def format_field_error(error: Mapping[str, Any]) -> str:
    """把 Pydantic 错误翻成短中文。"""

    kind = str(error.get("type", ""))
    if kind in {"missing", "value_error.missing"}:
        return "此项为必填"
    if kind in {"string_too_short", "too_short"}:
        return "内容过短"
    if kind in {"string_too_long", "too_long"}:
        return "内容过长"
    if kind in {"greater_than", "greater_than_equal"}:
        return "数值过小"
    if kind in {"less_than", "less_than_equal"}:
        return "数值过大"
    if kind in {"int_parsing", "int_type", "int_from_float"}:
        return "请填写整数"
    if kind in {"float_parsing", "float_type", "finite_number"}:
        return "请填写数字"
    if kind in {"datetime_parsing", "datetime_type", "datetime_from_date_parsing"}:
        return "日期时间格式无效"
    if kind in {"date_parsing", "date_type", "date_from_datetime_parsing"}:
        return "日期格式无效"
    if kind in {"time_parsing", "time_type", "time_delta_parsing"}:
        return "时间格式无效"
    if kind in {"enum", "literal_error"}:
        return "选项无效"
    if kind.startswith("path") or "path" in kind:
        return "路径无效"
    msg = str(error.get("msg", "")).strip()
    if msg and "validation error" not in msg.lower():
        return msg
    return "填写有误"


def collect_field_errors(exc: ValidationError) -> dict[str, str]:
    """每个字段只留第一条错误，按模型字段顺序展示。"""

    field_errors: dict[str, str] = {}
    for error in exc.errors():
        loc = error.get("loc") or ()
        name = str(loc[0]) if loc else ""
        if name and name not in field_errors:
            field_errors[name] = format_field_error(error)
    return field_errors


@dataclass(slots=True)
class FieldBinding:
    """单个字段的控件与读写。"""

    name: str
    field: FieldInfo
    extra: dict[str, Any]
    annotation: Any
    optional: bool
    widget: QWidget
    error_label: QLabel
    getter: Callable[[], Any]
    setter: Callable[[Any], None]
    validator: Callable[[Any], str | None] | None = None


class ModelFormController:
    """把字段控件与 ``BaseModel`` 的读取、回填、校验放在一起。"""

    def __init__(
        self,
        model_type: type[BaseModel],
        *,
        error_message: str = "参数无效",
    ) -> None:
        self.model_type = model_type
        self.error_message = error_message
        self._bindings: list[FieldBinding] = []
        self._hidden: dict[str, Any] = {}
        self._hidden_fields: dict[str, FieldInfo] = {}

    @property
    def bindings(self) -> tuple[FieldBinding, ...]:
        return tuple(self._bindings)

    def add(
        self,
        name: str,
        field: FieldInfo,
        *,
        widget: QWidget,
        error_label: QLabel,
        getter: Callable[[], Any],
        setter: Callable[[Any], None],
        validator: Callable[[Any], str | None] | None = None,
    ) -> FieldBinding:
        binding = FieldBinding(
            name=name,
            field=field,
            extra=field_extra(field),
            annotation=unwrap_annotation(field.annotation),
            optional=is_optional(field.annotation),
            widget=widget,
            error_label=error_label,
            getter=getter,
            setter=setter,
            validator=validator,
        )
        self._bindings.append(binding)
        return binding

    def add_hidden(self, name: str, field: FieldInfo, value: Any = UNSET) -> None:
        """没有控件的字段也要进提交数据，否则回填一次就丢了。"""

        if value is UNSET:
            value = field_default(field)
        if value is None and not is_optional(field.annotation):
            value = UNSET
        self._hidden[name] = value
        self._hidden_fields[name] = field

    def get_model(self) -> BaseModel:
        """读取控件并校验。失败时高亮字段并抛出 ``FormError``。"""

        self.clear_errors()
        payload: dict[str, Any] = {
            name: value for name, value in self._hidden.items() if value is not UNSET
        }
        pre_errors: dict[str, str] = {}
        for binding in self._bindings:
            value = binding.getter()
            if value is not UNSET:
                payload[binding.name] = value
            if binding.validator is not None:
                message = binding.validator(value)
                if message:
                    pre_errors[binding.name] = message
        model: BaseModel | None = None
        field_errors: dict[str, str] = {}
        try:
            model = self.model_type.model_validate(payload)
        except ValidationError as exc:
            field_errors = collect_field_errors(exc)
        field_errors.update(pre_errors)
        if field_errors:
            self.show_errors(field_errors)
            message = next(iter(field_errors.values()), self.error_message)
            raise FormError(message, field_errors)
        assert model is not None
        return model

    def set_model(self, model: BaseModel, *, block_signals: bool = True) -> None:
        """回填全部字段。默认挡住控件信号，避免「即改即存」被写成半截值。"""

        data = model.model_dump()
        for name in self._hidden:
            if name in data:
                value = data[name]
                field = self._hidden_fields[name]
                self._hidden[name] = (
                    UNSET if value is None and not is_optional(field.annotation) else value
                )
        silenced = self._silence(block_signals)
        try:
            for binding in self._bindings:
                if binding.name in data:
                    binding.setter(data[binding.name])
            self.clear_errors()
        finally:
            for obj, blocked in reversed(silenced):
                obj.blockSignals(blocked)

    def show_errors(self, field_errors: dict[str, str]) -> None:
        lookup = {binding.name: binding for binding in self._bindings}
        for name, text in field_errors.items():
            binding = lookup.get(name)
            if binding is None:
                continue
            binding.error_label.setText(text)
            binding.error_label.show()

    def clear_errors(self) -> None:
        for binding in self._bindings:
            binding.error_label.hide()
            binding.error_label.setText("")

    def _silence(self, enabled: bool) -> list[tuple[QObject, bool]]:
        silenced: list[tuple[QObject, bool]] = []
        if not enabled:
            return silenced
        for binding in self._bindings:
            for obj in (binding.widget, *binding.widget.findChildren(QObject)):
                silenced.append((obj, obj.signalsBlocked()))
                obj.blockSignals(True)
        return silenced
