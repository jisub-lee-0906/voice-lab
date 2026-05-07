from pathlib import Path

import backend.main as backend


def test_normalize_generation_request_does_not_use_target_text_as_prompt_text(tmp_path):
    request = backend.GenerateRequest(
        ref_audio_path=str(tmp_path / "ref.wav"),
        text="읽힐 한글 대사",
        prompt_text="",
        text_lang="ko",
        prompt_lang="auto",
    )
    normalized = backend.normalize_generation_request(request)
    assert normalized["prompt_text"] == ""
    assert normalized["text_lang"] == "ko"
    assert normalized["prompt_lang"] == "auto"


def test_normalize_generation_request_keeps_actual_reference_transcript(tmp_path):
    request = backend.GenerateRequest(
        ref_audio_path=str(tmp_path / "ref.wav"),
        text="읽힐 한글 대사",
        prompt_text=" 실제 참조 대사 ",
        text_lang="",
        prompt_lang="",
    )
    normalized = backend.normalize_generation_request(request)
    assert normalized["prompt_text"] == "실제 참조 대사"
    assert normalized["text_lang"] == "ko"
    assert normalized["prompt_lang"] == "auto"
