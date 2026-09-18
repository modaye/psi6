"""由 Pydantic 模型生成设置页：分组 + SettingRow，和 ConfigStore 同一份模型。"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ValidationError
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from psi6.ui.action_bar import ActionBar
from psi6.ui.buttons import primary_button
from psi6.ui.form import (
    FormError,
    _extra,
    _is_optional,
    _unwrap,
    create_field_editor,
    format_field_error,
)
from psi6.ui.section import Section
from psi6.ui.setting_row import SettingRow


class SettingsPage(QWidget):
    """设置页。``applied`` 给出通过校验的模型，由窗口去 ``save_config``。"""

    applied = Signal(object)

    def __init__(
        self,
        model_type: type[BaseModel],
        *,
        initial: BaseModel | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("psi6SettingsPage")
        self._model_type = model_type
        self._getters: dict[str, Callable[[], Any]] = {}
        self._setters: dict[str, Callable[[Any], None]] = {}
        self._errors: dict[str, QLabel] = {}
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)
        groups: dict[str, list[str]] = {}
        order: list[str] = []
        for name, field in model_type.model_fields.items():
            extra = _extra(field)
            if extra.get("hidden"):
                continue
            group = str(extra.get("group") or "设置")
            if group not in groups:
                groups[group] = []
                order.append(group)
            groups[group].append(name)

        seed: BaseModel | None
        if initial is not None:
            seed = initial
        else:
            try:
                seed = model_type()
            except ValidationError:
                seed = None
        values = seed.model_dump() if seed is not None else {}
        for group in order:
            section = Section(group)
            for name in groups[group]:
                field = model_type.model_fields[name]
                extra = _extra(field)
                title = field.description or name
                hint = str(extra.get("hint") or "")
                annotation = _unwrap(field.annotation)
                optional = _is_optional(field.annotation)
                error = QLabel(self)
                error.setObjectName("psi6Error")
                error.hide()
                self._errors[name] = error
                if annotation is bool and extra.get("kind") == "switch":
                    row = SettingRow(title, hint=hint, checked=bool(values.get(name)))
                    self._getters[name] = row.is_checked
                    self._setters[name] = row.set_checked
                    section.add_widget(row)
                    continue
                widget, getter, setter = create_field_editor(annotation, field, extra, optional)
                self._getters[name] = getter
                self._setters[name] = setter
                block = QWidget()
                block_layout = QVBoxLayout(block)
                block_layout.setContentsMargins(0, 0, 0, 0)
                block_layout.setSpacing(4)
                caption = QLabel(title)
                caption.setObjectName("psi6SettingTitle")
                block_layout.addWidget(caption)
                if hint:
                    note = QLabel(hint)
                    note.setObjectName("psi6Hint")
                    note.setWordWrap(True)
                    block_layout.addWidget(note)
                block_layout.addWidget(widget)
                block_layout.addWidget(error)
                section.add_widget(block)
                setter(values.get(name))
            root.addWidget(section)
        actions = ActionBar()
        apply_btn = primary_button("应用")
        apply_btn.setAccessibleName("应用设置")
        apply_btn.clicked.connect(self.apply)
        actions.add_right(apply_btn)
        root.addWidget(actions)
        root.addStretch()

    def get_model(self) -> BaseModel:
        """读取并校验。失败时在字段下显示错误。"""

        self._clear_errors()
        payload = {name: getter() for name, getter in self._getters.items()}
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
            message = next(iter(field_errors.values()), "设置无效")
            raise FormError(message, field_errors) from exc

    def set_model(self, model: BaseModel) -> None:
        data = model.model_dump()
        for name, setter in self._setters.items():
            if name in data:
                setter(data[name])
        self._clear_errors()

    def apply(self) -> BaseModel | None:
        """校验成功则发出 ``applied``。失败返回 ``None``。"""

        try:
            model = self.get_model()
        except FormError:
            return None
        self.applied.emit(model)
        return model

    def _show_errors(self, field_errors: dict[str, str]) -> None:
        for name, text in field_errors.items():
            label = self._errors.get(name)
            if label is None:
                continue
            label.setText(text)
            label.show()

    def _clear_errors(self) -> None:
        for label in self._errors.values():
            label.hide()
            label.setText("")


def pydantic_settings(
    model: type[BaseModel] | BaseModel,
    *,
    parent: QWidget | None = None,
) -> SettingsPage:
    """由模型生成设置页。实例作为初值。"""

    if isinstance(model, BaseModel):
        return SettingsPage(type(model), initial=model, parent=parent)
    return SettingsPage(model, parent=parent)
