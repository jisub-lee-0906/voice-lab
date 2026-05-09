from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import requests
import yaml

from voice_lab.analysis import collect_audio_files, create_faster_whisper_transcriber, load_feedback_labels, pick_best_candidate, write_best_pick

DEFAULT_BACKEND = "http://127.0.0.1:8100"
DEFAULT_GPTSOVITS = "http://127.0.0.1:9100"


def _url(base: str, path: str) -> str:
    return f"{base.rstrip('/')}/{path.lstrip('/')}"


def _print_json(data: dict[str, Any]) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _response_payload(response: requests.Response) -> dict[str, Any]:
    try:
        data = response.json()
        if isinstance(data, dict):
            return data
        return {"data": data}
    except Exception:
        return {"text": response.text}


def _handle_response(response: requests.Response) -> int:
    payload = _response_payload(response)
    if response.ok:
        _print_json(payload)
        return 0
    detail = payload.get("detail") or payload.get("text") or response.text or response.reason
    _print_json({"ok": False, "status_code": response.status_code, "detail": detail})
    return 1


def _probe(url: str, timeout: float) -> dict[str, Any]:
    try:
        response = requests.get(url, timeout=timeout)
        return {"ok": response.ok, "status_code": response.status_code, "url": url}
    except Exception as exc:
        return {"ok": False, "url": url, "error": str(exc)}


def cmd_doctor(args: argparse.Namespace) -> int:
    try:
        response = requests.get(_url(args.backend, "/api/runtime"), timeout=args.timeout)
        payload = _response_payload(response)
        _print_json(payload)
        return 0 if response.ok and payload.get("ok") is True else 1
    except Exception as exc:
        _print_json({"ok": False, "detail": str(exc)})
        return 1


def cmd_status(args: argparse.Namespace) -> int:
    backend = _probe(_url(args.backend, "/api/health"), args.timeout)
    gptsovits = _probe(_url(args.gptsovits, "/docs"), args.timeout)
    data = {"ok": bool(backend["ok"] and gptsovits["ok"]), "backend": backend, "gptsovits": gptsovits}
    _print_json(data)
    return 0 if data["ok"] else 1


def cmd_reference(args: argparse.Namespace) -> int:
    data = {
        "voice_name": args.voice,
        "emotion": args.emotion,
        "start_seconds": str(args.start),
        "duration_seconds": str(args.duration),
        "existing_path": args.existing_path or "",
    }
    files = None
    file_handle = None
    try:
        if args.file:
            path = Path(args.file).expanduser()
            file_handle = path.open("rb")
            files = {"audio_file": (path.name, file_handle)}
        kwargs: dict[str, Any] = {"data": data, "timeout": args.timeout}
        if files is not None:
            kwargs["files"] = files
        response = requests.post(_url(args.backend, "/api/reference"), **kwargs)
        return _handle_response(response)
    except Exception as exc:
        _print_json({"ok": False, "detail": str(exc)})
        return 1
    finally:
        if file_handle is not None:
            file_handle.close()


def cmd_generate(args: argparse.Namespace) -> int:
    payload = {
        "ref_audio_path": args.ref,
        "voice_name": args.voice,
        "emotion": args.emotion,
        "line_id": args.line_id,
        "text": args.text,
        "prompt_text": args.prompt_text or "",
        "candidate_count": args.candidates,
        "base_seed": args.seed,
        "text_lang": args.text_lang,
        "prompt_lang": args.prompt_lang,
        "autostart_api": not args.no_autostart,
    }
    try:
        response = requests.post(_url(args.backend, "/api/generate"), json=payload, timeout=args.timeout)
        return _handle_response(response)
    except Exception as exc:
        _print_json({"ok": False, "detail": str(exc)})
        return 1


def cmd_save(args: argparse.Namespace) -> int:
    payload = {"source_path": args.source, "voice_name": args.voice, "line_id": args.line_id}
    try:
        response = requests.post(_url(args.backend, "/api/save"), json=payload, timeout=args.timeout)
        return _handle_response(response)
    except Exception as exc:
        _print_json({"ok": False, "detail": str(exc)})
        return 1


