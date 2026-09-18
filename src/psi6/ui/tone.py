"""界面语气：信息、成功、警告、错误、中性。"""

from __future__ import annotations

from typing import Literal

Tone = Literal["neutral", "info", "success", "warning", "error"]

VALID_TONES: tuple[Tone, ...] = ("neutral", "info", "success", "warning", "error")


def normalize_tone(value: str) -> Tone:
    """未知语气回落到 ``neutral``。"""

    return value if value in VALID_TONES else "neutral"
