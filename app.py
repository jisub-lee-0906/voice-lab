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
from voice_lab.ui_config import (
    DEFAULT_HELP_TEXT,
    EMOTION_BUTTONS,
    LANGUAGE_PRESETS,
    QUICK_START_STEPS,
    format_candidate_summary,
    normalize_language_choice,
)
from voice_lab.workflow import generate_candidates


ROOT = Path(__file__).resolve().parent
DEFAULT_REPO = ROOT / "references" / "GPT-SoVITS"
DEFAULT_PYTHON = ROOT / ".venv-gpt-sovits" / "bin" / "python"
API_PROCESS = None


CUSTOM_CSS = """
.gradio-container { max-width: 1180px !important; margin: auto !important; }
.voice-lab-hero {
  border-radius: 18px;
  padding: 22px 24px;
  background: linear-gradient(135deg, #20243a 0%, #111827 58%, #0f172a 100%);
  color: #f8fafc;
  margin-bottom: 14px;
}
.voice-lab-hero h1 { margin: 0 0 8px 0; font-size: 30px; }
.voice-lab-hero p { margin: 4px 0; color: #dbeafe; }
.voice-lab-help {
  border-radius: 14px;
  padding: 12px 14px;
  background: #fff7ed;
  border: 1px solid #fed7aa;
  color: #7c2d12;
}
.voice-lab-step {
  border-radius: 14px;
  padding: 12px 14px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}
"""


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
        return "GPT-SoVITS API 준비 완료"
    except Exception:
        if not autostart:
            raise gr.Error("GPT-SoVITS API가 실행 중이 아닙니다. 자동 실행을 켜거나 API를 먼저 실행하세요.")
    if not DEFAULT_REPO.exists():
        raise gr.Error(f"GPT-SoVITS repo를 찾을 수 없습니다: {DEFAULT_REPO}")
    if not DEFAULT_PYTHON.exists():
        raise gr.Error(f"GPT-SoVITS Python을 찾을 수 없습니다: {DEFAULT_PYTHON}")
    API_PROCESS = start_api(DEFAULT_REPO, DEFAULT_PYTHON)
    wait_for_api(api_url, timeout_seconds=120)
    return "GPT-SoVITS API 자동 실행 완료"


def make_reference(
    uploaded_audio: str | None,
    existing_path: str,
    voice_name: str,
    emotion: str,
    start_seconds: float,
    duration_seconds: float,
):
    source = _source_path(uploaded_audio, existing_path)
    validate_reference_duration(duration_seconds)
    if not source.exists():
        raise gr.Error(f"음성 파일이 없습니다: {source}")
    ref_path = build_clip_path(ROOT, voice_name, emotion, source)
    cut_reference(source, ref_path, start_seconds, duration_seconds)
    duration = probe_duration(ref_path)
    status = (
        "참조 클립 생성 완료\n"
        f"저장 위치: {ref_path}\n"
        f"길이: {duration:.2f}초\n"
        f"감정 라벨: {normalize_emotion(emotion)}"
    )
    return str(ref_path), str(ref_path), status


