from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_frontend_dev_port_is_3100_and_api_base_is_8100():
    package_json = (ROOT / "frontend" / "package.json").read_text(encoding="utf-8")
    utils_ts = (ROOT / "frontend" / "src" / "lib" / "utils.ts").read_text(encoding="utf-8")
    assert "-p 3100" in package_json
    assert "-p 3000" not in package_json
    assert "http://127.0.0.1:8100" in utils_ts
    assert "http://127.0.0.1:8000" not in utils_ts


def test_backend_cors_port_is_3100_not_3000():
    main_py = (ROOT / "backend" / "main.py").read_text(encoding="utf-8")
    assert "http://127.0.0.1:3100" in main_py
    assert "http://localhost:3100" in main_py
    assert "http://127.0.0.1:3000" not in main_py


def test_gptsovits_default_port_is_9100_not_9880():
    gptsovits_py = (ROOT / "src" / "voice_lab" / "gptsovits.py").read_text(encoding="utf-8")
    assert "http://127.0.0.1:9100" in gptsovits_py
    assert "port: int = 9100" in gptsovits_py
    assert "9880" not in gptsovits_py
