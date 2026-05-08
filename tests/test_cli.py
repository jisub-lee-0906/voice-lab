import json

import pytest

from voice_lab import cli


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text
        self.ok = 200 <= status_code < 300

    def json(self):
        return self._payload


def read_json_output(capsys):
    return json.loads(capsys.readouterr().out)


def test_cli_doctor_reads_runtime_endpoint(monkeypatch, capsys):
    def fake_get(url, timeout):
        assert url == "http://backend/api/runtime"
        return FakeResponse(payload={"ok": True, "backend": {"ok": True}, "gptsovits": {"ok": True}})

    monkeypatch.setattr(cli.requests, "get", fake_get)

    assert cli.main(["doctor", "--backend", "http://backend"]) == 0
    data = read_json_output(capsys)

    assert data["ok"] is True
    assert data["backend"]["ok"] is True


def test_cli_status_reports_backend_and_gptsovits(monkeypatch, capsys):
    calls = []

    def fake_get(url, timeout):
        calls.append(url)
        return FakeResponse(payload={"status": "ok"})

    monkeypatch.setattr(cli.requests, "get", fake_get)

    assert cli.main(["status", "--backend", "http://backend", "--gptsovits", "http://gpt"]) == 0
    data = read_json_output(capsys)

    assert data["ok"] is True
    assert data["backend"]["ok"] is True
    assert data["gptsovits"]["ok"] is True
    assert calls == ["http://backend/api/health", "http://gpt/docs"]


def test_cli_reference_posts_existing_path_form(monkeypatch, capsys):
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse(payload={"path": "/tmp/ref.wav", "duration": 9.5})

    monkeypatch.setattr(cli.requests, "post", fake_post)

    assert cli.main([
        "reference",
        "--backend", "http://backend",
        "--existing-path", "/tmp/source.wav",
        "--start", "1.5",
        "--duration", "8",
        "--voice", "heroine_a",
        "--emotion", "다정",
    ]) == 0
    data = read_json_output(capsys)

    assert data["path"] == "/tmp/ref.wav"
    assert captured["url"] == "http://backend/api/reference"
    assert captured["data"] == {
        "voice_name": "heroine_a",
        "emotion": "다정",
        "start_seconds": "1.5",
        "duration_seconds": "8",
        "existing_path": "/tmp/source.wav",
    }
    assert "files" not in captured


def test_cli_reference_uploads_audio_file(monkeypatch, tmp_path, capsys):
    source = tmp_path / "voice.wav"
    source.write_bytes(b"wav")
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        assert "audio_file" in kwargs["files"]
        assert kwargs["files"]["audio_file"][0] == "voice.wav"
        return FakeResponse(payload={"path": "/tmp/ref.wav"})

    monkeypatch.setattr(cli.requests, "post", fake_post)

    assert cli.main(["reference", "--backend", "http://backend", "--file", str(source)]) == 0
    data = read_json_output(capsys)

    assert data["path"] == "/tmp/ref.wav"
    assert captured["data"]["existing_path"] == ""


def test_cli_generate_defaults_to_korean_and_returns_candidates(monkeypatch, capsys):
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse(payload={"candidates": [{"ogg": "/tmp/seed_1000.ogg"}]})

    monkeypatch.setattr(cli.requests, "post", fake_post)

    assert cli.main([
        "generate",
        "--backend", "http://backend",
        "--ref", "/tmp/ref.wav",
        "--text", "안녕하세요",
        "--line-id", "ch01_001",
    ]) == 0
    data = read_json_output(capsys)

    assert data["candidates"][0]["ogg"] == "/tmp/seed_1000.ogg"
    assert captured["url"] == "http://backend/api/generate"
    assert captured["json"]["text_lang"] == "ko"
    assert captured["json"]["prompt_lang"] == "auto"
    assert captured["json"]["prompt_text"] == ""


def test_cli_save_posts_selected_take(monkeypatch, capsys):
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse(payload={"path": "/approved/ch01_001.ogg"})

    monkeypatch.setattr(cli.requests, "post", fake_post)

    assert cli.main([
        "save",
        "--backend", "http://backend",
        "--source", "/tmp/seed_1000.ogg",
        "--voice", "heroine_a",
        "--line-id", "ch01_001",
    ]) == 0
    data = read_json_output(capsys)

    assert data["path"] == "/approved/ch01_001.ogg"
    assert captured["json"] == {
        "source_path": "/tmp/seed_1000.ogg",
        "voice_name": "heroine_a",
        "line_id": "ch01_001",
    }


def test_cli_batch_generates_manifest_from_json_lines(monkeypatch, tmp_path, capsys):
    batch = tmp_path / "lines.json"
    batch.write_text(json.dumps({"lines": [
        {"line_id": "ch01_001", "text": "안녕하세요", "ref_audio_path": "/refs/a.wav"},
        {"line_id": "ch01_002", "text": "반가워요", "ref_audio_path": "/refs/a.wav", "voice_name": "heroine_a"},
    ]}, ensure_ascii=False), encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    calls = []

    def fake_post(url, **kwargs):
        calls.append(kwargs["json"])
        return FakeResponse(payload={"candidates": [{"seed": kwargs["json"]["base_seed"], "ogg": f"/gen/{kwargs['json']['line_id']}.ogg"}]})

    monkeypatch.setattr(cli.requests, "post", fake_post)

    assert cli.main(["batch-generate", "--backend", "http://backend", "--input", str(batch), "--manifest", str(manifest), "--candidates", "1"]) == 0
    data = read_json_output(capsys)
    written = json.loads(manifest.read_text(encoding="utf-8"))

    assert data["ok"] is True
    assert [item["line_id"] for item in written["items"]] == ["ch01_001", "ch01_002"]
    assert calls[0]["text_lang"] == "ko"
    assert calls[0]["prompt_text"] == ""
    assert calls[1]["voice_name"] == "heroine_a"


def test_cli_api_error_exits_with_json_detail(monkeypatch, capsys):
    def fake_post(url, **kwargs):
        return FakeResponse(status_code=400, payload={"detail": "길이 초는 3~10초 사이여야 합니다."})

    monkeypatch.setattr(cli.requests, "post", fake_post)

    assert cli.main(["reference", "--existing-path", "/tmp/source.wav", "--duration", "15"]) == 1
    data = read_json_output(capsys)

    assert data["ok"] is False
    assert data["detail"] == "길이 초는 3~10초 사이여야 합니다."
