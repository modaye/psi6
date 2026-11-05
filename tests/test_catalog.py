"""控件索引覆盖 ``psi6.ui.__all__``，参数取自真实构造函数。"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import psi6.ui as ui
from psi6.ui.catalog import catalog_json, components, find


def test_catalog_covers_every_public_name() -> None:
    listed = {component.name for component in components()}
    assert listed == set(ui.__all__)
    assert len(components()) == len(ui.__all__)


def test_every_component_has_usage_text() -> None:
    for component in components():
        assert component.summary, component.name
        assert component.use, component.name
        assert component.avoid, component.name
        assert component.module.startswith(("psi6.ui.", "psi6.schema")), component.name
        assert "._" not in component.module, component.name


def test_constructor_params_are_read_from_code() -> None:
    table = find("DataTable")
    names = {param.name for param in table.params}
    assert {"columns", "empty_title", "empty_hint"} <= names
    empty_title = next(param for param in table.params if param.name == "empty_title")
    assert empty_title.default == repr("暂无数据")
    assert empty_title.kind == "keyword_only"
    assert find("FileInput").import_line == "from psi6.ui.file_input import FileInput"
    assert find("PathState").module == "psi6.ui.file_input"
    assert find("Tone").module == "psi6.ui.tone"
    assert find("Tone").params == ()


def test_unknown_name_lists_alternatives() -> None:
    try:
        find("Nope")
    except KeyError as exc:
        message = exc.args[0]
    else:  # pragma: no cover - 只在实现坏掉时执行
        raise AssertionError("应当拒绝未知控件")
    assert "DataTable" in message
    assert "Nope" in message


def test_catalog_json_round_trips() -> None:
    payload = json.loads(catalog_json())
    assert {entry["name"] for entry in payload} == set(ui.__all__)
    table = next(entry for entry in payload if entry["name"] == "DataTable")
    assert table["kind"] == "widget"
    assert table["import"] == "from psi6.ui.data_table import DataTable"
    assert isinstance(table["params"], list)


def test_catalog_cli_emits_json() -> None:
    env = os.environ.copy()
    env["QT_QPA_PLATFORM"] = "offscreen"
    completed = subprocess.run(
        [sys.executable, "-m", "psi6", "catalog", "--json", "DataTable"],
        env=env,
        check=False,
        capture_output=True,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr
    entry = json.loads(completed.stdout.decode("utf-8"))
    assert entry["name"] == "DataTable"
    assert entry["summary"]
