# Voice DB

한국어 전용 참조 음성 샘플을 정리하는 로컬 폴더입니다.

이 폴더는 “보이스 프로필 DB”입니다. 감정 연기톤은 GPT-SoVITS 생성 단계에서 조절하고, 여기서는 기본 목소리 분류만 관리합니다.

## 폴더 구성

```text
voice_db/
  README.md
  voice_db_naming_sample.csv   # 성별,연령,유형,파일명 규칙 샘플/기본 매니페스트
  original/                    # 사용자가 넣는 원본 mp3/wav/flac 등. git에 올리지 않음
  staging/                     # 잘라내기/정리 전 임시 작업물. git에 올리지 않음

refs/
  voice_db/
    <voice_id>/
      base/
        audio_ref.wav          # GPT-SoVITS 참조용 3~10초 WAV. git에 올리지 않음
```

예시:

```text
voice_db/original/female_teen_tsundere.mp3
refs/voice_db/female_teen_tsundere/base/audio_ref.wav
```

## CSV 형식

현재 기본 형식은 단순하게 유지합니다.

```csv
성별,연령,유형,파일명
female,teen,tsundere,female_teen_tsundere.mp3
```

규칙:

- 파일명은 `<성별>_<연령>_<유형>.mp3` 형식을 유지합니다.
- CSV는 UTF-8로 저장합니다.
- 한국어만 사용할 전제이므로 language 컬럼은 지금은 만들지 않습니다.
- 참조 음성의 실제 대사(`prompt_text`)를 모르면 비워두는 쪽이 안전하므로, 지금 단계에서는 CSV에 넣지 않습니다.
- 나중에 특정 샘플의 실제 발화 문장을 알게 되면 별도 메타 파일을 추가할 수 있습니다.

## 권장 사용 방식

1. 사용자가 원본 샘플을 `voice_db/original/`에 넣습니다.
2. 파일명은 CSV의 `파일명`과 맞춥니다.
3. 캐릭터마다 사용할 기본 보이스 프로필을 하나 고릅니다.
4. voice-lab에서 그 프로필의 3~10초 구간을 잘라 `refs/voice_db/<voice_id>/base/audio_ref.wav`로 만듭니다.
5. 생성할 때 `voice_name`은 `<voice_id>`를 사용하고, 감정/연기톤은 GPT-SoVITS 생성 단계에서 조절합니다.

## 캐릭터 매핑 방식

이 DB는 “한 캐릭터에 여러 후보를 계속 붙이는” 구조가 아니라, 캐릭터의 기본 목소리를 하나의 `voice_id`로 고정하기 위한 목록입니다.

예시:

```text
아리아 -> female_teen_tsundere
학원장 -> male_elder_mage
학생 A -> female_teen_pure
빌런 -> male_adult_villain
```

아리아용으로는 우선 아래 파일 하나만 넣으면 됩니다.

```text
voice_db/original/female_teen_tsundere.mp3
refs/voice_db/female_teen_tsundere/base/audio_ref.wav
```

이후 아리아의 차가운 말투, 당황, 부드러움 같은 변화는 `female_teen_tsundere` 참조를 유지한 채 GPT-SoVITS의 생성 대사/파라미터/seed/후보 선택으로 조절합니다.

## git 정책

- CSV와 README만 repo에 기록합니다.
- 실제 음성 원본과 참조 WAV는 로컬/private asset이므로 git에 올리지 않습니다.
- `.gitkeep`은 빈 폴더 유지를 위해서만 둡니다.
