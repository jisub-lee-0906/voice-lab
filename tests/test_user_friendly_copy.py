import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app
from voice_lab.ui_config import QUICK_START_STEPS, format_candidate_summary


def test_user_copy_uses_save_not_approve_language():
    combined = "\n".join(QUICK_START_STEPS) + "\n" + format_candidate_summary(
        "준비 완료", [{"seed": 1000, "ogg": "/tmp/a.ogg"}]
    )
    assert "승인" not in combined
    assert "저장" in combined
    assert "마음에 드는" in combined


def test_candidate_cards_have_equalizing_css_class():
    css = app.CUSTOM_CSS
    assert ".candidate-card" in css
    assert "min-height" in css
    assert "height: 96px" in css
