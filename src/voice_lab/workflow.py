from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .audio import build_clip_path, convert_to_ogg, cut_reference
from .core import build_take_paths, normalize_emotion, sanitize_id
from .gptsovits import build_tts_payload, generate_seeds, synthesize_to_wav


@dataclass(frozen=True)
class VoiceRequest:
    character: str
    emotion: str
    line_id: str
    text: str
    text_lang: str
    prompt_text: str
    prompt_lang: str
    source_audio: Path
    ref_audio: Path
    seed: int


def render_metadata(request: VoiceRequest, output_wav: Path, output_ogg: Path) -> dict[str, Any]:
    return {
        "character": sanitize_id(request.character),
        "emotion": normalize_emotion(request.emotion),
        "line_id": sanitize_id(request.line_id),
        "text": request.text,
        "text_lang": request.text_lang,
        "prompt_text": request.prompt_text,
        "prompt_lang": request.prompt_lang,
        "seed": int(request.seed),
        "source_audio": request.source_audio.as_posix(),
        "ref_audio": request.ref_audio.as_posix(),
        "outputs": {
            "wav": output_wav.as_posix(),
            "ogg": output_ogg.as_posix(),
        },
    }


def save_metadata(path: Path, data: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


def prepare_reference(
    *,
    root: Path,
    source_audio: Path,
    character: str,
    emotion: str,
    start_seconds: float,
    duration_seconds: float,
) -> Path:
    ref_path = build_clip_path(root, character, emotion, source_audio)
    return cut_reference(source_audio, ref_path, start_seconds, duration_seconds)


def generate_candidates(
    *,
    root: Path,
    character: str,
    emotion: str,
    line_id: str,
    text: str,
    text_lang: str,
    ref_audio: Path,
    prompt_text: str,
    prompt_lang: str,
    base_seed: int,
    count: int,
    api_url: str,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for seed in generate_seeds(base_seed, count):
        paths = build_take_paths(root, character, line_id, seed)
        request = VoiceRequest(
            character=character,
            emotion=emotion,
            line_id=line_id,
            text=text,
            text_lang=text_lang,
            prompt_text=prompt_text,
            prompt_lang=prompt_lang,
            source_audio=ref_audio,
            ref_audio=ref_audio,
            seed=seed,
        )
        payload = build_tts_payload(
            text=text,
            text_lang=text_lang,
            ref_audio_path=ref_audio,
            prompt_text=prompt_text,
            prompt_lang=prompt_lang,
            seed=seed,
        )
        synthesize_to_wav(payload, paths.wav, api_url=api_url)
        convert_to_ogg(paths.wav, paths.ogg)
        metadata = render_metadata(request, paths.wav, paths.ogg)
        save_metadata(paths.metadata, metadata)
        results.append({"seed": seed, "wav": str(paths.wav), "ogg": str(paths.ogg), "metadata": str(paths.metadata)})
    return results
