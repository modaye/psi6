"""由 Pydantic Model 生成表单，校验逻辑以模型为准。"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import date, datetime, time
from enum import Enum
from pathlib import Path
from types import UnionType
from typing import Any, Literal, Union, get_args, get_origin

from pydantic import BaseModel, Field, ValidationError
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined
from PySide6.QtCore import QDate, QDateTime, QTime
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDateTimeEdit,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from psi6.ui.collapsible import Collapsible
from psi6.ui.file_input import FileInput, FolderInput
from psi6.ui.switch import Switch

try:
    from annotated_types import Ge, Gt, Le, Lt
except ImportError:  # pragma: no cover - pydantic 会带上 annotated-types
    Ge = Gt = Le = Lt = None  # type: ignore[misc, assignment]


class FormError(Exception):
    """表单校验失败。``field_errors`` 为字段名到中文说明。"""

    def __init__(self, message: str, field_errors: dict[str, str] | None = None) -> None:
        super().__init__(message)
        self.field_errors = field_errors or {}


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


def _union_args(annotation: Any) -> tuple[Any, ...] | None:
    origin = get_origin(annotation)
    if origin is Union or origin is UnionType:
        return get_args(annotation)
    return None


def _unwrap(annotation: Any) -> Any:
    args = _union_args(annotation)
    if args is None:
        return annotation
    nonempty = [item for item in args if item is not type(None)]
    if len(nonempty) == 1:
        return nonempty[0]
    return annotation


def _is_optional(annotation: Any) -> bool:
    args = _union_args(annotation)
    return args is not None and type(None) in args


def _extra(field: FieldInfo) -> dict[str, Any]:
    raw = field.json_schema_extra
    return dict(raw) if isinstance(raw, dict) else {}


def _field_default(field: FieldInfo) -> Any:
    if field.default is PydanticUndefined:
        return None
    return field.default


def _numeric_bounds(field: FieldInfo) -> tuple[float | None, float | None]:
    low: float | None = None
    high: float | None = None
    if Ge is None:
        return low, high
    for item in field.metadata:
        if isinstance(item, Ge):
            low = float(item.ge)
        elif isinstance(item, Gt):
            low = float(item.gt)
        elif isinstance(item, Le):
            high = float(item.le)
        elif isinstance(item, Lt):
            high = float(item.lt)
    return low, high


def format_field_error(error: dict[str, Any]) -> str:
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
    if kind.startswith("path") or "path" in kind:
        return "路径无效"
    msg = str(error.get("msg", "")).strip()
    if msg and "validation error" not in msg.lower():
        return msg
    return "填写有误"


class _Binding:
    """单个字段的控件与读写。"""

    def __init__(
        self,
        name: str,
        widget: QWidget,
        error_label: QLabel,
        getter: Callable[[], Any],
        setter: Callable[[Any], None],
    ) -> None:
        self.name = name
        self.widget = widget
        self.error_label = error_label
        self.getter = getter
        self.setter = setter


class FormView(QWidget):
    """Schema 驱动的表单。"""

    def __init__(
        self,
        model_type: type[BaseModel],
        *,
        initial: BaseModel | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._model_type = model_type
        self._bindings: list[_Binding] = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        main_form = QFormLayout()
        main_form.setHorizontalSpacing(12)
        main_form.setVerticalSpacing(8)
        advanced_form = QFormLayout()
        advanced_form.setHorizontalSpacing(12)
        advanced_form.setVerticalSpacing(8)
        advanced_count = 0
        for name, field in model_type.model_fields.items():
            extra = _extra(field)
            if extra.get("hidden"):
                continue
            binding = self._make_binding(name, field, extra)
            self._bindings.append(binding)
            label = field.description or name
            cell = QWidget()
            cell_layout = QVBoxLayout(cell)
            cell_layout.setContentsMargins(0, 0, 0, 0)
            cell_layout.setSpacing(2)
            cell_layout.addWidget(binding.widget)
            cell_layout.addWidget(binding.error_label)
            binding.error_label.hide()
            target = advanced_form if extra.get("advanced") else main_form
            target.addRow(label, cell)
            if extra.get("advanced"):
                advanced_count += 1
        layout.addLayout(main_form)
        if advanced_count:
            self._advanced = Collapsible("高级选项")
            advanced_box = QWidget()
            advanced_box.setLayout(advanced_form)
            self._advanced.add_widget(advanced_box)
            layout.addWidget(self._advanced)
        if initial is not None:
            self.set_model(initial)

    def get_model(self) -> BaseModel:
        """读取控件并校验。失败时高亮字段并抛出 ``FormError``。"""

        self._clear_errors()
        payload: dict[str, Any] = {}
        for binding in self._bindings:
            payload[binding.name] = binding.getter()
        try:
            return self._model_type.model_validate(payload)
        except ValidationError as exc:
            field_errors: dict[str, str] = {}
            for error in exc.errors():
                loc = error.get("loc") or ()
                name = str(loc[0]) if loc else ""
                if name and name not in field_errors:
                    field_errors[name] = format_field_error(error)
            self._show_errors(field_errors)
            message = next(iter(field_errors.values()), "参数无效")
            raise FormError(message, field_errors) from exc

    def set_model(self, model: BaseModel) -> None:
        data = model.model_dump()
        for binding in self._bindings:
            if binding.name in data:
                binding.setter(data[binding.name])
        self._clear_errors()

    def _show_errors(self, field_errors: dict[str, str]) -> None:
        lookup = {item.name: item for item in self._bindings}
        for name, text in field_errors.items():
            binding = lookup.get(name)
            if binding is None:
                continue
            binding.error_label.setText(text)
            binding.error_label.show()

    def _clear_errors(self) -> None:
        for binding in self._bindings:
            binding.error_label.hide()
            binding.error_label.setText("")

    def _make_binding(self, name: str, field: FieldInfo, extra: dict[str, Any]) -> _Binding:
        optional = _is_optional(field.annotation)
        annotation = _unwrap(field.annotation)
        error = QLabel()
        error.setObjectName("psi6Error")
        widget, getter, setter = create_field_editor(annotation, field, extra, optional)
        return _Binding(name, widget, error, getter, setter)

    def _build_widget(
        self,
        annotation: Any,
        field: FieldInfo,
        extra: dict[str, Any],
        optional: bool,
    ) -> tuple[QWidget, Callable[[], Any], Callable[[Any], None]]:
        return create_field_editor(annotation, field, extra, optional)


def create_field_editor(
    annotation: Any,
    field: FieldInfo,
    extra: dict[str, Any],
    optional: bool,
) -> tuple[QWidget, Callable[[], Any], Callable[[Any], None]]:
    """为单个 Pydantic 字段构造控件。表单和设置页共用。"""

    default = _field_default(field)
    if annotation is bool:
        box = Switch() if extra.get("kind") == "switch" else QCheckBox()
        box.setChecked(bool(default) if default is not None else False)

        def get_bool() -> bool:
            return box.isChecked()

        def set_bool(value: Any) -> None:
            box.setChecked(bool(value))

        return box, get_bool, set_bool

    if annotation in {datetime, date, time}:
        return _datetime_editor(annotation, default)

    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin in {list, tuple, Sequence} and args and args[0] is Path:
        picker = FileInput(
            filters=str(extra.get("filters") or "All Files (*)"),
            multiple=True,
            allow_empty=optional,
        )
        if isinstance(default, Sequence) and not isinstance(default, (str, bytes)):
            picker.set_paths([Path(item) for item in default])

        def get_paths() -> list[Path] | None:
            found = picker.paths()
            if optional and not found:
                return None
            return found

        def set_paths(value: Any) -> None:
            if value is None:
                picker.set_paths([])
                return
            picker.set_paths([Path(item) for item in value])

        return picker, get_paths, set_paths

    if annotation is Path:
        if extra.get("kind") == "dir":
            path_picker: FileInput | FolderInput = FolderInput(allow_empty=optional)
        else:
            path_picker = FileInput(
                filters=str(extra.get("filters") or "All Files (*)"),
                multiple=bool(extra.get("multiple", False)),
                allow_empty=optional,
            )
        if isinstance(default, (Path, str)):
            path_picker.set_path(default)

        def get_path() -> Path | list[Path] | None:
            if extra.get("multiple") and isinstance(path_picker, FileInput):
                return path_picker.paths()
            return path_picker.path()

        def set_path(value: Any) -> None:
            if extra.get("multiple") and isinstance(path_picker, FileInput):
                if value is None:
                    path_picker.set_paths([])
                elif isinstance(value, (list, tuple)):
                    path_picker.set_paths(list(value))
                else:
                    path_picker.set_path(value)
                return
            path_picker.set_path(value)

        return path_picker, get_path, set_path

    if isinstance(annotation, type) and issubclass(annotation, Enum):
        combo = QComboBox()
        members = list(annotation)
        for member in members:
            combo.addItem(str(member.value), member)
        if isinstance(default, Enum):
            combo.setCurrentText(str(default.value))

        def get_enum() -> Any:
            return combo.currentData()

        def set_enum(value: Any) -> None:
            if isinstance(value, Enum):
                combo.setCurrentText(str(value.value))
            elif value is None:
                combo.setCurrentIndex(0)
            else:
                combo.setCurrentText(str(value))

        return combo, get_enum, set_enum

    if origin is Literal:
        combo = QComboBox()
        for option in get_args(annotation):
            combo.addItem(str(option), option)
        if default is not None:
            combo.setCurrentText(str(default))

        def get_literal() -> Any:
            return combo.currentData()

        def set_literal(value: Any) -> None:
            combo.setCurrentText("" if value is None else str(value))

        return combo, get_literal, set_literal

    if annotation is int:
        spin = QSpinBox()
        low, high = _numeric_bounds(field)
        spin.setRange(
            int(low) if low is not None else -1_000_000_000,
            int(high) if high is not None else 1_000_000_000,
        )
        if isinstance(default, int):
            spin.setValue(default)

        def get_int() -> int:
            return spin.value()

        def set_int(value: Any) -> None:
            spin.setValue(int(value or 0))

        return spin, get_int, set_int

    if annotation is float:
        spin_f = QDoubleSpinBox()
        spin_f.setDecimals(4)
        low, high = _numeric_bounds(field)
        spin_f.setRange(low if low is not None else -1e12, high if high is not None else 1e12)
        if isinstance(default, (int, float)):
            spin_f.setValue(float(default))

        def get_float() -> float:
            return spin_f.value()

        def set_float(value: Any) -> None:
            spin_f.setValue(float(value or 0))

        return spin_f, get_float, set_float

    edit = QLineEdit()
    if extra.get("secret") or extra.get("password"):
        edit.setEchoMode(QLineEdit.EchoMode.Password)
    if isinstance(default, str):
        edit.setText(default)
    example = extra.get("placeholder")
    if isinstance(example, str):
        edit.setPlaceholderText(example)

    def get_str() -> str | None:
        text = edit.text()
        if optional and text == "":
            return None
        return text

    def set_str(value: Any) -> None:
        edit.setText("" if value is None else str(value))

    return edit, get_str, set_str


def _datetime_editor(
    annotation: type,
    default: Any,
) -> tuple[QWidget, Callable[[], Any], Callable[[Any], None]]:
    if annotation is datetime:
        stamp = QDateTimeEdit()
        stamp.setCalendarPopup(True)
        stamp.setDisplayFormat("yyyy-MM-dd HH:mm")
        if isinstance(default, datetime):
            stamp.setDateTime(
                QDateTime(
                    QDate(default.year, default.month, default.day),
                    QTime(default.hour, default.minute, default.second),
                )
            )
        else:
            stamp.setDateTime(QDateTime.currentDateTime())

        def get_dt() -> datetime:
            stamp_value = stamp.dateTime()
            day = stamp_value.date()
            clock = stamp_value.time()
            return datetime(  # noqa: DTZ001
                day.year(),
                day.month(),
                day.day(),
                clock.hour(),
                clock.minute(),
                clock.second(),
            )

        def set_dt(value: Any) -> None:
            if isinstance(value, datetime):
                stamp.setDateTime(
                    QDateTime(
                        QDate(value.year, value.month, value.day),
                        QTime(value.hour, value.minute, value.second),
                    )
                )

        return stamp, get_dt, set_dt

    if annotation is date:
        day = QDateEdit()
        day.setCalendarPopup(True)
        day.setDisplayFormat("yyyy-MM-dd")
        if isinstance(default, date):
            day.setDate(QDate(default.year, default.month, default.day))
        else:
            day.setDate(QDate.currentDate())

        def get_date() -> date:
            day_value = day.date()
            return date(day_value.year(), day_value.month(), day_value.day())

        def set_date(value: Any) -> None:
            if isinstance(value, date):
                day.setDate(QDate(value.year, value.month, value.day))

        return day, get_date, set_date

    clock = QTimeEdit()
    clock.setDisplayFormat("HH:mm")
    if isinstance(default, time):
        clock.setTime(QTime(default.hour, default.minute, default.second))
    else:
        clock.setTime(QTime.currentTime())

    def get_time() -> time:
        clock_value = clock.time()
        return time(clock_value.hour(), clock_value.minute(), clock_value.second())

    def set_time(value: Any) -> None:
        if isinstance(value, time):
            clock.setTime(QTime(value.hour, value.minute, value.second))

    return clock, get_time, set_time


def pydantic_form(
    model: type[BaseModel] | BaseModel,
    *,
    parent: QWidget | None = None,
) -> FormView:
    """由 Model 类型或实例生成表单。``Path`` 字段按 metadata 映射到文件/目录输入。"""

    if isinstance(model, BaseModel):
        return FormView(type(model), initial=model, parent=parent)
    return FormView(model, parent=parent)
