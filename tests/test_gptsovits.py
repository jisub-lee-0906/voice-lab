from pathlib import Path

import pytest

from voice_lab import gptsovits
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
    assert Path(payload["ref_audio_path"]) == Path("/tmp/ref.wav")
    assert payload["prompt_text"] == "참조 문장입니다."
    assert payload["prompt_lang"] == "ko"
    assert payload["seed"] == 42
    assert payload["media_type"] == "wav"
    assert payload["streaming_mode"] is False


def test_wait_for_api_disables_redirects_and_reports_redirect(monkeypatch):
    calls = {}

    class RedirectResponse:
        # requests.Response.ok is True for redirects; status must be checked first.
        ok = True
        status_code = 302

    def fake_get(*args, **kwargs):
        calls.update(kwargs)
        return RedirectResponse()

    times = iter([0, 0, 2])
    monkeypatch.setattr(gptsovits.requests, "get", fake_get)
    monkeypatch.setattr(gptsovits.time, "time", lambda: next(times))
    monkeypatch.setattr(gptsovits.time, "sleep", lambda _seconds: None)

    with pytest.raises(TimeoutError, match="redirect is not allowed"):
        gptsovits.wait_for_api(timeout_seconds=1)

    assert calls["allow_redirects"] is False


def test_synthesize_rejects_redirect_without_following_it(monkeypatch, tmp_path):
    calls = {}

    class RedirectResponse:
        ok = False
        status_code = 307
        text = "redirect"
        content = b""

    def fake_post(*args, **kwargs):
        calls.update(kwargs)
        return RedirectResponse()

    monkeypatch.setattr(gptsovits.requests, "post", fake_post)

    with pytest.raises(RuntimeError, match="redirect is not allowed"):
        gptsovits.synthesize_to_wav({}, tmp_path / "candidate.wav")

    assert calls["allow_redirects"] is False
