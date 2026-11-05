"""按 Pydantic 字段类型构造编辑控件。表单页与设置页共用。"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time
from enum import Enum
from pathlib import Path
from typing import Any, Literal, get_args, get_origin

from pydantic.fields import FieldInfo
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QCompleter,
    QLineEdit,
    QWidget,
)

from psi6.ui.file_input import FileInput, FolderInput, PathState
from psi6.ui.form_model import UNSET, field_default
from psi6.ui.switch import Switch

__all__ = ["FieldEditor", "build_field_editor", "create_field_editor", "switch_row_supported"]

TEMPORAL_EXAMPLES = {
    datetime: "2024-01-02 03:04:05",
    date: "2024-01-02",
    time: "03:04:05",
}


@dataclass(frozen=True, slots=True)
class FieldEditor:
    """字段控件及其读写函数。``validator`` 在模型校验前给出中文错误。"""

    widget: QWidget
    getter: Callable[[], Any]
    setter: Callable[[Any], None]
    validator: Callable[[Any], str | None] | None = None


def create_field_editor(
    annotation: Any,
    field: FieldInfo,
    extra: dict[str, Any],
    optional: bool,
) -> tuple[QWidget, Callable[[], Any], Callable[[Any], None]]:
    """兼容旧调用方的三元组。需要字段校验时用 ``build_field_editor``。"""

    editor = build_field_editor(annotation, field, extra, optional)
    return editor.widget, editor.getter, editor.setter


def build_field_editor(
    annotation: Any,
    field: FieldInfo,
    extra: dict[str, Any],
    optional: bool,
    *,
    name: str = "",
) -> FieldEditor:
    """为单个 Pydantic 字段构造控件，返回控件、读写函数和可选校验。

    ``annotation`` 应已去掉 ``None``，``optional`` 表示原注解允许 ``None``。
    无法表达的注解直接抛 ``TypeError``，不会退化成文本框。
    """

    default = field_default(field)
    if annotation is bool:
        if optional:
            tri = QCheckBox()
            tri.setTristate(True)

            def get_opt_bool() -> bool | None:
                state = tri.checkState()
                if state is Qt.CheckState.PartiallyChecked:
                    return None
                return state is Qt.CheckState.Checked

            def set_opt_bool(value: Any) -> None:
                if value is None:
                    state = Qt.CheckState.PartiallyChecked
                else:
                    state = Qt.CheckState.Checked if value else Qt.CheckState.Unchecked
                tri.setCheckState(state)

            set_opt_bool(default)
            return FieldEditor(tri, get_opt_bool, set_opt_bool)

        box = Switch() if extra.get("kind") == "switch" else QCheckBox()
        box.setChecked(bool(default) if default is not None else False)

        def get_bool() -> bool:
            return box.isChecked()

        def set_bool(value: Any) -> None:
            box.setChecked(bool(value))

        return FieldEditor(box, get_bool, set_bool)

    if annotation in {datetime, date, time}:
        return _temporal_editor(annotation, default, optional, field)

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

        return FieldEditor(picker, get_paths, set_paths, _path_validator(picker, optional))

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

        return FieldEditor(path_picker, get_path, set_path, _path_validator(path_picker, optional))

    if isinstance(annotation, type) and issubclass(annotation, Enum):
        members = list(annotation)
        combo = _choice_combo(
            [(str(member.value), member) for member in members],
            current=default if isinstance(default, Enum) else None,
            search=bool(extra.get("search")),
            optional=optional,
        )

        def get_enum() -> Any:
            return combo.currentData()

        def set_enum(value: Any) -> None:
            _select_choice(combo, None if value is None else str(getattr(value, "value", value)))

        return FieldEditor(combo, get_enum, set_enum)

    if origin is Literal:
        options = list(get_args(annotation))
        combo = _choice_combo(
            [(str(option), option) for option in options],
            current=default,
            search=bool(extra.get("search")),
            optional=optional,
        )

        def get_literal() -> Any:
            return combo.currentData()

        def set_literal(value: Any) -> None:
            _select_choice(combo, None if value is None else str(value))

        return FieldEditor(combo, get_literal, set_literal)

    if annotation is int:
        return _number_editor(annotation, default, optional, field)

    if annotation is float:
        return _number_editor(annotation, default, optional, field)

    if annotation in {str, Any}:
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

        return FieldEditor(edit, get_str, set_str)

    label = name or "字段"
    raise TypeError(
        f"{label} 的类型 {annotation!r} 无法生成表单。"
        "支持 str、bool、int、float、Path、list[Path]、datetime、date、time、Enum 和 Literal。"
    )


def switch_row_supported(annotation: Any, extra: dict[str, Any], optional: bool) -> bool:
    """``SettingRow`` 只有两态，只能承接非可选布尔字段。"""

    return annotation is bool and not optional and extra.get("kind") == "switch"


def _number_editor(
    annotation: type[int] | type[float],
    default: Any,
    optional: bool,
    field: FieldInfo,
) -> FieldEditor:
    """数字用文本框。``QSpinBox`` 只到 32 位，还会把空值写成 0。"""

    edit = QLineEdit()
    edit.setProperty("psi6NumberKind", "int" if annotation is int else "float")
    required = field.is_required() and not optional
    if optional:
        edit.setPlaceholderText("留空表示不设置")
    elif required:
        edit.setPlaceholderText("必填")
    else:
        edit.setPlaceholderText("整数" if annotation is int else "数字")
    if default is not None:
        edit.setText(str(default))

    def get_number() -> Any:
        text = edit.text().strip()
        if text:
            return text
        if optional:
            return None
        return "" if required else UNSET

    def set_number(value: Any) -> None:
        edit.setText("" if value is None else str(value))

    validator = _required_text if required else None
    return FieldEditor(edit, get_number, set_number, validator)


def _temporal_editor(
    annotation: type,
    default: Any,
    optional: bool,
    field: FieldInfo,
) -> FieldEditor:
    """时间用 ISO 文本。秒、微秒和时区都能原样往返，空值保持未设置。"""

    edit = QLineEdit()
    example = TEMPORAL_EXAMPLES[annotation]
    prefix = "留空表示不设置；" if optional else ""
    edit.setPlaceholderText(f"{prefix}例如 {example}")
    edit.setProperty("psi6TemporalKind", annotation.__name__)
    if default is not None:
        edit.setText(default.isoformat() if hasattr(default, "isoformat") else str(default))
    required = field.is_required() and not optional

    def get_temporal() -> Any:
        text = edit.text().strip()
        if text:
            return text
        if optional:
            return None
        return "" if required else UNSET

    def set_temporal(value: Any) -> None:
        if value is None:
            edit.clear()
        elif hasattr(value, "isoformat"):
            edit.setText(value.isoformat())
        else:
            edit.setText(str(value))

    validator = _required_text if required else None
    return FieldEditor(edit, get_temporal, set_temporal, validator)


def _required_text(value: Any) -> str | None:
    return "此项为必填" if value == "" else None


def _path_validator(
    picker: FileInput | FolderInput,
    optional: bool,
) -> Callable[[Any], str | None]:
    """表单提交时检查路径。输入过程中只有输入框变色，不弹错。"""

    def validate(_value: Any) -> str | None:
        state = picker.state
        if state is PathState.SELECTED:
            return None
        if state is PathState.EMPTY:
            return None if optional else "此项为必填"
        return "路径不存在"

    return validate


def _choice_combo(
    pairs: list[tuple[str, Any]],
    *,
    current: Any,
    search: bool,
    optional: bool = False,
) -> QComboBox:
    """选项下拉。``search`` 时可以输入并按包含关系缩小列表。"""

    combo = QComboBox()
    if optional:
        combo.addItem("未设置", None)
    for label, data in pairs:
        combo.addItem(label, data)
    if search:
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        completer = QCompleter(combo.model(), combo)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        combo.setCompleter(completer)
    _select_choice(combo, None if current is None else str(getattr(current, "value", current)))
    return combo


def _select_choice(combo: QComboBox, text: str | None) -> None:
    if text is None:
        index = combo.findData(None)
        combo.setCurrentIndex(index if index >= 0 else (0 if combo.count() else -1))
        return
    index = combo.findText(text)
    if index >= 0:
        combo.setCurrentIndex(index)
        return
    combo.setCurrentText(text)
