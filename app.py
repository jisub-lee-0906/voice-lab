from __future__ import annotations

from pathlib import Path
import atexit
import os
import shutil
import time

import gradio as gr

from voice_lab.audio import build_clip_path, cut_reference, probe_duration
from voice_lab.core import normalize_emotion, sanitize_id, validate_reference_duration
from voice_lab.gptsovits import DEFAULT_API_URL, start_api, wait_for_api
from voice_lab.ui_config import EMOTION_BUTTONS, LANGUAGE_PRESETS, normalize_language_choice
from voice_lab.workflow import generate_candidates


ROOT = Path(__file__).resolve().parent
DEFAULT_REPO = ROOT / "references" / "GPT-SoVITS"
DEFAULT_PYTHON = ROOT / ".venv-gpt-sovits" / "bin" / "python"
API_PROCESS = None


def _cleanup_api_process() -> None:
    global API_PROCESS
    if API_PROCESS and API_PROCESS.poll() is None:
        API_PROCESS.terminate()


atexit.register(_cleanup_api_process)

def _source_path(uploaded_audio: str | None, existing_path: str | None) -> Path:
    if uploaded_audio:
        return Path(uploaded_audio)
    if existing_path and existing_path.strip():
        return Path(existing_path.strip()).expanduser()
    raise gr.Error("음성 파일을 업로드하거나 기존 파일 경로를 입력하세요.")


def ensure_api(api_url: str, autostart: bool) -> str:
    global API_PROCESS
    try:
        wait_for_api(api_url, timeout_seconds=3)
        return "GPT-SoVITS API: already running"
    except Exception:
        if not autostart:
            raise gr.Error("GPT-SoVITS API가 실행 중이 아닙니다. 자동 실행을 켜거나 API를 먼저 실행하세요.")
    if not DEFAULT_REPO.exists():
        raise gr.Error(f"GPT-SoVITS repo not found: {DEFAULT_REPO}")
    if not DEFAULT_PYTHON.exists():
        raise gr.Error(f"GPT-SoVITS python not found: {DEFAULT_PYTHON}")
    API_PROCESS = start_api(DEFAULT_REPO, DEFAULT_PYTHON)
    wait_for_api(api_url, timeout_seconds=120)
    return "GPT-SoVITS API: started"


def make_reference(
    uploaded_audio: str | None,
    existing_path: str,
    character: str,
    emotion: str,
    start_seconds: float,
    duration_seconds: float,
):
    source = _source_path(uploaded_audio, existing_path)
    validate_reference_duration(duration_seconds)
    if not source.exists():
        raise gr.Error(f"음성 파일이 없습니다: {source}")
    ref_path = build_clip_path(ROOT, character, emotion, source)
    cut_reference(source, ref_path, start_seconds, duration_seconds)
    duration = probe_duration(ref_path)
    return str(ref_path), str(ref_path), f"참조 클립 생성 완료: {ref_path}\n길이: {duration:.2f}s\n감정 라벨: {normalize_emotion(emotion)}"


def generate_voice(
    ref_audio_path: str,
    character: str,
    emotion: str,
    line_id: str,
    text: str,
    text_lang: str,
    prompt_text: str,
    prompt_lang: str,
    base_seed: int,
    candidate_count: int,
    api_url: str,
    autostart_api: bool,
):
    if not ref_audio_path.strip():
        raise gr.Error("먼저 참조 클립을 만들거나 참조 WAV 경로를 입력하세요.")
    ref_audio = Path(ref_audio_path.strip()).expanduser()
    if not ref_audio.exists():
        raise gr.Error(f"참조 WAV가 없습니다: {ref_audio}")
    if not text.strip():
        raise gr.Error("읽을 대사를 입력하세요.")
    if not prompt_text.strip():
        prompt_text = text
    if not line_id.strip():
        line_id = f"line_{int(time.time())}"

    api_status = ensure_api(api_url or DEFAULT_API_URL, autostart_api)
    results = generate_candidates(
        root=ROOT,
        character=character or "default",
        emotion=emotion,
        line_id=line_id,
        text=text,
        text_lang=normalize_language_choice(text_lang),
        ref_audio=ref_audio,
        prompt_text=prompt_text,
        prompt_lang=normalize_language_choice(prompt_lang),
        base_seed=int(base_seed),
        count=int(candidate_count),
        api_url=api_url or DEFAULT_API_URL,
    )
    audio_values = [item["ogg"] for item in results]
    while len(audio_values) < 5:
        audio_values.append(None)
    summary = api_status + "\n" + "\n".join(
        f"seed {item['seed']}: {item['ogg']}" for item in results
    )
    return (*audio_values[:5], summary)


