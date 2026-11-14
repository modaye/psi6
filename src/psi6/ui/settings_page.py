"""由 Pydantic 模型生成设置页：分组 + SettingRow，和 ConfigStore 同一份模型。"""

from __future__ import annotations

from pydantic import BaseModel, ValidationError
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from psi6.ui.action_bar import ActionBar
from psi6.ui.buttons import primary_button
from psi6.ui.fields import build_field_editor, switch_row_supported
from psi6.ui.file_input import FileInput, FolderInput
from psi6.ui.form_model import (
    FormError,
    ModelFormController,
    field_extra,
    is_optional,
    unwrap_annotation,
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
        self._controller = ModelFormController(model_type, error_message="设置无效")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)
        groups: dict[str, list[str]] = {}
        order: list[str] = []
        for name, field in model_type.model_fields.items():
            extra = field_extra(field)
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
        for name, field in model_type.model_fields.items():
            if field_extra(field).get("hidden"):
                self._controller.add_hidden(name, field, values.get(name))
        for group in order:
            section = Section(group)
            section.setMaximumWidth(720)
            for name in groups[group]:
                field = model_type.model_fields[name]
                extra = field_extra(field)
                title = field.description or name
                hint = str(extra.get("hint") or "")
                annotation = unwrap_annotation(field.annotation)
                optional = is_optional(field.annotation)
                error = QLabel(self)
                error.setObjectName("psi6Error")
                error.hide()
                if switch_row_supported(annotation, extra, optional):
                    row = SettingRow(title, hint=hint, checked=bool(values.get(name)))
                    self._controller.add(
                        name,
                        field,
                        widget=row,
                        error_label=error,
                        getter=row.is_checked,
                        setter=row.set_checked,
                    )
                    section.add_widget(row)
                    continue
                editor = build_field_editor(annotation, field, extra, optional, name=name)
                widget = editor.widget
                widget.setProperty("psi6Field", name)
                if isinstance(widget, (FileInput, FolderInput)):
                    widget.setMaximumWidth(480)
                else:
                    widget.setMaximumWidth(320)
                self._controller.add(
                    name,
                    field,
                    widget=widget,
                    error_label=error,
                    getter=editor.getter,
                    setter=editor.setter,
                    validator=editor.validator,
                )
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
                editor.setter(values.get(name))
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

        return self._controller.get_model()

    def set_model(self, model: BaseModel) -> None:
        """回填全部字段，期间挡住控件信号。"""

        self._controller.set_model(model)

    def apply(self) -> BaseModel | None:
        """校验成功则发出 ``applied``。失败返回 ``None``。"""

        try:
            model = self.get_model()
        except FormError:
            return None
        self.applied.emit(model)
        return model


def pydantic_settings(
    model: type[BaseModel] | BaseModel,
    *,
    parent: QWidget | None = None,
) -> SettingsPage:
    """由模型生成设置页。实例作为初值。"""

    if isinstance(model, BaseModel):
        return SettingsPage(type(model), initial=model, parent=parent)
    return SettingsPage(model, parent=parent)
