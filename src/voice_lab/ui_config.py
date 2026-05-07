from __future__ import annotations

EMOTION_BUTTONS = ["기본", "츤츤", "다정", "부끄러움", "진지", "화남", "기쁨", "슬픔"]
LANGUAGE_PRESETS = ["auto", "ko", "ja", "en", "zh", "all_zh", "all_ja", "all_ko", "all_yue"]


def normalize_language_choice(value: str | None) -> str:
    return (value or "auto").strip() or "auto"
