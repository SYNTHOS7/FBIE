from uuid import uuid4

from fastapi.testclient import TestClient

from app import main


client = TestClient(main.app)
REGION = {"id": "mumbai", "name": "Mumbai", "state": "Maharashtra", "latitude": 19.076, "longitude": 72.8777}


def test_live_coverage_is_explicit_about_supported_cells(monkeypatch):
    monkeypatch.setattr(main.repository, "configured", lambda: True)
    monkeypatch.setattr(main.repository, "locations", lambda q="": [REGION])
    monkeypatch.setattr(main.repository, "live_coverage", lambda: {
        "latest_run": "2026-09-28T00:00:00+00:00",
        "operational_coverage": [{"region_id": "mumbai", "variable": "rainfall", "lead_day": 1}],
        "lead_days": [1],
    })
    body = client.get("/v1/coverage").json()
    assert body["mode"] == "live"
    assert body["latest_run"] == "2026-09-28T00:00:00+00:00"
    assert body["operational_coverage"] == [{"region_id": "mumbai", "variable": "rainfall", "lead_day": 1}]


def test_published_risk_exposes_provenance_and_interval(monkeypatch):
    prediction_id = str(uuid4())
    monkeypatch.setattr(main.repository, "configured", lambda: True)
    monkeypatch.setattr(main.repository, "location", lambda slug: REGION if slug == "mumbai" else None)
    monkeypatch.setattr(main.repository, "live_risk", lambda *args: {
        "id": prediction_id, "mode": "live", "status": "live",
        "probability": 0.64, "risk_level": "elevated", "model_version": "baseline-v1",
        "source": {"name": "forecast source"}, "provenance": {"prediction_id": prediction_id},
        "forecast_value": 20.0, "error_threshold": 10.0,
        "predicted_error_p10": -8.0, "predicted_error_p90": 18.0,
        "forecast_time": "2026-09-28T00:00:00+00:00",
        "valid_time": "2026-09-29T00:00:00+00:00",
    })
    body = client.get("/v1/risk", params={"region_id": "mumbai", "variable": "rainfall", "lead_day": 1}).json()
    assert body["mode"] == "live"
    assert body["probability"] == 0.64
    assert body["predicted_error_p10"] == -8.0
    assert body["provenance"]["prediction_id"] == prediction_id


def test_unpublished_region_result_is_not_an_invented_risk(monkeypatch):
    monkeypatch.setattr(main.repository, "configured", lambda: True)
    monkeypatch.setattr(main.repository, "location", lambda slug: REGION)
    monkeypatch.setattr(main.repository, "live_risk", lambda *args: None)
    body = client.get("/v1/risk", params={"region_id": "mumbai", "variable": "rainfall", "lead_day": 1}).json()
    assert body["probability"] is None
    assert body["mode"] == "demo"


def test_verification_keeps_reference_kind(monkeypatch):
    monkeypatch.setattr(main.repository, "configured", lambda: True)
    monkeypatch.setattr(main.repository, "verification", lambda limit: {
        "summary": {"verified_predictions": 1, "skill": None, "calibration": None},
        "cases": [{"id": "one", "reference_kind": "reanalysis_proxy", "summary": "Compared against reanalysis estimate."}],
    })
    body = client.get("/v1/verification").json()
    assert body["mode"] == "live"
    assert body["cases"][0]["reference_kind"] == "reanalysis_proxy"


def test_saved_location_requires_valid_supabase_access_token(monkeypatch):
    monkeypatch.setattr(main.repository, "configured", lambda: True)
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "publishable-key")
    calls = []

    class FakeResponse:
        status_code = 401

    def fake_get(*args, **kwargs):
        calls.append(kwargs["headers"]["Authorization"])
        return FakeResponse()

    monkeypatch.setattr(main.httpx, "get", fake_get)
    response = client.get("/v1/me/saved-locations", headers={"Authorization": "Bearer forged.jwt.payload"})
    assert response.status_code == 401
    assert calls == ["Bearer forged.jwt.payload"]


def test_saved_locations_are_scoped_to_verified_user(monkeypatch):
    user_id = str(uuid4())
    monkeypatch.setattr(main.repository, "configured", lambda: True)
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "publishable-key")

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"id": user_id}

    monkeypatch.setattr(main.httpx, "get", lambda *args, **kwargs: FakeResponse())
    captured = []
    monkeypatch.setattr(main.repository, "saved_locations", lambda uid: captured.append(uid) or [REGION])
    body = client.get("/v1/me/saved-locations", headers={"Authorization": "Bearer valid"}).json()
    assert captured == [user_id]
    assert body["locations"] == [REGION]


def test_repository_normalizes_published_explanation_and_checks_probability():
    from datetime import datetime, timezone
    from app import repository

    row = {
        "prediction_id": str(uuid4()), "region_id": "mumbai", "variable": "rainfall",
        "lead_day": 1, "probability": 0.42, "risk_level": "elevated",
        "headline": "Estimate", "explanation": "Context",
        "drivers": ["historical rate", "forecast amount"],
        "failure_modes": {},
        "forecast_time": datetime(2026, 9, 28, tzinfo=timezone.utc),
        "valid_time": datetime(2026, 9, 29, tzinfo=timezone.utc),
        "model_version": "baseline-v1",
        "source": {"name": "source"},
        "provenance": {"forecast_value": 10, "error_threshold": 5},
    }
    result = repository._risk(row)
    assert result["drivers"][0] == {"label": "historical rate", "detail": ""}
    assert result["failure_modes"] == []
    assert result["error_threshold"] == 5
    row["probability"] = 1.2
    import pytest
    with pytest.raises(ValueError, match="probability"):
        repository._risk(row)


def test_coverage_counts_unique_cells_and_latest_run_separately(monkeypatch):
    from datetime import datetime, timezone
    from app import repository

    issued = datetime(2026, 9, 29, tzinfo=timezone.utc)
    queries = []

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, query):
            queries.append(query)

        def fetchall(self):
            return [
                {"region_id": "mumbai", "variable": "rainfall", "lead_day": 1},
                {"region_id": "mumbai", "variable": "rainfall", "lead_day": 2},
            ]

        def fetchone(self):
            return {"latest_run": issued}

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def cursor(self):
            return FakeCursor()

    monkeypatch.setattr(repository, "connect", lambda: FakeConnection())
    result = repository.live_coverage()
    assert result["latest_run"] == issued.isoformat()
    assert result["operational_coverage"] == [
        {"region_id": "mumbai", "variable": "rainfall", "lead_day": 1},
        {"region_id": "mumbai", "variable": "rainfall", "lead_day": 2},
    ]
    assert "SELECT DISTINCT region_id, variable, lead_day" in queries[0]
    assert "forecast_time" not in queries[0]
    assert "max(forecast_time)" in queries[1]
