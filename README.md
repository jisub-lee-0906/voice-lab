# Voice Lab

GPT-SoVITS 기반 개인용 로컬 음성 제작 도구입니다.

Voice Lab은 서버형 SaaS나 다중 사용자 서비스를 목표로 하지 않습니다. 개인 PC에서 음성 파일을 넣고, 3~10초 참조 클립을 만든 뒤, 원하는 대사를 GPT-SoVITS로 생성해 후보를 듣고 저장하는 범용 voice asset generator입니다. 나중에 게임/VN/영상 프로젝트에 결과물을 가져다 쓰는 것을 전제로 하지만, 특정 엔진 전용 export 로직은 core에 넣지 않습니다.

현재 UI는 Gradio가 아니라 Next.js + shadcn/ui 스타일 컴포넌트 + TailwindCSS + Motion으로 구성되어 있습니다. 음성 처리는 FastAPI backend가 Python GPT-SoVITS/ffmpeg workflow를 호출합니다.

## 현재 수준

개인용 로컬 제작 도구 기준으로는 바로 사용할 수 있는 상태입니다.

지원되는 흐름:

- 음성 파일 업로드 또는 기존 파일 경로 입력
- 3~10초 참조 음성 자르기
- 시작 초/길이 초/실제 참조 길이 검증
- 한국어 대사 기본 생성(`text_lang=ko`)
- `prompt_text` 오용 방지 및 warning 표시
- 후보 wav/ogg 생성
- ASR/Praat 기반 `pick-best` 품질 검증
- strict mechanical gate로 기계음/저음 뭉개짐/불안정 take 탈락
- 마음에 드는 후보 저장
- Hermes/스크립트 자동화를 위한 JSON CLI
- `/api/runtime`와 `voice-lab doctor` 상태 점검

아직 목표가 아닌 것:

- 공개 서비스/SaaS 운영
- 여러 사용자가 동시에 쓰는 queue 서버
- 상업 배포용 권리 검증 자동화
- 특정 게임 엔진 전용 export

## 최소/권장 사양

최소 사양:

```text
OS: Windows 10/11 + WSL2 Ubuntu 또는 Linux
GPU: NVIDIA GPU 8GB VRAM 이상
RAM: 16GB 이상
Disk: 30GB 이상 여유 공간
Python: 3.10~3.12 계열
Node.js: 20 이상
ffmpeg/ffprobe: 설치 필요
CUDA/PyTorch: GPT-SoVITS와 호환되는 조합
```

권장 사양:

```text
OS: Windows 11 + WSL2 Ubuntu
GPU: NVIDIA GPU 12GB VRAM 이상
RAM: 32GB 이상
Disk: 80GB 이상 여유 공간
CPU: 6코어 이상
```

주의:

- CPU-only 실행은 현실적으로 느립니다.
- GPT-SoVITS 모델/의존성/체크포인트는 repo에 포함하지 않습니다.
- 참조 음성은 깨끗한 3~10초 구간을 쓰는 것이 가장 안정적입니다.
- 긴 대사는 250자 이하의 짧은 문장 단위로 나눠 생성하세요.
- 생성 결과는 반드시 직접 들어보고 저장하세요.

## 포트

```text
Voice Lab UI:      http://127.0.0.1:3100
Voice Lab backend: http://127.0.0.1:8100
GPT-SoVITS API:    http://127.0.0.1:9100
ComfyUI reserved:  http://127.0.0.1:8000
```

브라우저는 backend를 직접 호출하지 않고 Next.js proxy를 사용합니다.

```text
Browser -> http://127.0.0.1:3100/api/...
Next.js -> http://127.0.0.1:8100/api/...
```

## 실행

터미널 1: backend

```bash
cd /home/jisub-lee/workspace/voice-lab
uv run python -m uvicorn backend.main:app --host 127.0.0.1 --port 8100
```

터미널 2: frontend

```bash
cd /home/jisub-lee/workspace/voice-lab/frontend
npm run dev
```

브라우저:

```text
http://127.0.0.1:3100
```

API 상태 확인:

```text
http://127.0.0.1:8100/api/health
```

운영 상태 점검:

```bash
cd /home/jisub-lee/workspace/voice-lab
uv run voice-lab doctor
```

GPT-SoVITS가 별도로 꺼져 있으면 backend의 `autostart_api` 흐름이 기본 경로의 GPT-SoVITS를 자동 실행하려고 시도합니다. 그래도 생성이 실패하면 `doctor` 결과와 UI의 `detail` 메시지를 먼저 확인하세요.

## 사용 순서

