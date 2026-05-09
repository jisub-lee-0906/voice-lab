from __future__ import annotations

import json
import math
import re
import shutil
import subprocess
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np

EPS = 1e-12
DEFAULT_SR = 16000


@dataclass
class AudioAnalysis:
    path: str
    duration_seconds: float
    rms_db: float
    peak_db: float
    clipping_ratio: float
    silence_ratio: float
    low_band_ratio: float
    spectral_flatness: float
    f0_median_hz: float | None
    f0_p10_hz: float | None
    f0_p25_hz: float | None
    f0_min_hz: float | None
    voiced_ratio: float
    hnr_db: float | None
    jitter_local: float | None
    shimmer_local: float | None
    transcribed_text: str | None
    asr_cer: float | None
    tools: dict[str, str]


@dataclass
class ScoredCandidate:
    path: str
    score: float
    flags: list[str]
    analysis: AudioAnalysis


@dataclass
class BestPickResult:
    best: ScoredCandidate
    ranked: list[ScoredCandidate]
    anchor: AudioAnalysis | None
    target_text: str


def normalize_asr_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).lower()
    return "".join(ch for ch in normalized if ch.isalnum() or "가" <= ch <= "힣")


def char_error_rate(reference: str, hypothesis: str) -> float:
    ref = normalize_asr_text(reference)
    hyp = normalize_asr_text(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0
    previous = list(range(len(hyp) + 1))
    for i, ref_ch in enumerate(ref, start=1):
        current = [i]
        for j, hyp_ch in enumerate(hyp, start=1):
            cost = 0 if ref_ch == hyp_ch else 1
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + cost))
        previous = current
    return previous[-1] / len(ref)


def _db(value: float) -> float:
    return 20.0 * math.log10(max(float(value), EPS))


def _decode_audio(path: Path, sample_rate: int = DEFAULT_SR) -> np.ndarray:
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(path),
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-f",
        "f32le",
        "pipe:1",
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace")[:500])
    return np.frombuffer(result.stdout, dtype=np.float32).copy()


def _band_ratio(samples: np.ndarray, sample_rate: int, high_hz: float = 180.0) -> float:
    if len(samples) < 512:
        return 0.0
    windowed = samples * np.hanning(len(samples))
    power = np.abs(np.fft.rfft(windowed)) ** 2
    freqs = np.fft.rfftfreq(len(windowed), 1.0 / sample_rate)
    mask = freqs <= high_hz
    return float(np.sum(power[mask]) / (np.sum(power) + EPS))


def _spectral_flatness(samples: np.ndarray) -> float:
    if len(samples) < 1024:
        return 0.0
    n_fft = 1024
    hop = 512
    values: list[float] = []
    for start in range(0, max(1, len(samples) - n_fft), hop):
        frame = samples[start : start + n_fft]
        if len(frame) < n_fft:
            break
        if float(np.sqrt(np.mean(frame * frame))) < 0.003:
            continue
        mag = np.abs(np.fft.rfft(frame * np.hanning(n_fft))) + EPS
        values.append(float(np.exp(np.mean(np.log(mag))) / (np.mean(mag) + EPS)))
    return float(np.median(values)) if values else 0.0


def _acf_f0(samples: np.ndarray, sample_rate: int, fmin: float = 80.0, fmax: float = 500.0) -> tuple[float | None, float | None, float | None, float | None, float]:
    frame_len = int(sample_rate * 0.04)
    hop = int(sample_rate * 0.01)
    min_lag = max(1, int(sample_rate / fmax))
    max_lag = min(frame_len - 1, int(sample_rate / fmin))
    f0s: list[float] = []
    frames = 0
    for start in range(0, max(1, len(samples) - frame_len), hop):
        frame = samples[start : start + frame_len]
        if len(frame) < frame_len:
            break
        frames += 1
        frame = frame - float(np.mean(frame))
        if float(np.sqrt(np.mean(frame * frame))) < 0.008:
            continue
        frame = frame * np.hanning(frame_len)
        corr = np.correlate(frame, frame, mode="full")[frame_len - 1 :]
        if corr[0] <= EPS:
            continue
        segment = corr[min_lag : max_lag + 1]
        if len(segment) == 0:
            continue
        lag = int(np.argmax(segment)) + min_lag
        confidence = float(corr[lag] / (corr[0] + EPS))
        if confidence < 0.28:
            continue
        f0s.append(float(sample_rate / lag))
    if not f0s:
        return None, None, None, None, 0.0
    arr = np.asarray(f0s, dtype=np.float32)
    return float(np.median(arr)), float(np.percentile(arr, 10)), float(np.percentile(arr, 25)), float(np.min(arr)), len(f0s) / max(1, frames)


