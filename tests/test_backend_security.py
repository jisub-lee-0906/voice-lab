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
    client = TestClient(backend.app, base_url="http://127.0.0.1:8100", client=("127.0.0.1", 50000))

    response = client.post("/api/reference", headers={"content-length": "5"})

    assert response.status_code == 413


def test_reference_body_limit_rejects_chunked_body_without_content_length(monkeypatch):
    monkeypatch.setattr(backend, "MAX_UPLOAD_BYTES", 4)
    client = TestClient(backend.app, base_url="http://127.0.0.1:8100", client=("127.0.0.1", 50000))

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


def test_local_boundary_rejects_untrusted_origin():
    client = TestClient(backend.app, base_url="http://127.0.0.1:8100", client=("127.0.0.1", 50000))

    response = client.get("/api/health", headers={"host": "127.0.0.1:8100", "origin": "https://evil.example"})

    assert response.status_code == 403


def test_local_boundary_accepts_frontend_proxy_origin():
    client = TestClient(backend.app, base_url="http://127.0.0.1:8100", client=("127.0.0.1", 50000))

    response = client.get("/api/health", headers={"host": "127.0.0.1:8100", "origin": "http://localhost:3100"})

    assert response.status_code == 200


def test_external_host_fails_closed_without_token(monkeypatch):
    monkeypatch.delenv("VOICE_LAB_API_TOKEN", raising=False)
    client = TestClient(backend.app, base_url="http://127.0.0.1:8100", client=("127.0.0.1", 50000))

    response = client.get("/api/health", headers={"host": "voice.example"})

    assert response.status_code == 403


def test_external_api_requires_matching_operator_token(monkeypatch):
    monkeypatch.setenv("VOICE_LAB_API_TOKEN", "test-only-token")
    client = TestClient(backend.app, base_url="http://127.0.0.1:8100", client=("127.0.0.1", 50000))

    denied = client.get("/api/health", headers={"host": "voice.example", "authorization": "Bearer wrong"})
    allowed = client.get("/api/health", headers={"host": "voice.example", "authorization": "Bearer test-only-token"})

    assert denied.status_code == 403
    assert allowed.status_code == 200


def test_external_media_remains_local_only_even_with_token(monkeypatch):
    monkeypatch.setenv("VOICE_LAB_API_TOKEN", "test-only-token")
    client = TestClient(backend.app, base_url="http://127.0.0.1:8100", client=("127.0.0.1", 50000))

    response = client.get("/media/generated/missing.ogg", headers={"host": "voice.example", "authorization": "Bearer test-only-token"})

    assert response.status_code == 403


def test_reference_paths_are_limited_to_refs_and_voice_db(monkeypatch, tmp_path):
    monkeypatch.setattr(backend, "ROOT", tmp_path)
    refs = tmp_path / "refs"
    voice_db = tmp_path / "voice_db"
    refs.mkdir()
    voice_db.mkdir()
    ref_file = refs / "sample.wav"
    voice_file = voice_db / "sample.wav"
    outside = tmp_path / "outside.wav"
    for path in (ref_file, voice_file, outside):
        path.write_bytes(b"audio")

    assert backend.resolve_allowed_reference_path(ref_file) == ref_file.resolve()
    assert backend.resolve_allowed_reference_path(voice_file) == voice_file.resolve()
    with pytest.raises(HTTPException):
        backend.resolve_allowed_reference_path(outside)


def test_remote_client_cannot_spoof_localhost_host_without_token(monkeypatch):
    monkeypatch.delenv("VOICE_LAB_API_TOKEN", raising=False)
    client = TestClient(
        backend.app,
        base_url="http://localhost:8100",
        client=("203.0.113.25", 50000),
    )

    response = client.get("/api/health", headers={"host": "localhost:8100"})

    assert response.status_code == 403


def test_remote_client_localhost_host_still_requires_token(monkeypatch):
    monkeypatch.setenv("VOICE_LAB_API_TOKEN", "test-only-token")
    client = TestClient(
        backend.app,
        base_url="http://localhost:8100",
        client=("203.0.113.25", 50000),
    )

    denied = client.get("/api/health", headers={"host": "localhost:8100"})
    allowed = client.get(
        "/api/health",
        headers={"host": "localhost:8100", "authorization": "Bearer test-only-token"},
    )

    assert denied.status_code == 403
    assert allowed.status_code == 200
