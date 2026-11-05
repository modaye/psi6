"""Pydantic 设置页分组与校验。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field
from PySide6.QtWidgets import QLabel, QLineEdit
from pytestqt.qtbot import QtBot

from psi6.ui.form import field_switch
from psi6.ui.setting_row import SettingRow
from psi6.ui.settings_page import pydantic_settings


class Prefs(BaseModel):
    recursive: bool = field_switch(default=True, description="包含子目录", group="扫描")
    appearance: Literal["light", "dark"] = Field(
        default="light",
        description="外观",
        json_schema_extra={"group": "外观"},
    )


def test_settings_page_groups_and_roundtrip(qtbot: QtBot) -> None:
    page = pydantic_settings(Prefs())
    qtbot.addWidget(page)
    assert page.findChildren(SettingRow)
    titles = [
        label.text()
        for label in page.findChildren(QLabel)
        if label.objectName() == "psi6SectionTitle"
    ]
    assert titles == ["扫描", "外观"]
    model = page.get_model()
    assert model.recursive is True
    assert model.appearance == "light"
    applied = page.apply()
    assert isinstance(applied, Prefs)


class OptionalPrefs(BaseModel):
    notify: bool | None = field_switch(default=None, description="通知", group="提醒")


def test_optional_switch_keeps_none(qtbot: QtBot) -> None:
    page = pydantic_settings(OptionalPrefs())
    qtbot.addWidget(page)
    assert page.findChildren(SettingRow) == []
    assert page.get_model().notify is None
    page.set_model(OptionalPrefs(notify=True))
    assert page.get_model().notify is True


def test_set_model_blocks_switch_signals(qtbot: QtBot) -> None:
    page = pydantic_settings(Prefs(recursive=False))
    qtbot.addWidget(page)
    row = page.findChild(SettingRow)
    assert row is not None
    hits: list[bool] = []
    row.toggled.connect(hits.append)
    page.set_model(Prefs(recursive=True))
    assert hits == []
    assert page.get_model().recursive is True


class LimitedPrefs(BaseModel):
    count: int = Field(
        default=1,
        gt=0,
        le=10,
        description="数量",
        json_schema_extra={"group": "扫描"},
    )


def test_settings_page_shows_field_error(qtbot: QtBot) -> None:
    page = pydantic_settings(LimitedPrefs())
    qtbot.addWidget(page)
    page.show()
    edit = next(
        item for item in page.findChildren(QLineEdit) if item.property("psi6NumberKind") == "int"
    )
    edit.setText("0")
    assert page.apply() is None
    shown = [
        label.text()
        for label in page.findChildren(QLabel)
        if label.objectName() == "psi6Error" and label.isVisible()
    ]
    assert shown == ["数值过小"]


def test_settings_page_keeps_hidden_field(qtbot: QtBot) -> None:
    class HiddenPrefs(BaseModel):
        visible: str = "a"
        internal: int = Field(default=5, json_schema_extra={"hidden": True})

    page = pydantic_settings(HiddenPrefs())
    qtbot.addWidget(page)
    assert page.get_model().internal == 5
    page.set_model(HiddenPrefs(visible="b", internal=8))
    model = page.get_model()
    assert model.visible == "b"
    assert model.internal == 8
