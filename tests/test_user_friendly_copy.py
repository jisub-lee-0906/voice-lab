from pathlib import Path

from voice_lab.ui_config import QUICK_START_STEPS, format_candidate_summary

FRONTEND_PAGE = Path(__file__).resolve().parents[1] / "frontend" / "src" / "app" / "page.tsx"


def test_user_copy_uses_save_not_approve_language():
    combined = "\n".join(QUICK_START_STEPS) + "\n" + format_candidate_summary(
        "준비 완료", [{"seed": 1000, "ogg": "/tmp/a.ogg"}]
    )
    assert "승인" not in combined
    assert "저장" in combined
    assert "마음에 드는" in combined


def test_frontend_copy_uses_plain_user_language():
    page = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "새 음성 만들기" in page
    assert "마음에 드는 음성 저장" in page
    assert "후보 1 승인" not in page
