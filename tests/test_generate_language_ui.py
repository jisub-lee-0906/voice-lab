from pathlib import Path

PAGE = Path(__file__).resolve().parents[1] / "frontend" / "src" / "app" / "page.tsx"


def test_generate_defaults_target_text_to_korean_and_does_not_fake_reference_transcript():
    page = PAGE.read_text(encoding="utf-8")
    assert 'text_lang: "ko"' in page
    assert 'prompt_lang: "auto"' in page
    assert "참조 음성의 실제 대사를 모르면 비워두세요" in page
    assert "읽힐 대사를 여기에 다시 넣으면 품질이 나빠질 수 있어요" in page
