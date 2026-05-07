from voice_lab.ui_config import EMOTION_BUTTONS, LANGUAGE_PRESETS, normalize_language_choice


def test_emotion_buttons_are_korean_quick_buttons_not_dropdown_values():
    assert EMOTION_BUTTONS == ["기본", "츤츤", "다정", "부끄러움", "진지", "화남", "기쁨", "슬픔"]


def test_language_presets_keep_auto_and_common_languages_visible():
    assert LANGUAGE_PRESETS[:4] == ["auto", "ko", "ja", "en"]


def test_normalize_language_choice_accepts_empty_as_auto():
    assert normalize_language_choice("") == "auto"
    assert normalize_language_choice("ko") == "ko"
