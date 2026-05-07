from fastapi.testclient import TestClient

from backend.main import app


def test_health_returns_ok():
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_config_exposes_beginner_friendly_defaults():
    client = TestClient(app)
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert data["defaultApiUrl"] == "http://127.0.0.1:9880"
    assert "기본" in data["emotions"]
    assert data["referenceDuration"]["min"] == 3
    assert data["referenceDuration"]["max"] == 10
