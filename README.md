# Voice Lab

GPT-SoVITS 기반 로컬 음성 제작 도구입니다.

현재 UI는 Gradio가 아니라 Next.js + shadcn/ui 스타일 컴포넌트 + TailwindCSS + Motion으로 구성되어 있습니다. 음성 처리는 FastAPI backend가 기존 Python GPT-SoVITS/ffmpeg workflow를 호출합니다.

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

## 사용 순서

1. 목소리 이름과 대사 ID를 입력합니다. 처음에는 기본값 그대로 써도 됩니다.
2. 원하는 느낌을 고릅니다.
3. 음성 파일을 업로드하거나 기존 파일 경로를 입력합니다.
4. 긴 음성에서 사용할 3~10초 구간을 잘라 참조 음성을 만듭니다.
5. 읽힐 대사를 입력합니다.
6. `새 음성 만들기`를 누릅니다.
7. 결과를 들어보고 마음에 드는 음성만 저장합니다.

## 에이전트/자동화 CLI

브라우저 UI와 별개로 Hermes나 스크립트가 쓰기 좋은 JSON CLI를 제공합니다. 모든 명령은 stdout에 JSON만 출력하므로 Ren'Py/VN 에셋 자동화에서 파싱하기 쉽습니다.

상태 확인:

```bash
cd /home/jisub-lee/workspace/voice-lab
uv run voice-lab status
```

참조 음성 만들기:

```bash
uv run voice-lab reference \
  --existing-path /mnt/c/Users/Desktop/Downloads/audio.mp3 \
  --start 87 \
  --duration 9.5 \
  --voice heroine_a \
  --emotion 기본
```

새 음성 후보 만들기:

```bash
uv run voice-lab generate \
  --ref /home/jisub-lee/workspace/voice-lab/refs/heroine_a/neutral/audio_ref.wav \
  --text "안녕하세요. 오늘부터 잘 부탁드립니다." \
  --line-id ch01_001 \
  --voice heroine_a \
  --candidates 3
```

마음에 드는 후보 저장:

```bash
uv run voice-lab save \
  --source /home/jisub-lee/workspace/voice-lab/generated/heroine_a/ch01_001/seed_1000.ogg \
  --voice heroine_a \
  --line-id ch01_001
```

Ren'Py/VN 대사 배치 생성용 manifest 예시:

```json
{
  "lines": [
    {
      "line_id": "ch01_001",
      "text": "안녕하세요. 오늘부터 잘 부탁드립니다.",
      "ref_audio_path": "/home/jisub-lee/workspace/voice-lab/refs/heroine_a/neutral/audio_ref.wav",
      "voice_name": "heroine_a",
      "emotion": "기본"
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

## 프로젝트 구조

```text
voice-lab/
  backend/                  # FastAPI API 서버
  frontend/                 # Next.js + TailwindCSS UI
  src/voice_lab/            # 기존 음성 처리 핵심 로직
  tests/                    # Python/backend/문구 테스트
  refs/                     # 참조 음성 위치
  generated/                # 생성 후보 위치
  approved/                 # 저장한 최종 음성 위치
  exports/                  # 외부 프로젝트 export 위치
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
