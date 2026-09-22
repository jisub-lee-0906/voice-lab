from __future__ import annotations

from pathlib import Path
import subprocess
import time
from typing import Any

import requests


DEFAULT_API_URL = "http://127.0.0.1:9100"


def generate_seeds(base_seed: int, count: int) -> list[int]:
    count = max(1, int(count))
    return [int(base_seed) + i for i in range(count)]


def build_tts_payload(
    *,
    text: str,
    text_lang: str,
    ref_audio_path: Path,
    prompt_text: str,
    prompt_lang: str,
    seed: int,
    speed_factor: float = 1.0,
    repetition_penalty: float = 1.35,
    text_split_method: str = "cut5",
) -> dict[str, Any]:
    return {
        "text": text,
        "text_lang": text_lang,
        "ref_audio_path": str(Path(ref_audio_path)),
        "prompt_text": prompt_text,
        "prompt_lang": prompt_lang,
        "text_split_method": text_split_method,
        "batch_size": 1,
        "media_type": "wav",
        "streaming_mode": False,
        "seed": int(seed),
        "parallel_infer": False,
        "repetition_penalty": float(repetition_penalty),
        "speed_factor": float(speed_factor),
    }


def wait_for_api(api_url: str = DEFAULT_API_URL, timeout_seconds: float = 90.0) -> None:
    deadline = time.time() + timeout_seconds
    last_error = None
    while time.time() < deadline:
        try:
            response = requests.get(f"{api_url.rstrip('/')}/docs", timeout=2, allow_redirects=False)
            if 300 <= response.status_code < 400:
                last_error = RuntimeError(f"GPT-SoVITS API redirect is not allowed (HTTP {response.status_code})")
            elif response.ok:
                return
        except requests.RequestException as exc:
            last_error = exc
        time.sleep(1)
    raise TimeoutError(f"GPT-SoVITS API did not become ready: {last_error}")


def start_api(repo_dir: Path, python_bin: Path, host: str = "127.0.0.1", port: int = 9100) -> subprocess.Popen:
    command = [
        str(python_bin),
        "api_v2.py",
        "-a",
        host,
        "-p",
        str(port),
        "-c",
        "GPT_SoVITS/configs/tts_infer.yaml",
    ]
    return subprocess.Popen(
        command,
        cwd=str(repo_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def synthesize_to_wav(payload: dict[str, Any], output_wav: Path, api_url: str = DEFAULT_API_URL) -> Path:
    output_wav.parent.mkdir(parents=True, exist_ok=True)
    response = requests.post(f"{api_url.rstrip('/')}/tts", json=payload, timeout=300, allow_redirects=False)
    if 300 <= response.status_code < 400:
        raise RuntimeError(f"GPT-SoVITS API redirect is not allowed (HTTP {response.status_code})")
    if not response.ok:
        raise RuntimeError(f"GPT-SoVITS request failed HTTP {response.status_code}: {response.text[:500]}")
    output_wav.write_bytes(response.content)
    return output_wav
