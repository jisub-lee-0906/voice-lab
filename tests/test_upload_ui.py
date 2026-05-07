from pathlib import Path

PAGE = Path(__file__).resolve().parents[1] / "frontend" / "src" / "app" / "page.tsx"


def test_upload_ui_makes_file_selection_and_reference_step_explicit():
    page = PAGE.read_text(encoding="utf-8")
    assert 'id="voice-file-input"' in page
    assert 'htmlFor="voice-file-input"' in page
    assert "선택된 파일" in page
    assert "파일을 고른 뒤 참조 음성 만들기를 눌러주세요" in page
    assert "음성 파일이나 기존 파일 경로를 먼저 넣어주세요" in page
    assert "const hasAudioSource" in page
