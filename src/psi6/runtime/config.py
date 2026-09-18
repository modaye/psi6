"""把 Pydantic 模型持久化到用户目录。"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Mapping, TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


class ConfigStore:
    """把 ``BaseModel`` 存到 ``~/.psi6/<app_name>/config.json``。"""

    def __init__(self, root: Path | None = None) -> None:
        """``root`` 仅测试注入；默认使用用户主目录下的 ``.psi6``。"""

        self._root = root or Path.home() / ".psi6"

    def path_for(self, app_name: str) -> Path:
        """返回指定应用的配置文件路径。"""

        return self._root / app_name / "config.json"

    def data_path(self, app_name: str, filename: str) -> Path:
        """应用数据目录下的任意文件。"""

        return self._root / app_name / filename

    def load(self, model_type: type[T], *, app_name: str) -> T:
        """读取配置；文件不存在或损坏时备份后返回模型默认值。"""

        path = self.path_for(app_name)
        if not path.is_file():
            return model_type()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return model_type.model_validate(data)
        except (OSError, json.JSONDecodeError, ValidationError):
            self._backup(path)
            return model_type()

    def save(self, model: BaseModel, *, app_name: str) -> None:
        """以 JSON 写入配置文件。"""

        path = self.path_for(app_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = model.model_dump(mode="json")
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load_data(self, app_name: str, filename: str) -> dict[str, Any] | None:
        """读取任意 JSON 对象；缺失或损坏时返回 ``None``。"""

        path = self.data_path(app_name, filename)
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self._backup(path)
            return None
        return data if isinstance(data, dict) else None

    def save_data(self, app_name: str, filename: str, payload: Mapping[str, Any]) -> None:
        """写入任意 JSON 对象。"""

        path = self.data_path(app_name, filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(dict(payload), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _backup(self, path: Path) -> None:
        bak = path.with_name(path.name + ".bak")
        try:
            shutil.copy2(path, bak)
        except OSError:
            pass