1. 목소리 이름과 대사 ID를 입력합니다. 처음에는 기본값 그대로 써도 됩니다.
2. 원하는 느낌을 고릅니다.
3. 음성 파일을 업로드하거나 기존 파일 경로를 입력합니다.
4. 긴 음성에서 사용할 3~10초 구간을 잘라 참조 음성을 만듭니다.
5. 읽힐 대사를 입력합니다.
6. `참조 음성의 실제 대사`는 참조 클립에서 실제로 말한 문장을 정확히 알 때만 입력합니다. 모르면 비워두세요.
7. `새 음성 만들기`를 누릅니다.
8. 결과를 들어보고 마음에 드는 음성만 저장합니다.

권장 입력:

- 참조 음성: 배경음/효과음/겹치는 말이 적은 3~10초.
- 읽힐 대사: 한 번에 250자 이하, 가능하면 한두 문장.
- `prompt_text`: 참조 음성의 실제 transcript만. 읽힐 대사를 복붙하지 마세요.
- 언어: 기본 생성 언어는 한국어입니다. 다른 언어는 CLI의 `--text-lang` 또는 추후 UI 옵션으로 조정합니다.

## 에이전트/자동화 CLI

브라우저 UI와 별개로 Hermes나 스크립트가 쓰기 좋은 JSON CLI를 제공합니다. 모든 명령은 stdout에 JSON만 출력하므로 Ren'Py/VN 에셋 자동화에서 파싱하기 쉽습니다.

상태 확인:

```bash
cd /home/jisub-lee/workspace/voice-lab
uv run voice-lab status
uv run voice-lab doctor
```

`doctor`는 backend, GPT-SoVITS, 필수 경로, 디스크 여유 공간을 JSON으로 점검합니다.

참조 음성 만들기:

```bash
uv run voice-lab reference \
  --existing-path /mnt/c/Users/Desktop/Downloads/audio.mp3 \
  --start 87 \
  --duration 9.5 \
  --voice tsundere \
  --emotion 츤츤
```

새 음성 후보 만들기:

```bash
uv run voice-lab generate \
  --ref /home/jisub-lee/workspace/voice-lab/refs/tsundere/tsun/audio_ref.wav \
  --text "안녕하세요. 오늘부터 잘 부탁드립니다." \
  --line-id ch01_001 \
  --voice tsundere \
  --candidates 3
```

마음에 드는 후보 저장:

```bash
uv run voice-lab save \
  --source /home/jisub-lee/workspace/voice-lab/generated/tsundere/ch01_001/seed_1000.ogg \
  --voice tsundere \
  --line-id ch01_001
```

Ren'Py/VN 대사 배치 생성용 manifest 예시:

```json
{
  "lines": [
    {
      "line_id": "ch01_001",
      "text": "안녕하세요. 오늘부터 잘 부탁드립니다.",
      "ref_audio_path": "/home/jisub-lee/workspace/voice-lab/refs/tsundere/tsun/audio_ref.wav",
      "voice_name": "tsundere",
      "emotion": "츤츤"
    }
  ]
}
```

배치 생성:

```bash
uv run voice-lab batch-generate \
  --input docs/voice_lines.json \
  --manifest exports/voice_manifest.json \
  --candidates 3
```

주의:

- `--text`는 새로 읽힐 대사입니다. 기본 언어는 한국어(`ko`)입니다.
- 기본 제공 참조가 있다면 `refs/tsundere/tsun/audio_ref.wav`처럼 실제 말투에 맞는 profile/emotion으로 분류하세요. 새 음성도 `refs/<voice_profile>/<emotion>/audio_ref.wav` 구조를 사용하고, 생성/저장 시 `voice_name`을 같은 profile 이름으로 맞춥니다.
- `--prompt-text`는 참조 음성 안에서 실제로 말한 대사입니다. 모르면 비워두는 편이 낫습니다.
- 한글 대사에 영어/로마자가 섞인 경우 GPT-SoVITS가 NLTK 영어 태거를 요구할 수 있습니다. `averaged_perceptron_tagger_eng` 오류가 나면 다음을 한 번 실행하세요.

```bash
/home/jisub-lee/workspace/voice-lab/.venv-gpt-sovits/bin/python - <<'PY'
import nltk
nltk.download('averaged_perceptron_tagger_eng')
nltk.download('averaged_perceptron_tagger')
PY
```

- CLI는 범용 음성 에셋 생성 도구로 유지합니다. Ren'Py export는 `line_id`, manifest, `approved/` 결과를 이용해 나중에 별도 sync 단계에서 처리합니다.

## 품질 검증 CLI

생성 후보를 바로 채택하지 말고 `pick-best`로 먼저 검증하세요. `balanced`는 탐색용, `strict`는 사용자에게 들려줄 후보를 고를 때 쓰는 보수적인 모드입니다.

