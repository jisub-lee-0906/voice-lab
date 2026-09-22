from fastapi import HTTPException
import pytest

import backend.main as backend


@pytest.mark.parametrize("start", [-1, float("nan"), float("inf")])
def test_validate_reference_window_rejects_invalid_start(tmp_path, start):
    source = tmp_path / "source.wav"
    source.write_bytes(b"fake")
    with pytest.raises(HTTPException) as exc:
        backend.validate_reference_window(source, start, 9.5)
    assert exc.value.status_code == 400
    assert "시작 초" in exc.value.detail


def test_validate_reference_window_rejects_duration_past_source(monkeypatch, tmp_path):
    source = tmp_path / "source.wav"
    source.write_bytes(b"fake")
    monkeypatch.setattr(backend, "probe_duration", lambda path: 20.0)
    with pytest.raises(HTTPException) as exc:
        backend.validate_reference_window(source, 15, 9.5)
    assert exc.value.status_code == 400
    assert "파일 길이" in exc.value.detail
    assert "24.50" in exc.value.detail


def test_validate_reference_window_accepts_valid_window(monkeypatch, tmp_path):
    source = tmp_path / "source.wav"
    source.write_bytes(b"fake")
    monkeypatch.setattr(backend, "probe_duration", lambda path: 30.0)
    backend.validate_reference_window(source, 15, 9.5)


def test_create_reference_reports_short_actual_clip(monkeypatch, tmp_path):
    source = tmp_path / "source.wav"
    source.write_bytes(b"fake")
    durations = iter([20.0, 2.0])
    monkeypatch.setattr(backend, "probe_duration", lambda path: next(durations))
    monkeypatch.setattr(backend, "cut_reference", lambda *args, **kwargs: None)

    with pytest.raises(HTTPException) as exc:
        backend.create_reference(voice_name="default", emotion="기본", existing_path=str(source), start_seconds=1, duration_seconds=3, audio_file=None)
    assert exc.value.status_code == 500
    assert "실제 참조 길이" in exc.value.detail