def approve_take(selected_take: str, character: str, line_id: str) -> str:
    if not selected_take:
        raise gr.Error("승인할 후보 파일 경로를 입력하세요.")
    source = Path(selected_take).expanduser()
    if not source.exists():
        raise gr.Error(f"후보 파일이 없습니다: {source}")
    dest = ROOT / "approved" / sanitize_id(character or "default") / f"{sanitize_id(line_id or source.stem)}.ogg"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)
    return f"승인본 저장 완료: {dest}"


def build_app() -> gr.Blocks:
    with gr.Blocks(title="Voice Lab") as demo:
        gr.Markdown(
            "# Voice Lab\n"
            "범용 GPT-SoVITS 음성 생성 UI입니다. 음성파일을 넣고, 감정 라벨과 대사를 지정해 후보 음성을 만듭니다.\n\n"
            "주의: 감정 선택은 파일 정리와 메타데이터에 쓰입니다. 실제 감정 표현은 참조 음성의 톤이 가장 크게 좌우합니다."
        )
        with gr.Row():
            character = gr.Textbox(label="Voice name", value="default", scale=1)
            line_id = gr.Textbox(label="Line ID", value="line_001", scale=1)
        emotion = gr.Radio(
            label="Emotion",
            choices=EMOTION_BUTTONS,
            value="기본",
            info="드롭다운 대신 빠른 버튼으로 선택합니다. 실제 감정은 참조 음성 톤이 가장 중요합니다.",
        )

        with gr.Tab("1. Reference Clip"):
            uploaded_audio = gr.Audio(label="Upload source audio", type="filepath")
            existing_path = gr.Textbox(label="Or existing audio path", placeholder="/mnt/c/Users/Desktop/Downloads/audio.mp3")
            with gr.Row():
                start_seconds = gr.Number(label="Start seconds", value=0.0)
                duration_seconds = gr.Number(label="Duration seconds (3-10)", value=9.5)
            make_ref_btn = gr.Button("Make 3-10s Reference Clip")
            ref_audio_path = gr.Textbox(label="Reference WAV path")
            ref_player = gr.Audio(label="Reference preview", type="filepath")
            ref_status = gr.Textbox(label="Reference status", lines=4)
            make_ref_btn.click(
                make_reference,
                inputs=[uploaded_audio, existing_path, character, emotion, start_seconds, duration_seconds],
                outputs=[ref_audio_path, ref_player, ref_status],
            )

        with gr.Tab("2. Generate"):
            text = gr.Textbox(label="Text to speak", lines=3, placeholder="대사를 입력하세요.")
            prompt_text = gr.Textbox(
                label="Reference transcript (recommended)",
                lines=2,
                placeholder="참조 음성의 실제 대사. 모르면 비워둘 수 있지만 품질이 떨어질 수 있습니다.",
            )
            with gr.Accordion("Advanced language settings", open=False):
                with gr.Row():
                    text_lang = gr.Radio(label="Text language", choices=LANGUAGE_PRESETS, value="auto")
                    prompt_lang = gr.Radio(label="Reference transcript language", choices=LANGUAGE_PRESETS, value="auto")
            with gr.Row():
                base_seed = gr.Number(label="Base seed", value=1000, precision=0)
                candidate_count = gr.Slider(label="Candidate count", minimum=1, maximum=5, step=1, value=3)
            with gr.Row():
                api_url = gr.Textbox(label="GPT-SoVITS API URL", value=DEFAULT_API_URL)
                autostart_api = gr.Checkbox(label="Auto-start local GPT-SoVITS API", value=True)
            generate_btn = gr.Button("Generate Candidates", variant="primary")

            gr.Markdown("## Candidates")
            out1 = gr.Audio(label="Candidate 1", type="filepath")
            out2 = gr.Audio(label="Candidate 2", type="filepath")
            out3 = gr.Audio(label="Candidate 3", type="filepath")
            out4 = gr.Audio(label="Candidate 4", type="filepath")
            out5 = gr.Audio(label="Candidate 5", type="filepath")
            generate_status = gr.Textbox(label="Generate status", lines=8)
            generate_btn.click(
                generate_voice,
                inputs=[
                    ref_audio_path,
                    character,
                    emotion,
                    line_id,
                    text,
                    text_lang,
                    prompt_text,
                    prompt_lang,
                    base_seed,
                    candidate_count,
                    api_url,
                    autostart_api,
                ],
                outputs=[out1, out2, out3, out4, out5, generate_status],
            )

        with gr.Tab("3. Approve"):
            selected_take = gr.Textbox(label="Candidate OGG path to approve")
            approve_btn = gr.Button("Copy to approved/")
            approve_status = gr.Textbox(label="Approve status")
            approve_btn.click(approve_take, inputs=[selected_take, character, line_id], outputs=[approve_status])

    return demo


if __name__ == "__main__":
    port = int(os.environ.get("VOICE_LAB_PORT", "7860"))
    build_app().launch(server_name="127.0.0.1", server_port=port)