def _add_common_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--backend", default=DEFAULT_BACKEND, help="voice-lab FastAPI origin, default: %(default)s")
    parser.add_argument("--timeout", type=float, default=300.0, help="HTTP timeout seconds")


def _load_batch(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    if isinstance(data, dict):
        lines = data.get("lines") or data.get("items") or []
    else:
        lines = data
    if not isinstance(lines, list):
        raise ValueError("batch input must be a list or an object with a lines/items list")
    return [dict(item) for item in lines]


def _generate_payload_from_item(args: argparse.Namespace, item: dict[str, Any], index: int) -> dict[str, Any]:
    return {
        "ref_audio_path": item.get("ref_audio_path") or item.get("ref") or args.ref,
        "voice_name": item.get("voice_name") or item.get("voice") or args.voice,
        "emotion": item.get("emotion") or args.emotion,
        "line_id": item.get("line_id") or item.get("id") or f"line_{index:04d}",
        "text": item.get("text") or item.get("dialogue") or "",
        "prompt_text": item.get("prompt_text") or "",
        "candidate_count": int(item.get("candidate_count") or args.candidates),
        "base_seed": int(item.get("base_seed") or args.seed + index - 1),
        "text_lang": item.get("text_lang") or args.text_lang,
        "prompt_lang": item.get("prompt_lang") or args.prompt_lang,
        "autostart_api": not args.no_autostart,
    }


def cmd_batch_generate(args: argparse.Namespace) -> int:
    try:
        lines = _load_batch(Path(args.input).expanduser())
        items: list[dict[str, Any]] = []
        for index, item in enumerate(lines, start=1):
            payload = _generate_payload_from_item(args, item, index)
            if not payload["ref_audio_path"]:
                raise ValueError(f"{payload['line_id']}: ref_audio_path is required")
            if not payload["text"]:
                raise ValueError(f"{payload['line_id']}: text is required")
            response = requests.post(_url(args.backend, "/api/generate"), json=payload, timeout=args.timeout)
            response_payload = _response_payload(response)
            if not response.ok:
                detail = response_payload.get("detail") or response_payload.get("text") or response.text
                raise RuntimeError(f"{payload['line_id']}: {detail}")
            items.append({"line_id": payload["line_id"], "text": payload["text"], "voice_name": payload["voice_name"], "emotion": payload["emotion"], "result": response_payload})
        manifest = {"ok": True, "items": items}
        if args.manifest:
            manifest_path = Path(args.manifest).expanduser()
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            manifest["manifest"] = str(manifest_path)
        _print_json(manifest)
        return 0
    except Exception as exc:
        _print_json({"ok": False, "detail": str(exc)})
        return 1


def cmd_pick_best(args: argparse.Namespace) -> int:
    try:
        candidates = collect_audio_files(args.input_dir)
        transcriber = None
        if args.asr_model:
            transcriber = create_faster_whisper_transcriber(args.asr_model, device=args.asr_device, compute_type=args.asr_compute_type)
        result = pick_best_candidate(
            candidates,
            anchor_path=args.anchor,
            target_text=args.target_text,
            transcriber=transcriber,
            asr_language=args.asr_language,
            feedback_labels=load_feedback_labels(args.feedback_labels),
        )
        payload = write_best_pick(result, args.output_dir)
        _print_json({"ok": True, "best": payload["best"], "output_dir": str(Path(args.output_dir).expanduser())})
        return 0
    except Exception as exc:
        _print_json({"ok": False, "detail": str(exc)})
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="voice-lab", description="Agent-friendly CLI for the local voice-lab FastAPI service.")
    _add_common_options(parser)
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="Check production readiness details from backend /api/runtime")
    _add_common_options(doctor)
    doctor.set_defaults(func=cmd_doctor)

    status = subparsers.add_parser("status", help="Check backend and GPT-SoVITS health")
    _add_common_options(status)
    status.add_argument("--gptsovits", default=DEFAULT_GPTSOVITS, help="GPT-SoVITS API origin, default: %(default)s")
    status.set_defaults(func=cmd_status)

    reference = subparsers.add_parser("reference", help="Create a 3-10 second reference WAV")
    _add_common_options(reference)
    reference.add_argument("--file", default="", help="Audio file to upload")
    reference.add_argument("--existing-path", default="", help="Existing audio path visible to the backend")
    reference.add_argument("--start", default="0", help="Start seconds")
    reference.add_argument("--duration", default="9.5", help="Clip duration seconds")
    reference.add_argument("--voice", default="default", help="Voice/profile id")
    reference.add_argument("--emotion", default="기본", help="Emotion/variant label")
    reference.set_defaults(func=cmd_reference)

    generate = subparsers.add_parser("generate", help="Generate voice candidates from a reference WAV")
    _add_common_options(generate)
    generate.add_argument("--ref", required=True, help="Reference WAV path returned by reference")
    generate.add_argument("--text", required=True, help="Target dialogue to read")
    generate.add_argument("--prompt-text", default="", help="Actual transcript of the reference clip; leave blank if unknown")
    generate.add_argument("--voice", default="default", help="Voice/profile id")
    generate.add_argument("--emotion", default="기본", help="Emotion/variant label")
    generate.add_argument("--line-id", default="line_001", help="Stable dialogue/asset id")
    generate.add_argument("--candidates", type=int, default=3, help="Number of candidates, 1-5")
    generate.add_argument("--seed", type=int, default=1000, help="Base seed")
    generate.add_argument("--text-lang", default="ko", help="Target text language; default Korean")
    generate.add_argument("--prompt-lang", default="auto", help="Reference transcript language")
    generate.add_argument("--no-autostart", action="store_true", help="Do not ask backend to autostart GPT-SoVITS")
    generate.set_defaults(func=cmd_generate)

    save = subparsers.add_parser("save", help="Promote a generated take into approved assets")
    _add_common_options(save)
    save.add_argument("--source", required=True, help="Generated OGG/WAV path to save")
    save.add_argument("--voice", default="default", help="Voice/profile id")
    save.add_argument("--line-id", default="line_001", help="Stable dialogue/asset id")
    save.set_defaults(func=cmd_save)
    batch = subparsers.add_parser("batch-generate", help="Generate many dialogue lines from a JSON/YAML manifest")
    _add_common_options(batch)
    batch.add_argument("--input", required=True, help="JSON/YAML with lines/items list")
    batch.add_argument("--manifest", default="", help="Optional JSON output manifest path")
    batch.add_argument("--ref", default="", help="Default reference WAV path for lines without ref_audio_path")
    batch.add_argument("--voice", default="default", help="Default voice/profile id")
    batch.add_argument("--emotion", default="기본", help="Default emotion/variant label")
    batch.add_argument("--candidates", type=int, default=3, help="Default candidates per line, 1-5")
    batch.add_argument("--seed", type=int, default=1000, help="Base seed; each line increments by one unless overridden")
    batch.add_argument("--text-lang", default="ko", help="Default target text language")
    batch.add_argument("--prompt-lang", default="auto", help="Default reference transcript language")
    batch.add_argument("--no-autostart", action="store_true", help="Do not ask backend to autostart GPT-SoVITS")
    batch.set_defaults(func=cmd_batch_generate)

    pick_best = subparsers.add_parser("pick-best", help="Analyze candidates and copy the single best take")
    pick_best.add_argument("--input-dir", required=True, help="Directory containing candidate .ogg/.wav files")
    pick_best.add_argument("--anchor", required=True, help="Known good anchor/reference take")
    pick_best.add_argument("--target-text", default="", help="Target dialogue text for reporting/future ASR checks")
    pick_best.add_argument("--output-dir", required=True, help="Directory for best_selection.json and best/ copy")
    pick_best.add_argument("--asr-model", default="", help="Optional faster-whisper model name/path for content/CER gate, e.g. tiny or small")
    pick_best.add_argument("--asr-language", default="ko", help="ASR language code, default: ko")
    pick_best.add_argument("--asr-device", default="auto", help="faster-whisper device, default: auto")
    pick_best.add_argument("--asr-compute-type", default="auto", help="faster-whisper compute_type, default: auto")
    pick_best.add_argument("--feedback-labels", default="", help="Optional YAML with human feedback labels/penalties")
    pick_best.set_defaults(func=cmd_pick_best)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
