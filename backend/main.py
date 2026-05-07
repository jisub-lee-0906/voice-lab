from __future__ import annotations

from pathlib import Path
import shutil
import time

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from voice_lab.audio import build_clip_path, cut_reference, probe_duration
from voice_lab.core import normalize_emotion, sanitize_id, validate_reference_duration
from voice_lab.gptsovits import DEFAULT_API_URL, start_api, wait_for_api
from voice_lab.ui_config import EMOTION_BUTTONS, LANGUAGE_PRESETS
from voice_lab.workflow import generate_candidates

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPO = ROOT / "references" / "GPT-SoVITS"
DEFAULT_PYTHON = ROOT / ".venv-gpt-sovits" / "bin" / "python"
UPLOADS_DIR = ROOT / "refs" / "uploads"
MEDIA_DIRS = [ROOT / "refs", ROOT / "generated", ROOT / "approved", ROOT / "exports"]
API_PROCESS = None

app = FastAPI(title="Voice Lab API")
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
    voice_name: str = "default"
    emotion: str = "기본"
    line_id: str = "line_001"
    text: str = Field(min_length=1)
    text_lang: str = "auto"
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


class SaveRequest(BaseModel):
    source_path: str
    voice_name: str = "default"
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


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


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
    voice_name: str = Form("default"),
    emotion: str = Form("기본"),
    start_seconds: float = Form(0.0),
    duration_seconds: float = Form(9.5),
    existing_path: str = Form(""),
    audio_file: UploadFile | None = File(None),
):
    validate_reference_duration(duration_seconds)
    source: Path
    if audio_file is not None and audio_file.filename:
        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        filename = sanitize_id(Path(audio_file.filename).stem) + Path(audio_file.filename).suffix.lower()
        source = UPLOADS_DIR / f"{int(time.time())}_{filename}"
        with source.open("wb") as out:
            shutil.copyfileobj(audio_file.file, out)
    elif existing_path.strip():
        source = Path(existing_path.strip()).expanduser()
    else:
        raise HTTPException(status_code=400, detail="음성 파일을 업로드하거나 기존 파일 경로를 입력하세요.")
    if not source.exists():
        raise HTTPException(status_code=404, detail=f"음성 파일이 없습니다: {source}")
    ref_path = build_clip_path(ROOT, voice_name, emotion, source)
    cut_reference(source, ref_path, start_seconds, duration_seconds)
    duration = probe_duration(ref_path)
    return ReferenceResponse(
        path=str(ref_path),
        url=media_url(ref_path),
        duration=duration,
        emotion=normalize_emotion(emotion),
        message="참조 클립을 만들었습니다.",
    )


@app.post("/api/generate", response_model=GenerateResponse)
def generate(request: GenerateRequest):
    ref_audio = Path(request.ref_audio_path).expanduser()
    if not ref_audio.exists():
        raise HTTPException(status_code=404, detail=f"참조 WAV가 없습니다: {ref_audio}")
    prompt_text = request.prompt_text.strip() or request.text
    line_id = request.line_id.strip() or f"line_{int(time.time())}"
    api_status = ensure_api(request.api_url or DEFAULT_API_URL, request.autostart_api)
    results = generate_candidates(
        root=ROOT,
        character=request.voice_name or "default",
        emotion=request.emotion,
        line_id=line_id,
        text=request.text,
        text_lang=request.text_lang,
        ref_audio=ref_audio,
        prompt_text=prompt_text,
        prompt_lang=request.prompt_lang,
        base_seed=request.base_seed,
        count=request.candidate_count,
        api_url=request.api_url or DEFAULT_API_URL,
    )
    candidates = [
        Candidate(index=i, seed=item["seed"], wav=item["wav"], ogg=item["ogg"], url=media_url(item["ogg"]))
        for i, item in enumerate(results, start=1)
    ]
    return GenerateResponse(message=api_status, candidates=candidates)


@app.post("/api/save", response_model=SaveResponse)
def save(request: SaveRequest):
    source = Path(request.source_path).expanduser()
    if not source.exists():
        raise HTTPException(status_code=404, detail=f"음성 파일이 없습니다: {source}")
    dest = ROOT / "approved" / sanitize_id(request.voice_name or "default") / f"{sanitize_id(request.line_id or source.stem)}.ogg"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)
    return SaveResponse(path=str(dest), url=media_url(dest), message="마음에 드는 음성을 저장했습니다.")
