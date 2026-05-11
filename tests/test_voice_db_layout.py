from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VOICE_DB = ROOT / "voice_db"


def test_voice_db_layout_exists_and_documents_korean_only_manifest():
    assert (VOICE_DB / "README.md").exists()
    assert (VOICE_DB / "voice_db_naming_sample.csv").exists()
    assert (VOICE_DB / "original" / ".gitkeep").exists()
    assert (VOICE_DB / "staging" / ".gitkeep").exists()
    assert (ROOT / "refs" / "voice_db" / ".gitkeep").exists()

    readme = (VOICE_DB / "README.md").read_text(encoding="utf-8")
    assert "한국어 전용" in readme
    assert "성별,연령,유형,파일명" in readme
    assert "refs/voice_db/<voice_id>/base/audio_ref.wav" in readme
    assert "아리아 -> female_teen_tsundere" in readme
    assert "아리아용으로는 우선 아래 파일 하나만" in readme
    assert "female_teen_cool.mp3\nfemale_teen_elegant.mp3" not in readme


def test_voice_db_sample_csv_is_utf8_and_matches_filename_rule():
    raw = (VOICE_DB / "voice_db_naming_sample.csv").read_bytes()
    text = raw.decode("utf-8")
    lines = [line for line in text.splitlines() if line.strip()]

    assert lines[0] == "성별,연령,유형,파일명"
    assert len(lines) > 10

    for line in lines[1:]:
        gender, age, archetype, filename = line.split(",")
        voice_id = f"{gender}_{age}_{archetype}"
        assert filename == f"{voice_id}.mp3"
        assert gender in {"female", "male", "neutral"}
        assert age in {"child", "teen", "young", "adult", "elder"}
        assert archetype in {
            "tsundere",
            "yandere",
            "cool",
            "pure",
            "elegant",
            "tomboy",
            "warrior",
            "mage",
            "rogue",
            "villain",
            "mad",
        }
