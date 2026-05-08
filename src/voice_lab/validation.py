from __future__ import annotations

import re
from pathlib import Path
from typing import Any

MAX_DIALOGUE_CHARS = 250
CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
WHITESPACE = re.compile(r"\s+")
SUPPORTED_LANGUAGES = {"ko", "ja", "en", "zh", "auto"}


class DialogueValidationError(ValueError):
    pass


def normalize_whitespace(text: str) -> str:
    return WHITESPACE.sub(" ", text.strip())


def validate_dialogue_text(text: str, *, label: str = "읽힐 대사", max_chars: int = MAX_DIALOGUE_CHARS) -> str:
    normalized = normalize_whitespace(text or "")
    if not normalized:
        raise DialogueValidationError(f"{label}를 입력하세요.")
    if CONTROL_CHARS.search(normalized):
        raise DialogueValidationError(f"{label}에 사용할 수 없는 제어 문자가 있습니다.")
    if len(normalized) > max_chars:
        raise DialogueValidationError(f"{label}는 {max_chars}자 이하로 나눠서 생성하세요.")
    return normalized


def validate_language(value: str, *, default: str) -> str:
    normalized = (value or default).strip().lower() or default
    if normalized not in SUPPORTED_LANGUAGES:
        raise DialogueValidationError(f"지원하지 않는 언어 코드입니다: {value}")
    return normalized


def validate_generation_inputs(*, text: str, prompt_text: str, text_lang: str, prompt_lang: str, ref_audio_path: Path) -> dict[str, Any]:
    ref_audio = Path(ref_audio_path).expanduser()
    if not ref_audio.exists():
        raise DialogueValidationError(f"참조 WAV가 없습니다: {ref_audio}")
    normalized_text = validate_dialogue_text(text)
    normalized_prompt = normalize_whitespace(prompt_text or "")
    if normalized_prompt:
        validate_dialogue_text(normalized_prompt, label="참조 음성의 실제 대사")
    warnings: list[str] = []
    if normalized_prompt and normalized_prompt == normalized_text:
        warnings.append("참조 음성의 실제 대사가 읽힐 대사와 같습니다. 실제로 같은 문장이 아니라면 비워두는 편이 안전합니다.")
    return {
        "text": normalized_text,
        "text_lang": validate_language(text_lang, default="ko"),
        "prompt_text": normalized_prompt,
        "prompt_lang": validate_language(prompt_lang, default="auto"),
        "warnings": warnings,
    }
