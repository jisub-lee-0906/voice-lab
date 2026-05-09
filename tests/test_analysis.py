import json
import math
import wave
from pathlib import Path

import pytest

from voice_lab import cli
from voice_lab.analysis import AudioAnalysis, analyze_audio, char_error_rate, load_feedback_labels, normalize_asr_text, pick_best_candidate, score_analysis


def write_tone(path: Path, *, hz: float = 330.0, duration: float = 1.0, amplitude: float = 0.3, sr: int = 16000) -> Path:
    frames = bytearray()
    for i in range(int(sr * duration)):
        sample = int(max(-1.0, min(1.0, math.sin(2 * math.pi * hz * i / sr) * amplitude)) * 32767)
        frames.extend(sample.to_bytes(2, byteorder="little", signed=True))
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sr)
        wav.writeframes(bytes(frames))
    return path


def test_analyze_audio_extracts_pitch_volume_and_professional_tool_status(tmp_path):
    audio = write_tone(tmp_path / "candidate.wav", hz=330.0, duration=1.0, amplitude=0.25)

    result = analyze_audio(audio)

    assert result.path == str(audio)
    assert result.duration_seconds == pytest.approx(1.0, abs=0.05)
    assert -18 <= result.rms_db <= -12
    assert result.f0_median_hz == pytest.approx(330.0, rel=0.12)
    assert "praat_parselmouth" in result.tools
    assert result.tools["praat_parselmouth"] == "ok"
    assert "ffmpeg" in result.tools


def test_analyze_audio_transcodes_ogg_for_praat_metrics(tmp_path):
    wav = write_tone(tmp_path / "candidate.wav", hz=330.0, duration=1.0, amplitude=0.25)
    ogg = tmp_path / "candidate.ogg"
    import subprocess
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(wav), "-c:a", "libvorbis", str(ogg)], check=True)

    result = analyze_audio(ogg)

    assert result.tools["praat_parselmouth"] == "ok"
    assert result.f0_median_hz == pytest.approx(330.0, rel=0.12)


def test_text_normalization_and_character_error_rate_ignore_spacing_and_punctuation():
    assert normalize_asr_text("흥, 네가 오늘부터 내 조수라는 거야?") == "흥네가오늘부터내조수라는거야"
    assert char_error_rate("흥, 네가 오늘부터 내 조수라는 거야?", "흥 네가 오늘부터 내 주수라는 거야") == pytest.approx(1 / 14)


def test_pick_best_candidate_penalizes_bad_asr_match(tmp_path):
    anchor = write_tone(tmp_path / "anchor.wav", hz=340.0, duration=1.0, amplitude=0.25)
    good = write_tone(tmp_path / "bd_intro_001_good.wav", hz=330.0, duration=1.0, amplitude=0.25)
    bad_text = write_tone(tmp_path / "bd_intro_001_bad_text.wav", hz=330.0, duration=1.0, amplitude=0.25)

    def fake_transcriber(path: Path, language: str) -> str:
        return "흥 네가 오늘부터 내 조수라는 거야" if path == good else "완전히 다른 이상한 문장"

    result = pick_best_candidate(
        [bad_text, good],
        anchor_path=anchor,
        target_text="흥, 네가 오늘부터 내 조수라는 거야?",
        transcriber=fake_transcriber,
    )

    assert result.best.path == str(good)
    assert result.best.analysis.transcribed_text == "흥 네가 오늘부터 내 조수라는 거야"
    assert result.ranked[-1].analysis.asr_cer is not None
    assert result.ranked[-1].analysis.asr_cer > 0.5
    assert any("ASR CER" in flag for flag in result.ranked[-1].flags)


def test_pick_best_candidate_penalizes_low_pitch_collapse_against_anchor(tmp_path):
    anchor = write_tone(tmp_path / "anchor.wav", hz=340.0, duration=1.0, amplitude=0.25)
    good = write_tone(tmp_path / "bd_intro_001_seed_1.wav", hz=330.0, duration=1.0, amplitude=0.25)
    low = write_tone(tmp_path / "bd_intro_001_seed_2.wav", hz=140.0, duration=1.0, amplitude=0.25)

    result = pick_best_candidate([low, good], anchor_path=anchor, target_text="테스트 대사")

    assert result.best.path == str(good)
    assert result.best.score > result.ranked[-1].score
    assert any("low-tail pitch" in flag or "median pitch" in flag for flag in result.ranked[-1].flags)


def test_feedback_labels_can_penalize_user_rejected_candidates(tmp_path):
    anchor = write_tone(tmp_path / "anchor.wav", hz=340.0, duration=1.0, amplitude=0.25)
    candidates = tmp_path / "candidates"
    candidates.mkdir()
    previously_rejected = write_tone(candidates / "bd_intro_002_seed_2026052105.wav", hz=330.0, duration=1.0, amplitude=0.25)
    alternative = write_tone(candidates / "bd_intro_002_seed_2026052005.wav", hz=330.0, duration=1.0, amplitude=0.25)
    labels_path = tmp_path / "labels.yaml"
    labels_path.write_text(
        "labels:\n"
        f"  - path: {previously_rejected}\n"
        "    verdict: reject\n"
        "    penalty: 80\n"
        "    reasons: [mechanical_front]\n",
        encoding="utf-8",
    )

    result = pick_best_candidate(
        [previously_rejected, alternative],
        anchor_path=anchor,
        target_text="테스트 대사",
        feedback_labels=load_feedback_labels(labels_path),
    )

    assert result.best.path == str(alternative)
    assert any("feedback reject" in flag for flag in result.ranked[-1].flags)


