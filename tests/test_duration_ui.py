from pathlib import Path

PAGE = Path(__file__).resolve().parents[1] / "frontend" / "src" / "app" / "page.tsx"


def test_duration_inputs_have_bounds_and_decimal_parsing_helpers():
    page = PAGE.read_text(encoding="utf-8")
    assert "function parseSeconds" in page
    assert "시작 초는 0 이상이어야 합니다" in page
    assert "길이 초는 3~10초 사이여야 합니다" in page
    assert 'min="0"' in page
    assert 'min="3"' in page
    assert 'max="10"' in page
    assert 'step="0.1"' in page
