"""SKILL.md 禁令的 AST 检查器。

检查业务代码里绕过框架的写法：直接创建 ``QApplication``、手写 ``QThread``、
直接弹 ``QFileDialog``、页面私有 QSS，以及从 ``psi6`` 私有模块导入。
不运行代码，也不导入 Qt。

命令行：``python -m psi6 check [目录或文件 ...]``。有发现时返回 2。
"""

from __future__ import annotations

import ast
import sys
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "Finding",
    "check_file",
    "check_paths",
    "check_source",
    "format_findings",
    "main",
]

_RULES: dict[str, tuple[str, str]] = {
    "PSI000": ("文件无法解析", "先修正语法错误，检查器才能继续。"),
    "PSI001": (
        "不要在业务代码里直接创建 QApplication",
        "用 App(name) 创建应用，再 app.run(window)。",
    ),
    "PSI002": (
        "不要手写 QThread 或在线程上调用 terminate",
        "把工作函数交给 app.runner.submit，取消用 TaskHandle.cancel。",
    ),
    "PSI003": (
        "业务代码不要直接调用 QFileDialog",
        "用 FileInput / FolderInput，或 pydantic_form 的 field_file / field_dir。",
    ),
    "PSI004": (
        "不要在页面里写内联 QSS",
        "颜色和尺寸走主题 token；控件外观用构造参数或子类钩子。",
    ),
    "PSI005": (
        "不要从 psi6 的私有模块导入",
        "从 psi6 根包或 psi6.ui 的公开模块导入。",
    ),
    "PSI006": (
        "不要用 processEvents 假装异步",
        "耗时工作交给 app.runner.submit，让 Qt 自己处理事件。",
    ),
    "PSI007": (
        "路径无法检查",
        "传入存在的目录或 .py 文件；目录会递归检查。",
    ),
}

_QT_WIDGETS = {"QApplication": "PSI001", "QFileDialog": "PSI003"}
_QT_CORE = {"QThread": "PSI002"}
# 查询线程身份不算手写线程。
_QTHREAD_QUERIES = {"currentThread", "currentThreadId", "idealThreadCount"}


@dataclass(frozen=True, slots=True, order=True)
class Finding:
    """一条检查结果。``line`` 和 ``column`` 从 1 开始。"""

    path: str
    line: int
    column: int
    rule: str
    message: str
    hint: str


def _finding(node: ast.AST, rule: str, *, path: str) -> Finding:
    message, hint = _RULES[rule]
    return Finding(
        path=path,
        line=getattr(node, "lineno", 1),
        column=getattr(node, "col_offset", 0) + 1,
        rule=rule,
        message=message,
        hint=hint,
    )


_Aliases = dict[str, str]


def _import_aliases(tree: ast.AST) -> _Aliases:
    """记录 ``as`` 导入的本地名字，检查时按原名字判断。"""

    aliases: _Aliases = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.asname:
                    aliases[alias.asname] = alias.name
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname:
                    aliases[alias.asname] = alias.name.rsplit(".", 1)[-1]
    return aliases


def _resolved_name(node: ast.AST, aliases: _Aliases) -> str:
    """把 ``QA`` 或 ``W.QApplication`` 还原成导入时的全名。"""

    if isinstance(node, ast.Name):
        return aliases.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        base = _resolved_name(node.value, aliases)
        return f"{base}.{node.attr}" if base else node.attr
    if isinstance(node, ast.Call):
        return _resolved_name(node.func, aliases)
    return ""


def _root_name(node: ast.AST, aliases: _Aliases) -> str:
    name = _resolved_name(node, aliases)
    return name.split(".", 1)[0] if name else ""


def _last_name(node: ast.AST, aliases: _Aliases) -> str:
    name = _resolved_name(node, aliases)
    return name.rsplit(".", 1)[-1] if name else ""


def _private_imports(node: ast.ImportFrom | ast.Import) -> Iterator[ast.AST]:
    """只找从 ``psi6`` 私有模块或私有名字进来的导入。"""

    if (
        isinstance(node, ast.ImportFrom)
        and node.module
        and (node.module == "psi6" or node.module.startswith("psi6."))
    ):
        if "._" in node.module:
            yield node
        yield from (alias for alias in node.names if alias.name.startswith("_"))
    elif isinstance(node, ast.Import):
        for alias in node.names:
            if alias.name.startswith("psi6.") and "._" in alias.name:
                yield alias


