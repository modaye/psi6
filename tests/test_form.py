"""pydantic_form 字段映射与校验。"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
from pytestqt.qtbot import QtBot

from psi6.ui.collapsible import Collapsible
from psi6.ui.file_input import FolderInput
from psi6.ui.form import (
    FormError,
    field_advanced,
    field_dir,
    field_file,
    field_secret,
    field_switch,
    pydantic_form,
)


class Kind(StrEnum):
    A = "a"
    B = "b"


class Sample(BaseModel):
    title: str = Field(min_length=1, description="标题")
    count: int = Field(default=2, ge=0, le=10, description="数量")
    flag: bool = Field(default=True, description="启用")
    kind: Kind = Kind.A
    mode: Literal["fast", "safe"] = "safe"
    folder: Path = Field(json_schema_extra={"kind": "dir"}, description="目录")


def test_form_roundtrip(qtbot: QtBot, tmp_path: Path) -> None:
    view = pydantic_form(Sample(title="ok", folder=tmp_path))
    qtbot.addWidget(view)
    model = view.get_model()
    assert model.title == "ok"
    assert model.count == 2
    assert model.flag is True
    assert model.kind is Kind.A
    assert model.mode == "safe"
    assert model.folder == tmp_path


def test_form_required_error(qtbot: QtBot) -> None:
    view = pydantic_form(Sample)
    qtbot.addWidget(view)
    try:
        view.get_model()
    except FormError as exc:
        assert "title" in exc.field_errors or "folder" in exc.field_errors
    else:
        raise AssertionError("expected FormError")


def test_path_dir_uses_folder_input(qtbot: QtBot) -> None:
    view = pydantic_form(Sample)
    qtbot.addWidget(view)
    folder_widgets = view.findChildren(FolderInput)
    assert folder_widgets


class OptionalModel(BaseModel):
    note: str | None = None
    folder: Path | None = field_dir(default=None, description="可选目录")
    token: str = field_secret(default="", description="令牌")
    internal: str = Field(default="x", json_schema_extra={"hidden": True})


def test_optional_path_and_hidden(qtbot: QtBot) -> None:
    view = pydantic_form(OptionalModel)
    qtbot.addWidget(view)
    model = view.get_model()
    assert model.folder is None
    assert model.note is None
    assert model.internal == "x"
    assert view.findChildren(FolderInput)


def test_secret_echo_mode(qtbot: QtBot) -> None:
    from PySide6.QtWidgets import QLineEdit

    view = pydantic_form(OptionalModel)
    qtbot.addWidget(view)
    edits = [edit for edit in view.findChildren(QLineEdit) if edit.echoMode() == QLineEdit.EchoMode.Password]
    assert edits


class AdvancedModel(BaseModel):
    title: str = Field(min_length=1, description="标题")
    count: int = field_advanced(default=2, ge=0, le=10, description="数量")


def test_advanced_fields_are_collapsed(qtbot: QtBot) -> None:
    view = pydantic_form(AdvancedModel(title="ok"))
    qtbot.addWidget(view)
    panels = view.findChildren(Collapsible)
    assert panels
    assert not panels[0].is_expanded()
    model = view.get_model()
    assert model.count == 2
    panels[0].set_expanded(True)
    assert panels[0].is_expanded()


class SwitchParams(BaseModel):
    recursive: bool = field_switch(default=True, description="包含子目录", advanced=True)


def test_field_switch_in_advanced(qtbot: QtBot) -> None:
    from psi6.ui.switch import Switch

    view = pydantic_form(SwitchParams())
    qtbot.addWidget(view)
    assert view.findChildren(Switch)


class Stamp(BaseModel):
    when: datetime = datetime(2024, 1, 2, 3, 4)  # noqa: DTZ001
    day: date = date(2024, 5, 6)
    files: list[Path] = field_file(multiple=True, default_factory=list)


def test_form_datetime_and_file_list(qtbot: QtBot, tmp_path: Path) -> None:
    one = tmp_path / "a.txt"
    one.write_text("x", encoding="utf-8")
    stamp = datetime(2024, 1, 2, 3, 4)  # noqa: DTZ001
    view = pydantic_form(Stamp(when=stamp, day=date(2024, 5, 6), files=[one]))
    qtbot.addWidget(view)
    model = view.get_model()
    assert model.when == stamp
    assert model.day == date(2024, 5, 6)
    assert model.files == [one]

