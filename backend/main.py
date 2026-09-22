from __future__ import annotations

from pathlib import Path
import math
import os
import shutil
import time
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from voice_lab.audio import build_clip_path, cut_reference, probe_duration
from voice_lab.core import normalize_emotion, sanitize_id, validate_reference_duration
from voice_lab.gptsovits import DEFAULT_API_URL, start_api, wait_for_api
from voice_lab.ui_config import EMOTION_BUTTONS, LANGUAGE_PRESETS
from voice_lab.validation import DialogueValidationError, validate_generation_inputs
from voice_lab.workflow import generate_candidates

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPO = ROOT / "references" / "GPT-SoVITS"
DEFAULT_PYTHON = ROOT / ".venv-gpt-sovits" / "bin" / "python"
UPLOADS_DIR = ROOT / "refs" / "uploads"
GENERATED_DIR = ROOT / "generated"
MEDIA_DIRS = [ROOT / "refs", GENERATED_DIR, ROOT / "approved", ROOT / "exports"]
MAX_UPLOAD_BYTES = int(os.environ.get("VOICE_LAB_MAX_UPLOAD_BYTES", str(100 * 1024 * 1024)))
API_PROCESS = None


def allowed_api_urls() -> set[str]:
    """Return server-configured GPT-SoVITS endpoints, normalized without a trailing slash."""
    configured = os.environ.get("VOICE_LAB_ALLOWED_API_URLS", "")
    return {DEFAULT_API_URL.rstrip("/"), *(url.strip().rstrip("/") for url in configured.split(",") if url.strip())}


def resolve_api_url(value: str) -> str:
    api_url = (value or DEFAULT_API_URL).strip().rstrip("/")
    if api_url not in allowed_api_urls():
        raise HTTPException(
            status_code=400,
            detail="허용되지 않은 GPT-SoVITS API 주소입니다. 외부 주소는 VOICE_LAB_ALLOWED_API_URLS 서버 환경설정에 명시하세요.",
        )
    return api_url


def upload_limit_detail() -> str:
    return f"참조 요청 본문은 multipart 형식 오버헤드를 포함해 {MAX_UPLOAD_BYTES}바이트를 넘을 수 없습니다."


def save_upload_with_limit(upload: UploadFile, destination: Path) -> Path:
    written = 0
    try:
        with destination.open("wb") as out:
            while chunk := upload.file.read(1024 * 1024):
                written += len(chunk)
                if written > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail=upload_limit_detail())
                out.write(chunk)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return destination


