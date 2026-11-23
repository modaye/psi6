"""检查 wheel 和 sdist 里有没有类型标记、图标和示例。

发布和 CI 在 ``uv build`` 之后调用。测试用临时包验证判定本身。
"""

from __future__ import annotations

import sys
import tarfile
import zipfile
from pathlib import Path

WHEEL_MARKERS = (
    "psi6/py.typed",
    "psi6/icons/svg/search.svg",
    "psi6/examples/minimal.py",
    "psi6/ui/data_table.py",
)
SDIST_MARKERS = (
    "pyproject.toml",
    "src/psi6/py.typed",
    "src/psi6/icons/svg/search.svg",
    "src/psi6/__init__.py",
)


def _missing(names: list[str], markers: tuple[str, ...]) -> list[str]:
    normalized = [name.replace("\\", "/") for name in names]
    missing: list[str] = []
    for marker in markers:
        if not any(name == marker or name.endswith("/" + marker) for name in normalized):
            missing.append(marker)
    return missing


def wheel_members(path: Path) -> list[str]:
    """读取 wheel 内的路径。"""

    with zipfile.ZipFile(path) as archive:
        return archive.namelist()


def sdist_members(path: Path) -> list[str]:
    """读取 sdist 内的路径。"""

    with tarfile.open(path) as archive:
        return archive.getnames()


def require_archive(path: Path, markers: tuple[str, ...], members: list[str]) -> None:
    """缺文件时抛出带清单的 ``SystemExit`` 信息。"""

    missing = _missing(members, markers)
    if missing:
        joined = ", ".join(missing)
        raise SystemExit(f"{path.name} 缺少 {joined}")


def main(argv: list[str] | None = None) -> int:
    """检查 ``dist/`` 里唯一的 wheel 和 sdist。"""

    root = Path(argv[0]) if argv else Path("dist")
    wheels = sorted(root.glob("psi6-*.whl"))
    sdists = sorted(root.glob("psi6-*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        print(
            f"期望各一个 wheel 和 sdist，实际 wheel={len(wheels)} sdist={len(sdists)}",
            file=sys.stderr,
        )
        return 1
    require_archive(wheels[0], WHEEL_MARKERS, wheel_members(wheels[0]))
    require_archive(sdists[0], SDIST_MARKERS, sdist_members(sdists[0]))
    print(f"ok {wheels[0].name} {sdists[0].name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