```bash
uv run voice-lab pick-best \
  --input-dir generated/default/ch01_001 \
  --anchor /path/to/clean_anchor.ogg \
  --target-text "안녕하세요. 오늘부터 잘 부탁드립니다." \
  --output-dir exports/ch01_001_best \
  --asr-model small \
  --asr-language ko \
  --asr-device cpu \
  --asr-compute-type int8 \
  --feedback-labels /path/to/voice_gate_feedback.yaml \
  --quality-mode strict
```

`best_selection.json`의 `quality_pass`가 `false`면 최종 후보로 쓰지 않습니다. production 자동화에서는 `quality_mode == "strict"`와 `quality_pass == true`를 함께 확인하세요. 그 외에는 후보를 더 생성하거나, 문장을 짧게 바꾸거나, 참조 음성을 바꿔 다시 시도하세요.

자세한 기준은 `docs/quality-gate.md`를 참고하세요.

## 운영 안정성 기준

현재 1차 production hardening은 로컬 제작 도구 기준입니다.

- 생성 전 대사 validation: 빈 대사, 제어 문자, 250자 초과, 미지원 언어 코드 차단.
- 참조 WAV 존재 여부를 engine 호출 전에 차단.
- `prompt_text`가 읽힐 대사와 같으면 warning을 반환/표시.
- `/api/runtime`와 `voice-lab doctor`로 backend/GPT-SoVITS/필수 경로/디스크 여유 공간 점검.
- CLI와 API 오류는 JSON `detail`로 반환해 에이전트가 파싱 가능하게 유지.

## 트러블슈팅

먼저 상태를 확인합니다.

```bash
uv run voice-lab doctor
```

자주 보는 증상:

```text
Failed to fetch
```

- 브라우저는 `http://127.0.0.1:3100`으로 접속해야 합니다.
- backend `8100`만 직접 열어놓고 UI를 쓰면 안 됩니다.
- `frontend/next.config.ts`의 `/api/*` rewrite가 backend `8100`을 바라봅니다.

```text
500 Internal Server Error 또는 /tts 실패
```

- GPT-SoVITS `9100`이 켜져 있어도 `/tts`만 꼬였을 수 있습니다.
- `doctor`에서 GPT-SoVITS 상태를 확인하고, 필요하면 9100 프로세스를 재시작하세요.
- UI에 표시되는 `detail` 메시지가 원인입니다.

```text
Reference audio is outside the 3-10 second range
```

- 참조 구간 길이를 3~10초로 맞추세요.
- 시작 초 + 길이 초가 원본 파일 길이를 넘지 않아야 합니다.

```text
생성 품질이 이상함
```

- 참조 음성이 너무 시끄럽거나 말이 겹치지 않는지 확인하세요.
- `참조 음성의 실제 대사` 칸에 읽힐 대사를 복붙하지 마세요.
- 한국어 대사를 만들 때는 가능하면 한국어 발음이 들어간 참조를 쓰는 편이 낫습니다.
- 긴 문장은 짧게 나눠 생성하세요.

```text
averaged_perceptron_tagger_eng not found
```

- 한글 대사에 영어/로마자가 섞이면 GPT-SoVITS가 NLTK 영어 태거를 요구할 수 있습니다.
- `에이전트/자동화 CLI` 섹션의 NLTK 설치 명령을 한 번 실행하세요.

## 프로젝트 구조

```text
voice-lab/
  backend/                  # FastAPI API 서버
  frontend/                 # Next.js + TailwindCSS UI
  src/voice_lab/            # 음성 처리 핵심 로직
  tests/                    # Python/backend/문구 테스트
  docs/quality-gate.md      # pick-best/strict 품질 검증 기준
  docs/voice-profiles.md    # 참조 음성 profile/emotion 분류 규칙
  refs/                     # 참조 음성 위치, 실제 음성 파일은 git 제외
  generated/                # 생성 후보 위치, 내용물 git 제외
  approved/                 # 저장한 최종 음성 위치, 내용물 git 제외
  exports/                  # 외부 프로젝트 export 위치, 내용물 git 제외
  references/GPT-SoVITS/    # 로컬 GPT-SoVITS repo, git 제외
  .venv-gpt-sovits/         # GPT-SoVITS 실행 venv, git 제외
```

## 검증

Python/backend:

```bash
cd /home/jisub-lee/workspace/voice-lab
uv run --extra dev pytest -q
```

Frontend:

```bash
cd /home/jisub-lee/workspace/voice-lab/frontend
npm run lint
npm run build
```

## GitHub 업로드 주의

GitHub에 올릴 때는 private repository가 기본입니다.

다음 항목은 용량과 권리 문제 때문에 git에 올리지 않습니다.

- `references/GPT-SoVITS/`
- `.venv-gpt-sovits/`
- `.venv/`
- `frontend/node_modules/`
- `frontend/.next/`
- `generated/`
- `approved/`
- `exports/`
- 실제 참조 음성 파일
