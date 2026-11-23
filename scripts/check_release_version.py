"""核对 Git 标签和 pyproject 版本。发布工作流在构建之前调用。

标签 ``v0.7.0`` 必须对应 ``version = "0.7.0"``。从普通分支手动触发时拒绝发布，
避免绕过标签把当前工作区的版本推进 PyPI。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def project_version(root: Path | None = None) -> str:
    """读取 ``[project].version``。不引入 TOML 依赖，只认这一行。"""

    text = (root or ROOT).joinpath("pyproject.toml").read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("version = "):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("pyproject.toml 里没有 version")


def tag_version(ref: str) -> str | None:
    """``refs/tags/v0.7.0`` 得到 ``0.7.0``。不是标签时返回 None。"""

    prefix = "refs/tags/"
    if not ref.startswith(prefix):
        return None
    tag = ref.removeprefix(prefix)
    if tag.startswith("v"):
        tag = tag[1:]
    return tag


def check(ref: str, event: str, version: str) -> str | None:
    """一致时返回 None。否则返回要打印的错误。"""

    tagged = tag_version(ref)
    if tagged is not None:
        if tagged != version:
            return f"标签 v{tagged} 与 pyproject 版本 {version} 不一致"
        return None
    if event == "workflow_dispatch":
        return "手动发布必须从与 pyproject 版本一致的 v* 标签触发，不能从分支直接发布"
    if ref:
        return f"发布只能由 v* 标签触发，当前 ref 是 {ref}"
    return None


def main() -> int:
    """给 GitHub Actions 用。本地没有 ``GITHUB_REF`` 时只打印版本。"""

    version = project_version()
    ref = os.environ.get("GITHUB_REF", "")
    event = os.environ.get("GITHUB_EVENT_NAME", "")
    problem = check(ref, event, version)
    if problem:
        print(problem, file=sys.stderr)
        return 1
    print(f"version {version} ref {ref or '(local)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
