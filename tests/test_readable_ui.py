from pathlib import Path

FRONTEND_PAGE = Path(__file__).resolve().parents[1] / "frontend" / "src" / "app" / "page.tsx"


def test_next_ui_uses_readable_light_product_surface():
    page = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "bg-white" in page
    assert "text-gray-950" in page
    assert "linear-gradient" not in page
    assert "후보 듣고 승인하기" not in page


def test_next_ui_uses_vertical_voice_results_not_horizontal_candidate_cards():
    page = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "마음에 드는 음성 저장" in page
    assert "가로 카드 대신 세로 목록" in page
    assert "음성 {candidate.index}" in page
