"""主题检查命令：列表、JSON、导入自定义主题和稳定退出码。"""

from __future__ import annotations

import json

import pytest

from psi6.theme.cli import main


def test_theme_cli_lists_builtin_themes(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    names = {row["name"] for row in rows}
    assert {"light", "dark", "auto", "obsidian", "brass"} <= names
    assert next(row for row in rows if row["name"] == "compact-dark")["style"] == "compact"


def test_theme_cli_reports_tokens_as_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["obsidian", "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["name"] == "obsidian"
    assert report["base"] == "dark"
    assert report["tokens"]["color_bg"] == "#0d0e14"
    assert report["tokens"]["color_pressed"]
    assert report["notes"] == []


def test_theme_cli_imports_theme_class(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["psi6.theme.builtin:Brass"]) == 0
    output = capsys.readouterr().out
    assert "base=light" in output
    assert "color_primary: #6b542e" in output


def test_theme_cli_check_and_unknown_theme(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--check"]) == 0
    assert "无对比度问题" in capsys.readouterr().out
    assert main(["granite"]) == 2
    assert "未知主题" in capsys.readouterr().err
    assert main(["--bad-flag"]) == 2
    assert "未知参数" in capsys.readouterr().err


def test_theme_cli_check_returns_one_for_diagnostics(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("psi6.theme.cli.contrast_notes", lambda _tokens: ["对比度不足"])
    assert main(["--check", "light"]) == 1
    assert "对比度不足" in capsys.readouterr().out
