"""由 Pydantic Model 生成表单，校验逻辑以模型为准。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from pydantic.fields import FieldInfo
from PySide6.QtWidgets import QFormLayout, QLabel, QVBoxLayout, QWidget

from psi6.schema import field_advanced, field_dir, field_file, field_secret, field_switch
from psi6.ui.collapsible import Collapsible
from psi6.ui.fields import build_field_editor, create_field_editor
from psi6.ui.form_model import (
    FieldBinding,
    FormError,
    ModelFormController,
    field_extra,
    format_field_error,
    is_optional,
    unwrap_annotation,
)

__all__ = [
    "FormError",
    "FormView",
    "create_field_editor",
    "field_advanced",
    "field_dir",
    "field_file",
    "field_secret",
    "field_switch",
    "format_field_error",
    "pydantic_form",
]


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
        self._controller = ModelFormController(model_type)
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
        seen_groups: set[tuple[bool, str]] = set()
        for name, field in model_type.model_fields.items():
            extra = field_extra(field)
            if extra.get("hidden"):
                self._controller.add_hidden(name, field)
                continue
            binding = self._add_binding(name, field, extra)
            label = field.description or name
            cell = QWidget()
            cell_layout = QVBoxLayout(cell)
            cell_layout.setContentsMargins(0, 0, 0, 0)
            cell_layout.setSpacing(2)
            cell_layout.addWidget(binding.widget)
            cell_layout.addWidget(binding.error_label)
            binding.error_label.hide()
            advanced = bool(extra.get("advanced"))
            target = advanced_form if advanced else main_form
            group = extra.get("group")
            if isinstance(group, str) and group and (advanced, group) not in seen_groups:
                seen_groups.add((advanced, group))
                heading = QLabel(group)
                heading.setObjectName("psi6FormGroup")
                target.addRow(heading)
            target.addRow(label, cell)
            if advanced:
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

        return self._controller.get_model()

    def set_model(self, model: BaseModel) -> None:
        """回填全部字段，期间挡住子控件信号。

        逐个 ``set_path`` 会让还没回填的字段被「即改即存」写成空。
        ``restore`` 是同一个方法，方便按「恢复会话」来读。
        """

        self._controller.set_model(model)

    def restore(self, model: BaseModel) -> None:
        """同 ``set_model``。回填不逐字段发信号。"""

        self.set_model(model)

    def _add_binding(self, name: str, field: FieldInfo, extra: dict[str, Any]) -> FieldBinding:
        error = QLabel()
        error.setObjectName("psi6Error")
        editor = build_field_editor(
            unwrap_annotation(field.annotation),
            field,
            extra,
            is_optional(field.annotation),
            name=name,
        )
        widget = editor.widget
        widget.setProperty("psi6Field", name)
        return self._controller.add(
            name,
            field,
            widget=widget,
            error_label=error,
            getter=editor.getter,
            setter=editor.setter,
            validator=editor.validator,
        )


def pydantic_form(
    model: type[BaseModel] | BaseModel,
    *,
    parent: QWidget | None = None,
) -> FormView:
    """由 Model 类型或实例生成表单。``Path`` 字段按 metadata 映射到文件/目录输入。"""

    if isinstance(model, BaseModel):
        return FormView(type(model), initial=model, parent=parent)
    return FormView(model, parent=parent)
