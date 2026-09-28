from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_coverage_is_explicitly_demo():
    response = client.get("/v1/coverage")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "demo"
    assert body["latest_run"] is None
    assert body["operational_coverage"] == []
    assert len(body["regions"]) >= 1


def test_risk_has_no_invented_probability(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    response = client.get("/v1/risk", params={"region_id": "ahmedabad", "variable": "rainfall", "lead_day": 3})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "demo"
    assert body["probability"] is None
    assert body["model_version"] is None
    assert body["source"]["type"] == "synthetic_scenario"
    assert "Do not use" in body["disclaimer"]


def test_unavailable_regions_and_lead_days():
    assert client.get("/v1/risk", params={"region_id": "unknown", "variable": "rainfall", "lead_day": 2}).status_code == 404
    assert client.get("/v1/risk", params={"region_id": "ahmedabad", "variable": "rainfall", "lead_day": 11}).status_code == 422


def test_verification_is_empty_until_observations_exist():
    body = client.get("/v1/verification").json()
    assert body["summary"]["verified_predictions"] == 0
    assert body["summary"]["skill"] is None
    assert body["cases"] == []


def test_no_published_runs_or_model_yet():
    assert client.get("/v1/forecast-runs").json()["runs"] == []
    assert client.get("/v1/models/status").json()["active_model_version"] is None
