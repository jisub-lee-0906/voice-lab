from __future__ import annotations

EMOTION_BUTTONS = ["기본", "츤츤", "다정", "부끄러움", "진지", "화남", "기쁨", "슬픔"]
LANGUAGE_PRESETS = ["auto", "ko", "ja", "en", "zh", "all_zh", "all_ja", "all_ko", "all_yue"]
QUICK_START_STEPS = [
    "1. 음성 파일을 넣고, 필요한 구간을 3~10초로 잘라요.",
    "2. 감정 버튼을 고르고, 읽힐 대사를 입력해요.",
    "3. 생성 버튼을 누른 뒤 가장 좋은 후보를 승인해요.",
]
DEFAULT_HELP_TEXT = (
    "감정 버튼은 파일 정리와 선택 기준입니다. 실제 감정 표현은 참조 음성의 말투, 에너지, 속도에 가장 크게 좌우됩니다. "
    "원하는 감정과 비슷한 참조 음성을 넣으면 결과가 좋아집니다."
)


def normalize_language_choice(value: str | None) -> str:
    return (value or "auto").strip() or "auto"


def format_candidate_summary(api_status: str, results: list[dict]) -> str:
    if not results:
        return f"{api_status}\n생성된 후보가 없습니다."
    lines = [api_status, "", "생성 완료. 아래 후보를 들어보고 마음에 드는 후보의 승인 버튼을 누르세요."]
    for index, item in enumerate(results, start=1):
        lines.append(f"후보 {index} / seed {item['seed']}: {item['ogg']}")
    return "\n".join(lines)
