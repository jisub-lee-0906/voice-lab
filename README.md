# Voice Lab

GPT-SoVITS 기반 로컬 음성 제작 도구입니다.

현재 UI는 Gradio가 아니라 Next.js + shadcn/ui 스타일 컴포넌트 + TailwindCSS + Motion으로 구성되어 있습니다. 음성 처리는 FastAPI backend가 기존 Python GPT-SoVITS/ffmpeg workflow를 호출합니다.

## 실행

터미널 1: backend

```bash
cd /home/jisub-lee/workspace/voice-lab
uv run python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

터미널 2: frontend

```bash
cd /home/jisub-lee/workspace/voice-lab/frontend
npm run dev
```

브라우저:

```text
http://127.0.0.1:3000
```

API 상태 확인:

```text
http://127.0.0.1:8000/api/health
```

## 사용 순서

1. 목소리 이름과 대사 ID를 입력합니다. 처음에는 기본값 그대로 써도 됩니다.
2. 원하는 느낌을 고릅니다.
3. 음성 파일을 업로드하거나 기존 파일 경로를 입력합니다.
4. 긴 음성에서 사용할 3~10초 구간을 잘라 참조 음성을 만듭니다.
5. 읽힐 대사를 입력합니다.
6. `새 음성 만들기`를 누릅니다.
7. 결과를 들어보고 마음에 드는 음성만 저장합니다.

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
