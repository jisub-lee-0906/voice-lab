from fastapi.testclient import TestClient

import backend.main as backend


def test_reference_unexpected_errors_return_korean_detail(monkeypatch, tmp_path):
    audio = tmp_path / "sample.wav"
    audio.write_bytes(b"not really wav")

    def boom(*args, **kwargs):
        raise RuntimeError("ffmpeg crashed")

    monkeypatch.setattr(backend, "probe_duration", lambda path: 20.0)
    monkeypatch.setattr(backend, "cut_reference", boom)
    client = TestClient(backend.app)
    response = client.post(
        "/api/reference",
        data={
            "voice_name": "default",
            "emotion": "기본",
            "start_seconds": "0",
            "duration_seconds": "9.5",
            "existing_path": str(audio),
        },
    )
    assert response.status_code == 500
    assert response.json()["detail"].startswith("참조 음성을 만들지 못했습니다")
    assert "ffmpeg crashed" in response.json()["detail"]


def test_generate_unexpected_errors_return_korean_detail(monkeypatch, tmp_path):
    ref = tmp_path / "ref.wav"
    ref.write_bytes(b"fake")

    monkeypatch.setattr(backend, "ensure_api", lambda *args, **kwargs: "ready")

    def boom(*args, **kwargs):
        raise RuntimeError("tts failed")

    monkeypatch.setattr(backend, "generate_candidates", boom)
    client = TestClient(backend.app)
    response = client.post(
        "/api/generate",
        json={
            "ref_audio_path": str(ref),
            "text": "안녕하세요",
            "autostart_api": False,
        },
    )
    assert response.status_code == 500
    assert response.json()["detail"].startswith("음성 생성에 실패했습니다")
    assert "tts failed" in response.json()["detail"]