class ReferenceBodyLimitMiddleware:
    """Reject an oversized reference request before multipart parsing can spool it to disk."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] != "POST" or scope["path"] != "/api/reference":
            await self.app(scope, receive, send)
            return
        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        try:
            content_length = int(headers.get(b"content-length", b"0"))
        except ValueError:
            content_length = 0
        if content_length > MAX_UPLOAD_BYTES:
            await JSONResponse(status_code=413, content={"detail": upload_limit_detail()})(scope, receive, send)
            return

        messages = []
        received = 0
        while True:
            message = await receive()
            if message["type"] != "http.request":
                messages.append(message)
                break
            received += len(message.get("body", b""))
            if received > MAX_UPLOAD_BYTES:
                await JSONResponse(status_code=413, content={"detail": upload_limit_detail()})(scope, receive, send)
                return
            messages.append(message)
            if not message.get("more_body", False):
                break

        async def replay_receive():
            if messages:
                return messages.pop(0)
            return {"type": "http.request", "body": b"", "more_body": False}

        await self.app(scope, replay_receive, send)


app = FastAPI(title="Voice Lab API")
app.add_middleware(ReferenceBodyLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3100", "http://localhost:3100"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
for path in MEDIA_DIRS:
    path.mkdir(parents=True, exist_ok=True)
app.mount("/media/refs", StaticFiles(directory=ROOT / "refs"), name="media_refs")
app.mount("/media/generated", StaticFiles(directory=ROOT / "generated"), name="media_generated")
app.mount("/media/approved", StaticFiles(directory=ROOT / "approved"), name="media_approved")
app.mount("/media/exports", StaticFiles(directory=ROOT / "exports"), name="media_exports")


class ReferenceResponse(BaseModel):
    path: str
    url: str
    duration: float
    emotion: str
    message: str


class GenerateRequest(BaseModel):
    ref_audio_path: str
    voice_name: str = "tsundere"
    emotion: str = "츤츤"
    line_id: str = "line_001"
    text: str = Field(min_length=1)
    text_lang: str = "ko"
    prompt_text: str = ""
    prompt_lang: str = "auto"
    base_seed: int = 1000
    candidate_count: int = Field(default=3, ge=1, le=5)
    api_url: str = DEFAULT_API_URL
    autostart_api: bool = True


class Candidate(BaseModel):
    index: int
    seed: int
    wav: str
    ogg: str
    url: str


class GenerateResponse(BaseModel):
    message: str
    candidates: list[Candidate]
    warnings: list[str] = Field(default_factory=list)


class SaveRequest(BaseModel):
    source_path: str
    voice_name: str = "tsundere"
    line_id: str = "line_001"


class SaveResponse(BaseModel):
    path: str
    url: str
    message: str


def media_url(path: str | Path) -> str:
    resolved = Path(path).resolve()
    for base, prefix in [
        ((ROOT / "refs").resolve(), "/media/refs"),
        ((ROOT / "generated").resolve(), "/media/generated"),
        ((ROOT / "approved").resolve(), "/media/approved"),
        ((ROOT / "exports").resolve(), "/media/exports"),
    ]:
        try:
            rel = resolved.relative_to(base)
            return f"{prefix}/{rel.as_posix()}"
        except ValueError:
            continue
    return str(path)


def validate_reference_window(source: Path, start_seconds: float, duration_seconds: float) -> None:
    try:
        start = float(start_seconds)
        duration = float(duration_seconds)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="시작 초와 길이 초는 숫자로 입력하세요.") from exc
    if not math.isfinite(start) or start < 0:
        raise HTTPException(status_code=400, detail="시작 초는 유한한 0 이상의 숫자여야 합니다.")
    try:
        validate_reference_duration(duration)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="길이 초는 3~10초 사이여야 합니다.") from exc
    try:
        source_duration = probe_duration(source)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"원본 음성 길이를 확인하지 못했습니다: {exc}") from exc
    end = start + duration
    if start >= source_duration:
        raise HTTPException(status_code=400, detail=f"시작 초가 파일 길이({source_duration:.2f}초)를 넘어갑니다.")
    if end > source_duration:
        raise HTTPException(status_code=400, detail=f"선택한 구간 끝({end:.2f}초)이 파일 길이({source_duration:.2f}초)를 넘어갑니다.")


def normalize_generation_request(request: GenerateRequest) -> dict[str, Any]:
    try:
        return validate_generation_inputs(
            text=request.text,
            prompt_text=request.prompt_text,
            text_lang=request.text_lang,
            prompt_lang=request.prompt_lang,
            ref_audio_path=Path(request.ref_audio_path),
        )
    except DialogueValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def ensure_api(api_url: str, autostart: bool) -> str:
    global API_PROCESS
    try:
        wait_for_api(api_url, timeout_seconds=3)
        return "GPT-SoVITS API 준비 완료"
    except Exception:
        if not autostart:
            raise HTTPException(status_code=503, detail="GPT-SoVITS API가 실행 중이 아닙니다.")
    if not DEFAULT_REPO.exists():
        raise HTTPException(status_code=500, detail=f"GPT-SoVITS repo를 찾을 수 없습니다: {DEFAULT_REPO}")
    if not DEFAULT_PYTHON.exists():
        raise HTTPException(status_code=500, detail=f"GPT-SoVITS Python을 찾을 수 없습니다: {DEFAULT_PYTHON}")
    API_PROCESS = start_api(DEFAULT_REPO, DEFAULT_PYTHON)
    wait_for_api(api_url, timeout_seconds=120)
    return "GPT-SoVITS API 자동 실행 완료"


def runtime_status(api_url: str = DEFAULT_API_URL) -> dict[str, Any]:
    paths = {
        "gptsovits_repo": str(DEFAULT_REPO),
        "gptsovits_python": str(DEFAULT_PYTHON),
        "refs": str(ROOT / "refs"),
        "generated": str(ROOT / "generated"),
        "approved": str(ROOT / "approved"),
    }
    path_checks = {name: {"path": path, "exists": Path(path).exists()} for name, path in paths.items()}
    try:
        wait_for_api(api_url, timeout_seconds=3)
        gptsovits = {"ok": True, "url": api_url}
    except Exception as exc:
        gptsovits = {"ok": False, "url": api_url, "error": str(exc)}
    usage = shutil.disk_usage(ROOT)
    disk = {"root": str(ROOT), "free_bytes": usage.free, "total_bytes": usage.total, "ok": usage.free > 1_000_000_000}
    ok = bool(gptsovits["ok"] and disk["ok"] and all(item["exists"] for item in path_checks.values()))
    return {"ok": ok, "backend": {"ok": True}, "gptsovits": gptsovits, "paths": path_checks, "disk": disk}


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/runtime")
def runtime() -> dict[str, Any]:
    return runtime_status()


@app.get("/api/config")
def config() -> dict:
    return {
        "emotions": EMOTION_BUTTONS,
        "languages": LANGUAGE_PRESETS,
        "defaultApiUrl": DEFAULT_API_URL,
        "referenceDuration": {"min": 3, "max": 10, "default": 9.5},
    }


@app.post("/api/reference", response_model=ReferenceResponse)
def create_reference(
    voice_name: str = Form("tsundere"),
    emotion: str = Form("츤츤"),
    start_seconds: float = Form(0.0),
    duration_seconds: float = Form(9.5),
    existing_path: str = Form(""),
    audio_file: UploadFile | None = File(None),
):
    source: Path
    upload_filename = getattr(audio_file, "filename", "") if audio_file is not None else ""
    if audio_file is not None and upload_filename:
        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        filename = sanitize_id(Path(upload_filename).stem) + Path(upload_filename).suffix.lower()
        source = UPLOADS_DIR / f"{int(time.time())}_{filename}"
        save_upload_with_limit(audio_file, source)
    elif existing_path.strip():
        source = Path(existing_path.strip()).expanduser()
    else:
        raise HTTPException(status_code=400, detail="음성 파일을 업로드하거나 기존 파일 경로를 입력하세요.")
    if not source.exists():
        raise HTTPException(status_code=404, detail=f"음성 파일이 없습니다: {source}")
    validate_reference_window(source, start_seconds, duration_seconds)
    try:
        ref_path = build_clip_path(ROOT, voice_name, emotion, source)
        cut_reference(source, ref_path, start_seconds, duration_seconds)
        duration = probe_duration(ref_path)
        try:
            validate_reference_duration(duration)
        except ValueError as exc:
            raise HTTPException(status_code=500, detail=f"실제 참조 길이({duration:.2f}초)가 GPT-SoVITS 허용 범위(3~10초)를 벗어났습니다. 시작 초와 길이 초를 다시 조정하세요.") from exc
        return ReferenceResponse(
            path=str(ref_path),
            url=media_url(ref_path),
            duration=duration,
            emotion=normalize_emotion(emotion),
            message="참조 클립을 만들었습니다.",
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"참조 음성을 만들지 못했습니다: {exc}") from exc


@app.post("/api/generate", response_model=GenerateResponse)
def generate(request: GenerateRequest):
    ref_audio = Path(request.ref_audio_path).expanduser()
    normalized = normalize_generation_request(request)
    api_url = resolve_api_url(request.api_url)
    line_id = request.line_id.strip() or f"line_{int(time.time())}"
    try:
        api_status = ensure_api(api_url, request.autostart_api)
        results = generate_candidates(
            root=ROOT,
            character=request.voice_name or "tsundere",
            emotion=request.emotion,
            line_id=line_id,
            text=normalized["text"],
            text_lang=normalized["text_lang"],
            ref_audio=ref_audio,
            prompt_text=normalized["prompt_text"],
            prompt_lang=normalized["prompt_lang"],
            base_seed=request.base_seed,
            count=request.candidate_count,
            api_url=api_url,
        )
        candidates = [
            Candidate(index=i, seed=item["seed"], wav=item["wav"], ogg=item["ogg"], url=media_url(item["ogg"]))
            for i, item in enumerate(results, start=1)
        ]
        return GenerateResponse(message=api_status, candidates=candidates, warnings=normalized["warnings"])
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"음성 생성에 실패했습니다: {exc}") from exc


@app.post("/api/save", response_model=SaveResponse)
def save(request: SaveRequest):
    source = Path(request.source_path).expanduser().resolve()
    try:
        source.relative_to(GENERATED_DIR.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="생성 폴더의 음성 후보만 저장할 수 있습니다.") from exc
    if not source.is_file() or source.suffix.lower() != ".ogg":
        raise HTTPException(status_code=400, detail="저장할 생성 후보 OGG 파일을 찾을 수 없습니다.")
    try:
        duration = probe_duration(source)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="저장할 생성 후보가 유효한 오디오 파일이 아닙니다.") from exc
    if not math.isfinite(duration) or duration <= 0:
        raise HTTPException(status_code=400, detail="저장할 생성 후보가 유효한 오디오 파일이 아닙니다.")
    dest = ROOT / "approved" / sanitize_id(request.voice_name or "tsundere") / f"{sanitize_id(request.line_id or source.stem)}.ogg"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)
    return SaveResponse(path=str(dest), url=media_url(dest), message="마음에 드는 음성을 저장했습니다.")