def _praat_metrics(path: Path) -> tuple[dict[str, float | None], str]:
    try:
        import parselmouth
        from parselmouth.praat import call
    except Exception as exc:
        return {"hnr_db": None, "jitter_local": None, "shimmer_local": None}, f"unavailable: {exc}"
    try:
        praat_path = path
        cleanup_path: Path | None = None
        if path.suffix.lower() not in {".wav", ".aiff", ".aif"}:
            cleanup_path = path.with_suffix(path.suffix + ".praat_tmp.wav")
            command = [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(path),
                "-ac",
                "1",
                "-ar",
                str(DEFAULT_SR),
                str(cleanup_path),
            ]
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            if result.returncode != 0:
                return {"hnr_db": None, "jitter_local": None, "shimmer_local": None}, f"failed to transcode for praat: {result.stderr.decode(errors='replace')[:200]}"
            praat_path = cleanup_path
        try:
            snd = parselmouth.Sound(str(praat_path))
            pitch = snd.to_pitch(time_step=0.01, pitch_floor=75, pitch_ceiling=600)
            point_process = call(snd, "To PointProcess (periodic, cc)", 75, 600)
            hnr = call(snd, "To Harmonicity (cc)", 0.01, 75, 0.1, 1.0)
            hnr_db = float(call(hnr, "Get mean", 0, 0))
            jitter = float(call(point_process, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3))
            shimmer = float(call([snd, point_process], "Get shimmer (local)", 0, 0, 0.0001, 0.02, 1.3, 1.6))
            selected = pitch.selected_array["frequency"]
            selected = selected[selected > 0]
            metrics: dict[str, float | None] = {
                "hnr_db": hnr_db if math.isfinite(hnr_db) else None,
                "jitter_local": jitter if math.isfinite(jitter) else None,
                "shimmer_local": shimmer if math.isfinite(shimmer) else None,
            }
            if len(selected):
                metrics["praat_f0_median_hz"] = float(np.median(selected))
                metrics["praat_f0_p10_hz"] = float(np.percentile(selected, 10))
            return metrics, "ok"
        finally:
            if cleanup_path is not None:
                cleanup_path.unlink(missing_ok=True)
    except Exception as exc:
        return {"hnr_db": None, "jitter_local": None, "shimmer_local": None}, f"failed: {exc}"


def analyze_audio(path: str | Path, *, target_text: str = "", transcribed_text: str | None = None) -> AudioAnalysis:
    audio_path = Path(path)
    samples = _decode_audio(audio_path)
    if len(samples) == 0:
        raise ValueError(f"empty audio: {audio_path}")
    duration = len(samples) / DEFAULT_SR
    rms = float(np.sqrt(np.mean(samples * samples)))
    peak = float(np.max(np.abs(samples)))
    f0_median, f0_p10, f0_p25, f0_min, voiced_ratio = _acf_f0(samples, DEFAULT_SR)
    praat, praat_status = _praat_metrics(audio_path)
    if praat.get("praat_f0_median_hz"):
        f0_median = float(praat["praat_f0_median_hz"])
    if praat.get("praat_f0_p10_hz"):
        f0_p10 = float(praat["praat_f0_p10_hz"])
    asr_cer = char_error_rate(target_text, transcribed_text) if target_text and transcribed_text is not None else None
    return AudioAnalysis(
        path=str(audio_path),
        duration_seconds=float(duration),
        rms_db=_db(rms),
        peak_db=_db(peak),
        clipping_ratio=float(np.mean(np.abs(samples) >= 0.98)),
        silence_ratio=float(np.mean(np.abs(samples) <= 0.005)),
        low_band_ratio=_band_ratio(samples, DEFAULT_SR),
        spectral_flatness=_spectral_flatness(samples),
        f0_median_hz=f0_median,
        f0_p10_hz=f0_p10,
        f0_p25_hz=f0_p25,
        f0_min_hz=f0_min,
        voiced_ratio=voiced_ratio,
        hnr_db=praat.get("hnr_db"),
        jitter_local=praat.get("jitter_local"),
        shimmer_local=praat.get("shimmer_local"),
        transcribed_text=transcribed_text,
        asr_cer=asr_cer,
        tools={"ffmpeg": "ok", "praat_parselmouth": praat_status},
    )


def _semitones(candidate: float | None, anchor: float | None) -> float | None:
    if not candidate or not anchor or candidate <= 0 or anchor <= 0:
        return None
    return 12.0 * math.log2(candidate / anchor)


