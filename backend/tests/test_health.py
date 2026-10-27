from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_reports_no_secret() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert isinstance(body["credential_configured"], bool)
    # The health payload must never carry the key or any part of it.
    assert "api_key" not in body
    assert "LLM_" not in response.text
