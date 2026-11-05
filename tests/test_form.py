"""pydantic_form 字段映射与校验。"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from enum import StrEnum
from pathlib import Path
from typing import Literal

import pytest
from pydantic import BaseModel, Field
from pytestqt.qtbot import QtBot

from psi6.ui.collapsible import Collapsible
from psi6.ui.file_input import FileInput, FolderInput
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


def test_restore_does_not_emit_path_changes(qtbot: QtBot, tmp_path: Path) -> None:
    other = tmp_path / "other"
    other.mkdir()

    class TwoFolders(BaseModel):
        left: Path = Field(json_schema_extra={"kind": "dir"}, description="左")
        right: Path = Field(json_schema_extra={"kind": "dir"}, description="右")

    view = pydantic_form(TwoFolders)
    qtbot.addWidget(view)
    hits: list[object] = []
    for picker in view.findChildren(FolderInput):
        picker.path_changed.connect(hits.append)
    view.restore(TwoFolders(left=tmp_path, right=other))
    assert hits == []
    model = view.get_model()
    assert model.left == tmp_path
    assert model.right == other


def test_form_group_and_field_error_stay_on_the_field(qtbot: QtBot) -> None:
    from PySide6.QtWidgets import QLabel, QLineEdit

    class Limited(BaseModel):
        count: int = Field(
            default=1, gt=0, le=10, description="数量", json_schema_extra={"group": "扫描"}
        )

    view = pydantic_form(Limited)
    qtbot.addWidget(view)
    view.show()
    groups = [
        label.text() for label in view.findChildren(QLabel) if label.objectName() == "psi6FormGroup"
    ]
    assert groups == ["扫描"]
    edit = next(
        item for item in view.findChildren(QLineEdit) if item.property("psi6NumberKind") == "int"
    )
    edit.setText("0")
    with pytest.raises(FormError):
        view.get_model()
    shown = [
        label.text()
        for label in view.findChildren(QLabel)
        if label.objectName() == "psi6Error" and label.isVisible()
    ]
    assert shown == ["数值过小"]


def test_searchable_choice_filters_by_contains(qtbot: QtBot) -> None:
    from PySide6.QtWidgets import QComboBox

    class Choice(BaseModel):
        pace: Literal["alpha", "beta", "gamma"] = Field(
            default="alpha",
            json_schema_extra={"search": True},
        )

    view = pydantic_form(Choice)
    qtbot.addWidget(view)
    combo = view.findChild(QComboBox)
    assert combo is not None
    assert combo.isEditable()
    completer = combo.completer()
    assert completer is not None
    completer.setCompletionPrefix("be")
    assert completer.completionCount() == 1


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
    edits = [
        edit
        for edit in view.findChildren(QLineEdit)
        if edit.echoMode() == QLineEdit.EchoMode.Password
    ]
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
    when: datetime = datetime(2024, 1, 2, 3, 4)
    day: date = date(2024, 5, 6)
    files: list[Path] = field_file(multiple=True, default_factory=list)


def test_form_datetime_and_file_list(qtbot: QtBot, tmp_path: Path) -> None:
    one = tmp_path / "a.txt"
    one.write_text("x", encoding="utf-8")
    stamp = datetime(2024, 1, 2, 3, 4)
    view = pydantic_form(Stamp(when=stamp, day=date(2024, 5, 6), files=[one]))
    qtbot.addWidget(view)
    model = view.get_model()
    assert model.when == stamp
    assert model.day == date(2024, 5, 6)
    assert model.files == [one]


class OptionalScalars(BaseModel):
    flag: bool | None = None
    count: int | None = None
    ratio: float | None = None


def test_optional_scalars_keep_none(qtbot: QtBot) -> None:
    view = pydantic_form(OptionalScalars)
    qtbot.addWidget(view)
    model = view.get_model()
    assert model.flag is None
    assert model.count is None
    assert model.ratio is None


def test_optional_scalars_round_trip_values(qtbot: QtBot) -> None:
    view = pydantic_form(OptionalScalars(flag=True, count=3, ratio=1.5))
    qtbot.addWidget(view)
    model = view.get_model()
    assert model.flag is True
    assert model.count == 3
    assert model.ratio == 1.5


def test_default_factory_seeds_the_editor(qtbot: QtBot, tmp_path: Path) -> None:
    seed = tmp_path / "seed.txt"
    seed.write_text("x", encoding="utf-8")

    class FactoryPaths(BaseModel):
        files: list[Path] = Field(default_factory=lambda: [seed])

    view = pydantic_form(FactoryPaths)
    qtbot.addWidget(view)
    assert view.get_model().files == [seed]


def test_required_number_does_not_invent_zero(qtbot: QtBot) -> None:
    class Required(BaseModel):
        count: int

    view = pydantic_form(Required)
    qtbot.addWidget(view)
    with pytest.raises(FormError) as info:
        view.get_model()
    assert info.value.field_errors["count"] == "此项为必填"


def test_required_nullable_number_accepts_empty(qtbot: QtBot) -> None:
    class Nullable(BaseModel):
        count: int | None
        when: datetime | None

    view = pydantic_form(Nullable)
    qtbot.addWidget(view)
    model = view.get_model()
    assert model.count is None
    assert model.when is None


def test_large_int_and_float_precision_round_trip(qtbot: QtBot) -> None:
    class Numbers(BaseModel):
        total: int = Field(default=10_000_000_000, ge=10_000_000_000)
        ratio: float = 0.123456789

    view = pydantic_form(Numbers)
    qtbot.addWidget(view)
    model = view.get_model()
    assert model.total == 10_000_000_000
    assert model.ratio == 0.123456789


def test_required_datetime_is_not_now(qtbot: QtBot) -> None:
    class Stamp(BaseModel):
        when: datetime

    view = pydantic_form(Stamp)
    qtbot.addWidget(view)
    with pytest.raises(FormError) as info:
        view.get_model()
    assert info.value.field_errors["when"] == "此项为必填"


class OptionalChoices(BaseModel):
    kind: Kind | None = None
    mode: Literal["fast", "safe"] | None = None


def test_optional_enum_and_literal_keep_none(qtbot: QtBot) -> None:
    view = pydantic_form(OptionalChoices)
    qtbot.addWidget(view)
    assert view.get_model().kind is None
    view.restore(OptionalChoices(kind=Kind.B, mode="fast"))
    model = view.get_model()
    assert model.kind is Kind.B
    assert model.mode == "fast"
    view.restore(OptionalChoices())
    model = view.get_model()
    assert model.kind is None
    assert model.mode is None


def test_optional_temporal_round_trip_keeps_precision(qtbot: QtBot) -> None:
    class OptionalStamp(BaseModel):
        when: datetime | None = None
        day: date | None = None
        clock: time | None = None

    view = pydantic_form(OptionalStamp)
    qtbot.addWidget(view)
    assert view.get_model().when is None
    moment = datetime(2024, 6, 7, 8, 9, 10, 123456, tzinfo=timezone(timedelta(hours=8)))
    day = date(2024, 6, 7)
    clock = time(8, 9, 10, 123456, tzinfo=timezone(timedelta(hours=8)))
    view.restore(OptionalStamp(when=moment, day=day, clock=clock))
    model = view.get_model()
    assert model.when == moment
    assert model.day == day
    assert model.clock == clock


def test_hidden_field_keeps_value_after_restore(qtbot: QtBot) -> None:
    class Hidden(BaseModel):
        visible: str = "a"
        secret_id: int = Field(default=3, json_schema_extra={"hidden": True})

    view = pydantic_form(Hidden())
    qtbot.addWidget(view)
    assert view.get_model().secret_id == 3
    view.restore(Hidden(visible="b", secret_id=9))
    model = view.get_model()
    assert model.visible == "b"
    assert model.secret_id == 9


def test_unsupported_annotation_is_rejected_loudly() -> None:
    class Nested(BaseModel):
        tags: list[str] = Field(default_factory=list)

    with pytest.raises(TypeError) as info:
        pydantic_form(Nested)
    assert "tags" in str(info.value)
    assert "list[str]" in str(info.value)


def test_missing_path_is_a_field_error(qtbot: QtBot, tmp_path: Path) -> None:
    class NeedsFile(BaseModel):
        source: Path

    view = pydantic_form(NeedsFile)
    qtbot.addWidget(view)
    picker = view.findChild(FileInput)
    assert picker is not None
    picker.set_path(tmp_path / "missing.txt")
    with pytest.raises(FormError) as info:
        view.get_model()
    assert info.value.field_errors["source"] == "路径不存在"
