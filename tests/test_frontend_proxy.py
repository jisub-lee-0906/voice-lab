from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_frontend_uses_same_origin_api_base_to_avoid_browser_fetch_failures():
    utils_ts = (ROOT / "frontend" / "src" / "lib" / "utils.ts").read_text(encoding="utf-8")
    assert 'export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";' in utils_ts
    assert "http://127.0.0.1:8100" not in utils_ts


def test_next_config_rewrites_api_and_media_to_backend_8100():
    config_ts = (ROOT / "frontend" / "next.config.ts").read_text(encoding="utf-8")
    assert "async rewrites()" in config_ts
    assert 'BACKEND_ORIGIN = process.env.VOICE_LAB_BACKEND_ORIGIN ?? "http://127.0.0.1:8100"' in config_ts
    assert 'destination: `${BACKEND_ORIGIN}/api/:path*`' in config_ts
    assert 'destination: `${BACKEND_ORIGIN}/media/:path*`' in config_ts
