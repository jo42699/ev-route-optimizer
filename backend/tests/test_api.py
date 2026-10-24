from fastapi.testclient import TestClient

from app.main import app


def test_metadata_and_health_do_not_need_external_calls():
    client = TestClient(app)
    metadata = client.get("/api/metadata")
    assert metadata.status_code == 200
    assert "CCS" in metadata.json()["connector_types"]
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["status"] == "degraded"


def test_history_is_explicitly_unavailable():
    response = TestClient(app).get("/api/chargers/ocm:12/history")
    assert response.status_code == 200
    assert response.json()["available"] is False
    assert response.json()["observations"] == []
