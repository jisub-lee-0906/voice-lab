from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import re


EMOTION_ALIASES = {
    "기본": "neutral",
    "중립": "neutral",
    "보통": "neutral",
    "neutral": "neutral",
    "츤츤": "tsun",
    "츤데레": "tsun",
    "tsun": "tsun",
    "화남": "angry",
    "angry": "angry",
    "다정": "soft",
    "부드러움": "soft",
    "soft": "soft",
    "부끄러움": "embarrassed",
    "embarrassed": "embarrassed",
    "진지": "serious",
    "serious": "serious",
    "기쁨": "happy",
    "happy": "happy",
    "슬픔": "sad",
    "sad": "sad",
}


@dataclass(frozen=True)
class TakePaths:
    wav: Path
    ogg: Path
    metadata: Path


def normalize_emotion(value: str) -> str:
    key = (value or "neutral").strip().lower()
    return EMOTION_ALIASES.get(key, sanitize_id(key) or "neutral")


def sanitize_id(value: str) -> str:
    normalized = re.sub(r"[^0-9A-Za-z가-힣_-]+", "_", value.strip().lower())
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized or "untitled"


def validate_reference_duration(duration_seconds: float) -> None:
    duration = float(duration_seconds)
    if not math.isfinite(duration) or not 3.0 <= duration <= 10.0:
        raise ValueError("GPT-SoVITS reference audio must be a finite value in the 3-10 second range")


def build_take_paths(root: Path, character: str, line_id: str, seed: int) -> TakePaths:
    base = Path(root) / "generated" / sanitize_id(character) / sanitize_id(line_id)
    return TakePaths(
        wav=base / f"seed_{int(seed)}.wav",
        ogg=base / f"seed_{int(seed)}.ogg",
        metadata=base / f"seed_{int(seed)}.yaml",
    )