def check_source(source: str, *, filename: str = "<string>") -> list[Finding]:
    """检查一段源码。语法错误也作为一条 ``PSI000`` 返回。"""

    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError as exc:
        return [
            Finding(
                path=filename,
                line=exc.lineno or 1,
                column=exc.offset or 1,
                rule="PSI000",
                message=f"{_RULES['PSI000'][0]}：{exc.msg}",
                hint=_RULES["PSI000"][1],
            )
        ]

    findings: list[Finding] = []
    aliases = _import_aliases(tree)
    thread_classes = {
        node.name.lower()
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
        and any(_last_name(base, aliases) == "QThread" for base in node.bases)
    }
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for hit in _private_imports(node):
                findings.append(_finding(hit, "PSI005", path=filename))
            continue

        if isinstance(node, ast.ClassDef):
            if any(_last_name(base, aliases) == "QThread" for base in node.bases):
                findings.append(_finding(node, "PSI002", path=filename))
            continue

        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            called = _last_name(node.func, aliases)
            if called == "QApplication":
                findings.append(_finding(node, "PSI001", path=filename))
            elif called == "QThread":
                findings.append(_finding(node, "PSI002", path=filename))
            elif called == "QFileDialog":
                findings.append(_finding(node, "PSI003", path=filename))
            continue
        if not isinstance(node.func, ast.Attribute):
            continue
        attr = _last_name(node.func, aliases)
        owner = _root_name(node.func.value, aliases)
        receiver = _last_name(node.func.value, aliases)
        is_file_dialog = "QFileDialog" in {owner, receiver}
        is_thread = "QThread" in {owner, receiver}
        known_thread = owner.lower() in thread_classes or receiver.lower() in thread_classes
        if attr == "processEvents":
            findings.append(_finding(node, "PSI006", path=filename))
        elif attr == "setStyleSheet":
            findings.append(_finding(node, "PSI004", path=filename))
        elif is_file_dialog:
            findings.append(_finding(node, "PSI003", path=filename))
        elif (is_thread and attr not in _QTHREAD_QUERIES) or (attr == "terminate" and known_thread):
            findings.append(_finding(node, "PSI002", path=filename))
        elif attr in {"QApplication", "QFileDialog", "QThread"}:
            # 通过 ``QtWidgets.QApplication`` 这类限定名调用时，根名字是模块名。
            rule = _QT_WIDGETS.get(attr) or _QT_CORE[attr]
            findings.append(_finding(node, rule, path=filename))
    return sorted(findings)


def check_file(path: Path | str) -> list[Finding]:
    """检查一个 ``.py`` 文件。"""

    file_path = Path(path)
    try:
        source = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [
            Finding(
                path=str(file_path),
                line=1,
                column=1,
                rule="PSI000",
                message=f"{_RULES['PSI000'][0]}：{exc}",
                hint=_RULES["PSI000"][1],
            )
        ]
    return check_source(source, filename=str(file_path))


def _iter_python_files(root: Path, excluded: tuple[Path, ...]) -> Iterator[Path]:
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        if any(part.startswith(".") for part in path.relative_to(root).parts):
            continue
        if any(path == item or item in path.parents for item in excluded):
            continue
        yield path


def _path_finding(root: Path, message: str) -> Finding:
    return Finding(
        path=str(root),
        line=1,
        column=1,
        rule="PSI007",
        message=f"{_RULES['PSI007'][0]}：{message}",
        hint=_RULES["PSI007"][1],
    )


def check_paths(
    paths: Iterable[str | Path] = (),
    *,
    exclude: Iterable[str | Path] = (),
) -> list[Finding]:
    """递归检查目录（或单个文件）。``exclude`` 会跳过指定目录及其子目录。

    不存在或不是 ``.py`` 的输入也记为一条 ``PSI007``，避免命令行静默放过。
    """

    roots = [Path(item) for item in paths] or [Path.cwd()]
    excluded = tuple(Path(item).resolve() for item in exclude)
    findings: list[Finding] = []
    for root in roots:
        resolved = root.resolve()
        if any(resolved == item or item in resolved.parents for item in excluded):
            continue
        if not resolved.exists():
            findings.append(_path_finding(root, f"路径不存在：{root}"))
            continue
        if resolved.is_dir():
            for path in _iter_python_files(resolved, excluded):
                findings.extend(check_file(path))
        elif resolved.suffix.lower() == ".py":
            findings.extend(check_file(resolved))
        else:
            findings.append(_path_finding(root, f"不是 .py 文件：{root}"))
    return sorted(findings)


def format_findings(findings: Iterable[Finding]) -> str:
    """把发现格式化成一行一条，附下一行的修改建议。"""

    lines: list[str] = []
    for item in findings:
        lines.append(f"{item.path}:{item.line}:{item.column} {item.rule} {item.message}")
        lines.append(f"  → {item.hint}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """``python -m psi6 check [目录或文件 ...] [--exclude 目录 ...]``。"""

    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    args = list(sys.argv[1:] if argv is None else argv)
    paths: list[str] = []
    exclude: list[str] = []
    target = paths
    for arg in args:
        if arg == "--exclude":
            target = exclude
            continue
        if arg.startswith("--exclude="):
            exclude.append(arg.split("=", 1)[1])
            continue
        target.append(arg)
    findings = check_paths(paths, exclude=exclude)
    if not findings:
        sys.stdout.write("psi6: 未发现规范问题\n")
        return 0
    sys.stdout.write(format_findings(findings) + "\n")
    sys.stderr.write(f"psi6: {len(findings)} 处规范问题\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
