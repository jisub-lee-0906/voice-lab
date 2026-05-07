from pathlib import Path

from voice_lab.gptsovits import build_tts_payload, generate_seeds


def test_generate_seeds_is_deterministic_from_base_seed():
    assert generate_seeds(100, 3) == [100, 101, 102]


def test_build_tts_payload_uses_generic_text_language_and_emotion_metadata_only():
    payload = build_tts_payload(
        text="안녕하세요.",
        text_lang="ko",
        ref_audio_path=Path("/tmp/ref.wav"),
        prompt_text="참조 문장입니다.",
        prompt_lang="ko",
        seed=42,
    )
    assert payload["text"] == "안녕하세요."
    assert payload["text_lang"] == "ko"
    assert payload["ref_audio_path"] == "/tmp/ref.wav"
    assert payload["prompt_text"] == "참조 문장입니다."
    assert payload["prompt_lang"] == "ko"
    assert payload["seed"] == 42
    assert payload["media_type"] == "wav"
    assert payload["streaming_mode"] is False
