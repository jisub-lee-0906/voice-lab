import io

import pytest
from fastapi import HTTPException, UploadFile
from fastapi.testclient import TestClient

import backend.main as backend


def test_save_rejects_path_outside_generated_directory(monkeypatch, tmp_path):
    monkeypatch.setattr(backend, "GENERATED_DIR", tmp_path / "generated")
    outside = tmp_path / "outside.ogg"
    outside.write_bytes(b"not audio")

    with pytest.raises(HTTPException) as exc:
        backend.save(backend.SaveRequest(source_path=str(outside)))

    assert exc.value.status_code == 400
    assert "생성 폴더" in exc.value.detail


def test_save_requires_valid_generated_ogg(monkeypatch, tmp_path):
    generated = tmp_path / "generated"
    source = generated / "voice" / "candidate.ogg"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"not audio")
    monkeypatch.setattr(backend, "GENERATED_DIR", generated)

    def invalid_audio(_path):
        raise RuntimeError("ffprobe failed")

    monkeypatch.setattr(backend, "probe_duration", invalid_audio)
    with pytest.raises(HTTPException) as exc:
        backend.save(backend.SaveRequest(source_path=str(source)))

    assert exc.value.status_code == 400
    assert "유효한 오디오" in exc.value.detail


def test_save_accepts_generated_ogg_candidate(monkeypatch, tmp_path):
    generated = tmp_path / "generated"
    source = generated / "voice" / "candidate.ogg"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"audio")
    monkeypatch.setattr(backend, "ROOT", tmp_path)
    monkeypatch.setattr(backend, "GENERATED_DIR", generated)
    monkeypatch.setattr(backend, "probe_duration", lambda _path: 1.0)

    result = backend.save(backend.SaveRequest(source_path=str(source), voice_name="voice", line_id="line_001"))

    saved = tmp_path / "approved" / "voice" / "line_001.ogg"
    assert saved.read_bytes() == b"audio"
    assert result.path == str(saved)


def test_generate_rejects_unconfigured_api_url(tmp_path):
    ref = tmp_path / "ref.wav"
    ref.write_bytes(b"audio")

    with pytest.raises(HTTPException) as exc:
        backend.generate(backend.GenerateRequest(ref_audio_path=str(ref), text="안녕하세요", api_url="http://example.test:9100"))

    assert exc.value.status_code == 400
    assert "허용되지 않은" in exc.value.detail


def test_server_config_can_opt_in_additional_api_url(monkeypatch):
    monkeypatch.setenv("VOICE_LAB_ALLOWED_API_URLS", "https://tts.example.test:9443/")

    assert backend.resolve_api_url("https://tts.example.test:9443/") == "https://tts.example.test:9443"


def test_reference_body_limit_rejects_declared_oversize(monkeypatch):
    monkeypatch.setattr(backend, "MAX_UPLOAD_BYTES", 4)
    client = TestClient(backend.app)

    response = client.post("/api/reference", headers={"content-length": "5"})

    assert response.status_code == 413


def test_reference_body_limit_rejects_chunked_body_without_content_length(monkeypatch):
    monkeypatch.setattr(backend, "MAX_UPLOAD_BYTES", 4)
    client = TestClient(backend.app)

    def chunks():
        yield b"12"
        yield b"345"

    response = client.post("/api/reference", content=chunks(), headers={"content-type": "multipart/form-data; boundary=test"})

    assert response.status_code == 413


def test_streaming_upload_limit_removes_partial_file(monkeypatch, tmp_path):
    monkeypatch.setattr(backend, "MAX_UPLOAD_BYTES", 4)
    destination = tmp_path / "partial.wav"
    upload = UploadFile(file=io.BytesIO(b"12345"), filename="sample.wav")

    with pytest.raises(HTTPException) as exc:
        backend.save_upload_with_limit(upload, destination)

    assert exc.value.status_code == 413
    assert not destination.exists()