def test_collect_audio_files_deduplicates_wav_when_ogg_exists(tmp_path):
    from voice_lab.analysis import collect_audio_files

    candidates = tmp_path / "candidates"
    candidates.mkdir()
    write_tone(candidates / "seed_1.wav", hz=330.0)
    write_tone(candidates / "seed_2.wav", hz=330.0)
    ogg = candidates / "seed_1.ogg"
    import subprocess
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(candidates / "seed_1.wav"), "-c:a", "libvorbis", str(ogg)], check=True)

    files = collect_audio_files(candidates)

    assert [path.name for path in files] == ["seed_1.ogg", "seed_2.wav"]


def make_analysis(
    *,
    path: str = "candidate.wav",
    hnr_db: float | None = 9.0,
    jitter: float | None = 0.016,
    shimmer: float | None = 0.10,
    flatness: float = 0.39,
    silence: float = 0.34,
    voiced: float = 0.56,
    f0: float = 360.0,
    f0_p10: float = 270.0,
    low_band: float = 0.004,
    asr_cer: float | None = 0.02,
) -> AudioAnalysis:
    return AudioAnalysis(
        path=path,
        duration_seconds=3.0,
        rms_db=-27.0,
        peak_db=-7.0,
        clipping_ratio=0.0,
        silence_ratio=silence,
        low_band_ratio=low_band,
        spectral_flatness=flatness,
        f0_median_hz=f0,
        f0_p10_hz=f0_p10,
        f0_p25_hz=f0_p10 + 15,
        f0_min_hz=max(80.0, f0_p10 - 40),
        voiced_ratio=voiced,
        hnr_db=hnr_db,
        jitter_local=jitter,
        shimmer_local=shimmer,
        transcribed_text="테스트",
        asr_cer=asr_cer,
        tools={"ffmpeg": "ok", "praat_parselmouth": "ok"},
    )


def test_strict_quality_gate_rejects_residual_mechanical_texture():
    anchor = make_analysis(path="anchor.wav", hnr_db=10.0, jitter=0.014, shimmer=0.09, flatness=0.38, silence=0.32, voiced=0.58, f0=380.0, f0_p10=275.0)
    residual_mechanical = make_analysis(
        hnr_db=6.8,
        jitter=0.021,
        shimmer=0.132,
        flatness=0.46,
        silence=0.42,
        voiced=0.43,
        f0=330.0,
        f0_p10=240.0,
        asr_cer=0.18,
    )

    score, flags = score_analysis(residual_mechanical, anchor, quality_mode="strict")

    assert score < 75
    assert any("STRICT FAIL" in flag for flag in flags)
    assert any("mechanical risk" in flag for flag in flags)


def test_strict_quality_gate_allows_near_clean_take():
    anchor = make_analysis(path="anchor.wav", hnr_db=10.0, jitter=0.014, shimmer=0.09, flatness=0.38, silence=0.32, voiced=0.58, f0=380.0, f0_p10=275.0)
    clean = make_analysis(hnr_db=9.2, jitter=0.015, shimmer=0.095, flatness=0.39, silence=0.34, voiced=0.57, f0=375.0, f0_p10=272.0, asr_cer=0.02)

    score, flags = score_analysis(clean, anchor, quality_mode="strict")

    assert score >= 90
    assert not any("STRICT FAIL" in flag for flag in flags)


def test_cli_pick_best_writes_json_and_best_copy(tmp_path, capsys):
    anchor = write_tone(tmp_path / "anchor.wav", hz=340.0, duration=1.0, amplitude=0.25)
    candidates = tmp_path / "candidates"
    candidates.mkdir()
    write_tone(candidates / "bd_intro_001_seed_1.wav", hz=330.0, duration=1.0, amplitude=0.25)
    write_tone(candidates / "bd_intro_001_seed_2.wav", hz=140.0, duration=1.0, amplitude=0.25)
    output = tmp_path / "best"

    assert cli.main([
        "pick-best",
        "--input-dir", str(candidates),
        "--anchor", str(anchor),
        "--target-text", "테스트 대사",
        "--output-dir", str(output),
    ]) == 0
    data = json.loads(capsys.readouterr().out)

    assert data["ok"] is True
    assert Path(data["best"]["path"]).name == "bd_intro_001_seed_1.wav"
    assert (output / "best" / "bd_intro_001_seed_1.wav").exists()
    assert (output / "best_selection.json").exists()


def test_cli_pick_best_strict_reports_quality_fail(tmp_path, capsys):
    anchor = write_tone(tmp_path / "anchor.wav", hz=340.0, duration=1.0, amplitude=0.25)
    candidates = tmp_path / "candidates"
    candidates.mkdir()
    write_tone(candidates / "bad.wav", hz=140.0, duration=1.0, amplitude=0.25)
    output = tmp_path / "best_strict"

    assert cli.main([
        "pick-best",
        "--input-dir", str(candidates),
        "--anchor", str(anchor),
        "--target-text", "테스트 대사",
        "--output-dir", str(output),
        "--quality-mode", "strict",
    ]) == 0
    data = json.loads(capsys.readouterr().out)

    assert data["best"]["quality_pass"] is False
    assert json.loads((output / "best_selection.json").read_text(encoding="utf-8"))["quality_pass"] is False