def score_analysis(analysis: AudioAnalysis, anchor: AudioAnalysis | None = None) -> tuple[float, list[str]]:
    score = 100.0
    flags: list[str] = []
    if analysis.duration_seconds < 0.5 or analysis.duration_seconds > 12.0:
        score -= 35
        flags.append("bad duration")
    if analysis.rms_db < -36:
        score -= 18
        flags.append("too quiet")
    if analysis.peak_db > -0.5 or analysis.clipping_ratio > 0.0005:
        score -= 25
        flags.append("clipping risk")
    if analysis.silence_ratio > 0.45:
        score -= 18
        flags.append("silence/dropout high")
    if analysis.voiced_ratio < 0.28:
        score -= 18
        flags.append("low voiced ratio")
    if analysis.hnr_db is not None and analysis.hnr_db < 5:
        score -= 15
        flags.append("low harmonicity/noisy voice")
    if analysis.jitter_local is not None and analysis.jitter_local > 0.035:
        score -= 10
        flags.append("jitter high")
    if analysis.shimmer_local is not None and analysis.shimmer_local > 0.18:
        score -= 10
        flags.append("shimmer high")
    if anchor:
        med = _semitones(analysis.f0_median_hz, anchor.f0_median_hz)
        low = _semitones(analysis.f0_p10_hz, anchor.f0_p10_hz)
        if med is not None and med < -2.0:
            score -= min(30, abs(med + 2.0) * 8)
            flags.append(f"median pitch {med:.1f} st below anchor")
        if low is not None and low < -3.0:
            score -= min(40, abs(low + 3.0) * 8)
            flags.append(f"low-tail pitch {low:.1f} st below anchor")
        if analysis.low_band_ratio > max(anchor.low_band_ratio * 2.2, 0.23):
            score -= 14
            flags.append("low-band mud high")
        if analysis.spectral_flatness > max(anchor.spectral_flatness * 1.35, 0.45):
            score -= 12
            flags.append("spectral flatness high")
    elif analysis.f0_p10_hz is not None and analysis.f0_p10_hz < 170:
        score -= 20
        flags.append("low-tail pitch risk")
    if analysis.asr_cer is not None:
        if analysis.asr_cer > 0.45:
            score -= 45
            flags.append(f"ASR CER high {analysis.asr_cer:.2f}")
        elif analysis.asr_cer > 0.25:
            score -= 22
            flags.append(f"ASR CER medium {analysis.asr_cer:.2f}")
        elif analysis.asr_cer > 0.12:
            score -= 8
            flags.append(f"ASR CER mild {analysis.asr_cer:.2f}")
    return max(0.0, min(100.0, score)), flags or ["auto gate ok"]


def pick_best_candidate(
    paths: Iterable[str | Path],
    *,
    anchor_path: str | Path | None = None,
    target_text: str = "",
    transcriber: Any | None = None,
    asr_language: str = "ko",
) -> BestPickResult:
    anchor = analyze_audio(anchor_path) if anchor_path else None
    ranked: list[ScoredCandidate] = []
    for path in paths:
        candidate_path = Path(path)
        transcript = transcriber(candidate_path, asr_language) if transcriber and target_text else None
        analysis = analyze_audio(candidate_path, target_text=target_text, transcribed_text=transcript)
        score, flags = score_analysis(analysis, anchor)
        ranked.append(ScoredCandidate(path=analysis.path, score=round(score, 2), flags=flags, analysis=analysis))
    if not ranked:
        raise ValueError("no candidates to rank")
    ranked.sort(key=lambda item: item.score, reverse=True)
    return BestPickResult(best=ranked[0], ranked=ranked, anchor=anchor, target_text=target_text)


def create_faster_whisper_transcriber(model_name: str, *, device: str = "auto", compute_type: str = "auto") -> Any:
    from faster_whisper import WhisperModel

    model = WhisperModel(model_name, device=device, compute_type=compute_type)

    def transcribe(path: Path, language: str) -> str:
        segments, _info = model.transcribe(str(path), language=language or None, beam_size=1, vad_filter=True)
        return "".join(segment.text.strip() for segment in segments)

    return transcribe


def collect_audio_files(input_dir: str | Path) -> list[Path]:
    root = Path(input_dir)
    files = sorted(root.rglob("*.ogg")) + sorted(root.rglob("*.wav"))
    result: list[Path] = []
    for path in files:
        lowered = str(path).lower()
        if "hp120_norm" in lowered or "keep_reference" in lowered or "top3" in lowered or "auto_rank" in lowered:
            continue
        result.append(path)
    return result


def write_best_pick(result: BestPickResult, output_dir: str | Path) -> dict[str, Any]:
    out = Path(output_dir)
    best_dir = out / "best"
    best_dir.mkdir(parents=True, exist_ok=True)
    src = Path(result.best.path)
    best_copy = best_dir / src.name
    shutil.copy2(src, best_copy)
    payload = {
        "ok": True,
        "best": {**asdict(result.best), "copied_path": str(best_copy)},
        "ranked": [asdict(item) for item in result.ranked],
        "anchor": asdict(result.anchor) if result.anchor else None,
        "target_text": result.target_text,
    }
    (out / "best_selection.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# Voice best candidate selection", "", f"Best: `{src.name}`", "", f"Score: {result.best.score:.1f}", "", "## Ranked", ""]
    lines.append("| rank | score | file | flags |")
    lines.append("|---:|---:|---|---|")
    for rank, item in enumerate(result.ranked, start=1):
        lines.append(f"| {rank} | {item.score:.1f} | `{Path(item.path).name}` | {'; '.join(item.flags)} |")
    (out / "best_selection.md").write_text("\n".join(lines), encoding="utf-8")
    return payload
