from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "frontend" / "src" / "app" / "page.tsx"


def test_frontend_extracts_fastapi_detail_instead_of_raw_internal_server_error():
    page = PAGE.read_text(encoding="utf-8")
    assert "async function readErrorMessage" in page
    assert "data.detail" in page
    assert "response.statusText" in page
    assert "await readErrorMessage(response)" in page
