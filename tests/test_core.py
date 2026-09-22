from pathlib import Path

from voice_lab.core import (
    build_take_paths,
    normalize_emotion,
    sanitize_id,
    validate_reference_duration,
)


def test_normalize_emotion_maps_korean_labels_to_stable_keys():
    assert normalize_emotion("츤츤") == "tsun"
    assert normalize_emotion("다정") == "soft"
    assert normalize_emotion("neutral") == "neutral"


def test_sanitize_id_keeps_safe_characters_and_lowercases():
    assert sanitize_id("Seria CH01 S01 001!") == "seria_ch01_s01_001"


def test_validate_reference_duration_accepts_gptsovits_safe_range():
    validate_reference_duration(3.0)
    validate_reference_duration(9.99)


def test_validate_reference_duration_rejects_outside_gptsovits_range():
    for duration in (2.99, 10.01):
        try:
            validate_reference_duration(duration)
        except ValueError as exc:
            assert "3-10" in str(exc)
        else:
            raise AssertionError("expected ValueError")


def test_build_take_paths_places_outputs_under_generated_character_line_id():
    root = Path("/tmp/voice-lab")
    paths = build_take_paths(root, "Seria", "CH01 S01 001", 1234)
    assert paths.wav == root / "generated" / "seria" / "ch01_s01_001" / "seed_1234.wav"
    assert paths.ogg == root / "generated" / "seria" / "ch01_s01_001" / "seed_1234.ogg"


def test_validate_reference_duration_rejects_non_finite_values():
    for duration in (float("nan"), float("inf"), float("-inf")):
        try:
            validate_reference_duration(duration)
        except ValueError as exc:
            assert "finite" in str(exc)
        else:
            raise AssertionError("expected ValueError")
