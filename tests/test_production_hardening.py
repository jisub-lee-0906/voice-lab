import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import backend.main as backend
from voice_lab.validation import DialogueValidationError, validate_dialogue_text, validate_generation_inputs


def test_validate_dialogue_text_normalizes_whitespace():
    assert validate_dialogue_text(" 안녕\n하세요\t반가워요 ") == "안녕 하세요 반가워요"


def test_validate_dialogue_text_rejects_empty_control_and_too_long():
    with pytest.raises(DialogueValidationError, match="읽힐 대사"):
        validate_dialogue_text("   ")
    with pytest.raises(DialogueValidationError, match="제어 문자"):
        validate_dialogue_text("안녕\x00하세요")
    with pytest.raises(DialogueValidationError, match="250자"):
        validate_dialogue_text("가" * 251)


def test_validate_generation_inputs_warns_when_prompt_matches_target(tmp_path):
    ref = tmp_path / "ref.wav"
    ref.write_bytes(b"wav")
    normalized = validate_generation_inputs(
        text="안녕하세요",
        prompt_text="안녕하세요",
        text_lang="ko",
        prompt_lang="auto",
        ref_audio_path=ref,
    )
    assert normalized["text"] == "안녕하세요"
    assert normalized["prompt_text"] == "안녕하세요"
    assert normalized["warnings"] == ["참조 음성의 실제 대사가 읽힐 대사와 같습니다. 실제로 같은 문장이 아니라면 비워두는 편이 안전합니다."]


def test_generate_rejects_bad_dialogue_before_engine(monkeypatch, tmp_path):
    ref = tmp_path / "ref.wav"
    ref.write_bytes(b"wav")
    client = TestClient(backend.app)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("engine should not be called for invalid dialogue")

    monkeypatch.setattr(backend, "generate_candidates", fail_if_called)

    response = client.post(
        "/api/generate",
        json={"ref_audio_path": str(ref), "text": "가" * 251, "candidate_count": 1},
    )

    assert response.status_code == 400
    assert "250자" in response.json()["detail"]


def test_runtime_endpoint_reports_dependencies(monkeypatch):
    client = TestClient(backend.app)

    monkeypatch.setattr(backend, "wait_for_api", lambda api_url, timeout_seconds: True)

    response = client.get("/api/runtime")

    assert response.status_code == 200
    data = response.json()
    assert data["backend"]["ok"] is True
    assert data["gptsovits"]["ok"] is True
    assert "paths" in data
    assert "disk" in data
