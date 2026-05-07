# Voice Lab

GPT-SoVITS 기반 로컬 음성 생성 도구입니다.

목표는 단순합니다.

1. 음성 파일을 넣습니다.
2. 감정을 고릅니다.
3. 읽힐 대사를 입력합니다.
4. 후보 음성을 생성합니다.
5. 들어보고 가장 좋은 후보를 승인합니다.

## 실행

```bash
cd /home/jisub-lee/workspace/voice-lab
uv run --extra dev python app.py
```

브라우저에서 아래 주소를 엽니다.

```text
http://127.0.0.1:7860
```

## 사용 순서

### 1. 기본 정보

- `목소리 이름`: 목소리/캐릭터/화자 이름입니다. 처음에는 `default`로 둬도 됩니다.
- `대사 ID`: 저장 파일 이름에 쓰입니다. 처음에는 `line_001`로 둬도 됩니다.
- `감정`: 기본, 츤츤, 다정, 부끄러움, 진지, 화남, 기쁨, 슬픔 중 고릅니다.

주의: 감정 버튼이 실제 감정을 마법처럼 바꾸지는 않습니다. 결과 감정은 참조 음성의 톤이 가장 크게 좌우합니다.

### 2. 음성 파일

- 음성 파일을 업로드하거나 기존 파일 경로를 입력합니다.
- 긴 음성 파일이면 `시작 초`와 `길이 초`를 입력해 3~10초 구간만 자릅니다.
- GPT-SoVITS는 참조 음성이 3~10초여야 합니다.

### 3. 대사 입력

- `읽힐 대사`: 새로 생성할 음성이 말할 문장입니다.
- `참조 음성의 실제 대사`: 참조 클립에서 실제로 말한 문장입니다. 선택 항목이지만 입력하면 품질이 좋아집니다.
- 언어, seed, 후보 개수, API 주소는 `고급 설정`에 숨겨져 있습니다.

### 4. 후보 듣고 승인하기

- `후보 음성 생성`을 누르면 1~5개 후보가 생성됩니다.
- 후보를 들어보고 마음에 드는 후보의 `승인` 버튼을 누릅니다.
- 승인된 파일은 `approved/` 아래에 저장됩니다.

## 프로젝트 구조

```text
voice-lab/
  app.py                    # 한글 Gradio UI
  src/voice_lab/            # 핵심 로직
  tests/                    # 테스트
  refs/                     # 참조 음성 위치
  generated/                # 생성 후보 위치
  approved/                 # 승인본 위치
  exports/                  # 외부 프로젝트 export 위치
  references/GPT-SoVITS/    # 로컬 GPT-SoVITS repo, git 제외
  .venv-gpt-sovits/         # GPT-SoVITS 실행 venv, git 제외
```

## GitHub 업로드 주의

이 프로젝트를 GitHub에 올릴 때는 private repository로 올리는 것을 기본으로 합니다.

다음 항목은 용량과 권리 문제 때문에 git에 올리지 않습니다.

- `references/GPT-SoVITS/`
- `.venv-gpt-sovits/`
- `.venv/`
- `generated/`
- `approved/`
- `exports/`
- 실제 참조 음성 파일

## 검증

```bash
cd /home/jisub-lee/workspace/voice-lab
uv run --extra dev pytest -q
```
