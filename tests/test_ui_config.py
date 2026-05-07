from voice_lab.ui_config import (
    DEFAULT_HELP_TEXT,
    EMOTION_BUTTONS,
    LANGUAGE_PRESETS,
    QUICK_START_STEPS,
    format_candidate_summary,
    normalize_language_choice,
)


def test_emotion_buttons_are_korean_quick_buttons_not_dropdown_values():
    assert EMOTION_BUTTONS == ["기본", "츤츤", "다정", "부끄러움", "진지", "화남", "기쁨", "슬픔"]


def test_language_presets_keep_auto_and_common_languages_visible():
    assert LANGUAGE_PRESETS[:4] == ["auto", "ko", "ja", "en"]


def test_normalize_language_choice_accepts_empty_as_auto():
    assert normalize_language_choice("") == "auto"
    assert normalize_language_choice("ko") == "ko"


def test_quick_start_steps_are_beginner_friendly_korean():
    assert QUICK_START_STEPS[0].startswith("1.")
    assert "음성" in QUICK_START_STEPS[0]
    assert "생성" in QUICK_START_STEPS[-1]


def test_default_help_text_warns_emotion_comes_from_reference_voice():
    assert "참조 음성" in DEFAULT_HELP_TEXT
    assert "감정" in DEFAULT_HELP_TEXT


def test_format_candidate_summary_has_clickable_approval_guidance():
    results = [{"seed": 1000, "ogg": "/tmp/a.ogg"}, {"seed": 1001, "ogg": "/tmp/b.ogg"}]
    summary = format_candidate_summary("API 준비 완료", results)
    assert "후보 1" in summary
    assert "승인" in summary
    assert "/tmp/a.ogg" in summary
