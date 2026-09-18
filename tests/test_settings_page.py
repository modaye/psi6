"""Pydantic 设置页分组与校验。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field
from PySide6.QtWidgets import QLabel
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
    titles = [label.text() for label in page.findChildren(QLabel) if label.objectName() == "psi6SectionTitle"]
    assert titles == ["扫描", "外观"]
    model = page.get_model()
    assert model.recursive is True
    assert model.appearance == "light"
    applied = page.apply()
    assert isinstance(applied, Prefs)
