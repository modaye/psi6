"""把 Pydantic 模型持久化到用户目录。"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

_BAD_COMPONENT = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "CONIN$",
    "CONOUT$",
    "CLOCK$",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
    "COM¹",
    "COM²",
    "COM³",
    "LPT¹",
    "LPT²",
    "LPT³",
}
_logger = logging.getLogger("psi6.runtime.config")


def _component(value: str, *, label: str) -> str:
    """把用户传入的名字限制成单层目录或文件名，挡住 ``..`` 和分隔符。"""

    cleaned = _BAD_COMPONENT.sub("-", str(value).strip()).strip(". ")
    if not cleaned or cleaned in {".", ".."}:
        raise ValueError(f"{label} 不能为空，也不能指向上级目录")
    if cleaned.split(".", 1)[0].upper() in _RESERVED_NAMES:
        raise ValueError(f"{label} 不能使用系统保留名：{cleaned}")
    return cleaned


class ConfigStore:
    """把 ``BaseModel`` 存到 ``~/.psi6/<app_name>/config.json``。

    文件是明文 JSON，只适合窗口位置、上次目录这类普通设置；密码、令牌等
    敏感值不要放进来，改用系统钥匙串。
    """

    def __init__(self, root: Path | None = None) -> None:
        """``root`` 仅测试注入；默认使用用户主目录下的 ``.psi6``。"""

        self._root = root or Path.home() / ".psi6"

    def path_for(self, app_name: str) -> Path:
        """返回指定应用的配置文件路径。"""

        return self._root / _component(app_name, label="app_name") / "config.json"

    def data_path(self, app_name: str, filename: str) -> Path:
        """应用数据目录下的任意文件。"""

        return (
            self._root
            / _component(app_name, label="app_name")
            / _component(filename, label="filename")
        )

    def load(
        self,
        model_type: type[T],
        *,
        app_name: str,
        migrate: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    ) -> T:
        """读取配置；文件不存在或损坏时备份后返回模型默认值。

        ``migrate`` 在校验之前改写 JSON 对象，用来把旧文件升到当前模型。
        迁移抛错或结果仍对不上模型时，同样备份并退回默认值，应用仍能启动。
        """

        path = self.path_for(app_name)
        if not path.is_file():
            return model_type()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("配置必须是 JSON 对象")
            if migrate is not None:
                data = migrate(data)
                if not isinstance(data, dict):
                    raise ValueError("配置迁移必须返回对象")
            return model_type.model_validate(data)
        except Exception as exc:
            backup = self._backup(path)
            _warn_fallback(path, exc, backup)
            return model_type()

    def save(self, model: BaseModel, *, app_name: str) -> None:
        """以 JSON 写入配置文件。先写临时文件，再原子替换。"""

        path = self.path_for(app_name)
        _replace_text(path, json.dumps(model.model_dump(mode="json"), ensure_ascii=False, indent=2))

    def load_data(
        self,
        app_name: str,
        filename: str,
        *,
        migrate: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    ) -> dict[str, Any] | None:
        """读取任意 JSON 对象；缺失或损坏时返回 ``None``。

        ``migrate`` 与 ``load`` 相同，用在不是 Pydantic 模型的状态文件上。
        """

        path = self.data_path(app_name, filename)
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            backup = self._backup(path)
            _warn_fallback(path, exc, backup)
            return None
        if not isinstance(data, dict):
            return None
        if migrate is None:
            return data
        try:
            migrated = migrate(data)
        except Exception as exc:
            backup = self._backup(path)
            _warn_fallback(path, exc, backup)
            return None
        if not isinstance(migrated, dict):
            backup = self._backup(path)
            _warn_fallback(path, ValueError("配置迁移必须返回对象"), backup)
            return None
        return migrated

    def save_data(self, app_name: str, filename: str, payload: Mapping[str, Any]) -> None:
        """写入任意 JSON 对象。先写临时文件，再原子替换。"""

        path = self.data_path(app_name, filename)
        _replace_text(path, json.dumps(dict(payload), ensure_ascii=False, indent=2))

    def _backup(self, path: Path) -> Path | None:
        bak = path.with_name(path.name + ".bak")
        try:
            shutil.copy2(path, bak)
        except OSError:
            return None
        return bak


def _warn_fallback(path: Path, exc: BaseException, backup: Path | None) -> None:
    if backup is None:
        _logger.warning("读取 %s 失败（%s），备份也失败；使用默认值", path, exc)
        return
    _logger.warning("读取 %s 失败（%s），已备份到 %s；使用默认值", path, exc, backup)


def _fsync_directory(folder: Path) -> None:
    """``os.replace`` 只保证文件内容落盘，目录项在 POSIX 上还要单独同步。"""

    if os.name == "nt":
        return
    try:
        fd = os.open(folder, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def _replace_text(path: Path, text: str) -> None:
    """写入同目录唯一临时文件，再用 ``os.replace`` 换上。

    固定临时名会让两个进程同时保存时互相覆盖，这里用 ``mkstemp``
    保证每次写入互不干扰，失败时原来的文件保持不动。
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


class ConfigMigrations:
    """按整数版本把旧 JSON 升到当前模型。

    文件里没有 ``version`` 时从 0 开始。``add(n, step)`` 把版本 ``n`` 升到 ``n + 1``，
    版本号由这里写回，步骤函数不必自己加一。没有下一步时停住，剩下的交给模型校验。
    传给 ``ConfigStore.load(..., migrate=migrations)`` 即可，本类可以直接当函数调用。
    """

    def __init__(self, *, version_key: str = "version") -> None:
        key = str(version_key).strip()
        if not key:
            raise ValueError("version_key 不能为空")
        self._version_key = key
        self._steps: dict[int, Callable[[dict[str, Any]], dict[str, Any]]] = {}

    def add(
        self,
        from_version: int,
        step: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> None:
        """登记从 ``from_version`` 升到下一版的一步。同一版本不能登记两次。"""

        version = int(from_version)
        if version < 0:
            raise ValueError("版本不能为负")
        if step is None:
            raise ValueError("迁移步骤不能为空")
        if version in self._steps:
            raise ValueError(f"版本 {version} 已经有迁移")
        self._steps[version] = step

    def __call__(self, data: dict[str, Any]) -> dict[str, Any]:
        """按已登记的步骤前进，直到没有下一步。"""

        if not isinstance(data, dict):
            raise ValueError("配置必须是 JSON 对象")
        current = dict(data)
        version = _version_of(current.get(self._version_key, 0))
        seen = 0
        limit = len(self._steps) + 1
        while version in self._steps:
            if seen >= limit:
                raise ValueError("配置迁移没有前进")
            stepped = self._steps[version](dict(current))
            if not isinstance(stepped, dict):
                raise ValueError("配置迁移必须返回对象")
            current = stepped
            version += 1
            current[self._version_key] = version
            seen += 1
        return current


def _version_of(raw: object) -> int:
    if isinstance(raw, bool) or not isinstance(raw, int):
        try:
            text = str(raw).strip()
            if not text or text.startswith("-"):
                raise ValueError
            version = int(text)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"配置版本无法识别：{raw}") from exc
    else:
        version = raw
    if version < 0:
        raise ValueError(f"配置版本无法识别：{raw}")
    return version
