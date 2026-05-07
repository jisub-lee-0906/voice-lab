from __future__ import annotations

from pathlib import Path
import json
import subprocess

from .core import normalize_emotion, sanitize_id, validate_reference_duration


def build_clip_path(root: Path, character: str, emotion: str, source_path: Path) -> Path:
    source_stem = sanitize_id(Path(source_path).stem)
    return Path(root) / "refs" / sanitize_id(character) / normalize_emotion(emotion) / f"{source_stem}_ref.wav"


def ffmpeg_cut_command(source: Path, output_wav: Path, start_seconds: float, duration_seconds: float) -> list[str]:
    return [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        str(float(start_seconds)),
        "-t",
        str(float(duration_seconds)),
        "-i",
        str(source),
        "-ac",
        "1",
        "-ar",
        "32000",
        str(output_wav),
    ]


def ffmpeg_ogg_command(source_wav: Path, output_ogg: Path) -> list[str]:
    return [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(source_wav),
        "-c:a",
        "libvorbis",
        "-q:a",
        "5",
        str(output_ogg),
    ]


def run_command(command: list[str]) -> None:
    subprocess.run(command, check=True)


def cut_reference(source: Path, output_wav: Path, start_seconds: float, duration_seconds: float) -> Path:
    validate_reference_duration(duration_seconds)
    output_wav.parent.mkdir(parents=True, exist_ok=True)
    run_command(ffmpeg_cut_command(source, output_wav, start_seconds, duration_seconds))
    return output_wav


def convert_to_ogg(source_wav: Path, output_ogg: Path) -> Path:
    output_ogg.parent.mkdir(parents=True, exist_ok=True)
    run_command(ffmpeg_ogg_command(source_wav, output_ogg))
    return output_ogg


def probe_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    return float(data["format"]["duration"])