def generate_voice(
    ref_audio_path: str,
    voice_name: str,
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
        raise gr.Error("먼저 '참조 클립 만들기'를 누르거나 참조 WAV 경로를 입력하세요.")
    ref_audio = Path(ref_audio_path.strip()).expanduser()
    if not ref_audio.exists():
        raise gr.Error(f"참조 WAV가 없습니다: {ref_audio}")
    if not text.strip():
        raise gr.Error("읽힐 대사를 입력하세요.")
    if not prompt_text.strip():
        prompt_text = text
    if not line_id.strip():
        line_id = f"line_{int(time.time())}"

    api_status = ensure_api(api_url or DEFAULT_API_URL, autostart_api)
    results = generate_candidates(
        root=ROOT,
        character=voice_name or "default",
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
    path_values = [item["ogg"] for item in results]
    while len(audio_values) < 5:
        audio_values.append(None)
        path_values.append("")
    summary = format_candidate_summary(api_status, results)
    return (*audio_values[:5], *path_values[:5], summary)


def approve_take(selected_take: str, voice_name: str, line_id: str) -> str:
    if not selected_take:
        raise gr.Error("승인할 후보가 없습니다. 먼저 후보를 생성하세요.")
    source = Path(selected_take).expanduser()
    if not source.exists():
        raise gr.Error(f"후보 파일이 없습니다: {source}")
    dest = ROOT / "approved" / sanitize_id(voice_name or "default") / f"{sanitize_id(line_id or source.stem)}.ogg"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)
    return f"승인 완료: {dest}"


def build_app() -> gr.Blocks:
    with gr.Blocks(title="Voice Lab") as demo:
        gr.HTML(
            f"<style>{CUSTOM_CSS}</style>"
            "<div class='voice-lab-hero'>"
            "<h1>Voice Lab</h1>"
            "<p>음성 파일, 감정, 대사만 넣으면 GPT-SoVITS로 후보 음성을 만드는 로컬 도구입니다.</p>"
            "<p>처음 쓰는 사람도 위에서 아래로만 진행하면 됩니다.</p>"
            "</div>"
        )
        with gr.Row():
            for step in QUICK_START_STEPS:
                gr.HTML(f"<div class='voice-lab-step'>{step}</div>")
        gr.HTML(f"<div class='voice-lab-help'>{DEFAULT_HELP_TEXT}</div>")

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("## 1. 기본 정보")
                voice_name = gr.Textbox(label="목소리 이름", value="default", placeholder="예: default, narrator, character_a")
                line_id = gr.Textbox(label="대사 ID", value="line_001", placeholder="예: line_001")
                emotion = gr.Radio(label="감정", choices=EMOTION_BUTTONS, value="기본")

                gr.Markdown("## 2. 음성 파일")
                uploaded_audio = gr.Audio(label="음성 파일 업로드", type="filepath")
                existing_path = gr.Textbox(
                    label="또는 기존 파일 경로",
                    placeholder="예: /mnt/c/Users/Desktop/Downloads/audio.mp3",
                )
                with gr.Row():
                    start_seconds = gr.Number(label="시작 초", value=0.0)
                    duration_seconds = gr.Number(label="길이 초 (3~10)", value=9.5)
                make_ref_btn = gr.Button("참조 클립 만들기", variant="secondary")
                ref_audio_path = gr.Textbox(label="참조 WAV 경로", interactive=True)
                ref_player = gr.Audio(label="참조 클립 미리듣기", type="filepath")
                ref_status = gr.Textbox(label="참조 클립 상태", lines=4, interactive=False)

            with gr.Column(scale=1):
                gr.Markdown("## 3. 대사 입력")
                text = gr.Textbox(
                    label="읽힐 대사",
                    lines=5,
                    placeholder="이 목소리로 읽힐 대사를 입력하세요.",
                )
                prompt_text = gr.Textbox(
                    label="참조 음성의 실제 대사 (선택이지만 권장)",
                    lines=3,
                    placeholder="참조 클립에서 실제로 말한 문장을 적으면 품질이 좋아집니다. 모르면 비워도 됩니다.",
                )
                with gr.Accordion("고급 설정", open=False):
                    with gr.Row():
                        text_lang = gr.Radio(label="읽힐 대사 언어", choices=LANGUAGE_PRESETS, value="auto")
                        prompt_lang = gr.Radio(label="참조 대사 언어", choices=LANGUAGE_PRESETS, value="auto")
                    with gr.Row():
                        base_seed = gr.Number(label="기본 seed", value=1000, precision=0)
                        candidate_count = gr.Slider(label="후보 개수", minimum=1, maximum=5, step=1, value=3)
                    api_url = gr.Textbox(label="GPT-SoVITS API 주소", value=DEFAULT_API_URL)
                    autostart_api = gr.Checkbox(label="GPT-SoVITS API 자동 실행", value=True)

                generate_btn = gr.Button("후보 음성 생성", variant="primary", size="lg")
                generate_status = gr.Textbox(label="생성 상태", lines=8, interactive=False)

        gr.Markdown("## 4. 후보 듣고 승인하기")
        with gr.Row():
            candidate_outputs = []
            candidate_paths = []
            approve_buttons = []
            for idx in range(1, 6):
                with gr.Column(scale=1):
                    audio = gr.Audio(label=f"후보 {idx}", type="filepath")
                    path_box = gr.Textbox(label=f"후보 {idx} 경로", visible=False)
                    button = gr.Button(f"후보 {idx} 승인")
                    candidate_outputs.append(audio)
                    candidate_paths.append(path_box)
                    approve_buttons.append(button)
        approve_status = gr.Textbox(label="승인 상태", interactive=False)

        make_ref_btn.click(
            make_reference,
            inputs=[uploaded_audio, existing_path, voice_name, emotion, start_seconds, duration_seconds],
            outputs=[ref_audio_path, ref_player, ref_status],
        )
        generate_btn.click(
            generate_voice,
            inputs=[
                ref_audio_path,
                voice_name,
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
            outputs=[*candidate_outputs, *candidate_paths, generate_status],
        )
        for button, path_box in zip(approve_buttons, candidate_paths):
            button.click(approve_take, inputs=[path_box, voice_name, line_id], outputs=[approve_status])

    return demo


if __name__ == "__main__":
    port = int(os.environ.get("VOICE_LAB_PORT", "7860"))
    build_app().launch(server_name="127.0.0.1", server_port=port)
