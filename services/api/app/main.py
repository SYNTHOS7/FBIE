"""FBIE public API: published forecasts, verification, and saved locations."""

from __future__ import annotations

import logging
import os
from typing import Annotated
from uuid import UUID

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import repository
from .demo import DISCLAIMER, REGIONS, VARIABLES, region_by_id, scenario

logger = logging.getLogger(__name__)
app = FastAPI(
    title="FBIE API",
    description="Forecast reliability estimates, provenance, and verification.",
    version="0.2.0",
)

origins = [entry.strip() for entry in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if entry.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


def db_call(operation, *args):
    try:
        return operation(*args)
    except Exception:
        logger.exception("FBIE database lookup failed")
        raise HTTPException(status_code=503, detail="Published data is temporarily unavailable") from None


def all_locations() -> list[dict]:
    return db_call(repository.locations) if repository.configured() else REGIONS


def find_location(region_id: str) -> dict | None:
    return db_call(repository.location, region_id) if repository.configured() else region_by_id(region_id)


def _unavailable_risk(region: dict, variable: str, lead_day: int) -> dict:
    if not repository.configured() and region_by_id(region["id"]):
        return scenario(region["id"], variable, lead_day)
    return {
        "id": None, "status": "no_data", "mode": "demo",
        "disclaimer": "No published forecast reliability estimate exists for this location and lead day.",
        "region_id": region["id"], "region_name": region["name"], "region": region,
        "variable": variable, "lead_day": lead_day, "probability": None,
        "risk_level": "unavailable", "headline": "Forecast reliability unavailable",
        "explanation": "This location has no published estimate for the selected variable and lead day.",
        "drivers": [], "failure_modes": [], "forecast_time": None, "valid_time": None,
        "model_version": None, "source": None, "provenance": None,
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "mode": "configured" if repository.configured() else "demo", "version": app.version}


@app.get("/v1/coverage")
def coverage() -> dict:
    if not repository.configured():
        return {
            "status": "demo", "mode": "demo", "disclaimer": DISCLAIMER,
            "regions": REGIONS, "variables": VARIABLES, "lead_days": list(range(1, 11)),
            "latest_run": None, "operational_coverage": [],
        }
    regions = db_call(repository.locations)
    published = db_call(repository.live_coverage)
    live = bool(published["operational_coverage"])
    return {
        "status": "live" if live else "no_data", "mode": "live" if live else "demo",
        "disclaimer": None if live else "No published forecast risk estimates are available yet.",
        "regions": regions, "variables": VARIABLES,
        "lead_days": published["lead_days"] if live else list(range(1, 11)),
        "latest_run": published["latest_run"],
        "operational_coverage": published["operational_coverage"],
    }


@app.get("/v1/locations")
def locations(q: str = "") -> dict:
    term = q.strip()[:100]
    if repository.configured():
        matches = db_call(repository.locations, term)
    else:
        folded = term.casefold()
        matches = [r for r in REGIONS if folded in r["name"].casefold() or folded in r["state"].casefold()]
    return {"status": "live" if repository.configured() else "demo", "locations": matches}


@app.get("/v1/forecast-runs")
def forecast_runs() -> dict:
    runs = db_call(repository.forecast_runs) if repository.configured() else []
    return {
        "status": "live" if runs else "no_data",
        "runs": runs,
        "message": None if runs else "No published forecast runs are available.",
    }


@app.get("/v1/risk")
def risk(region_id: str, variable: str, lead_day: Annotated[int, Query(ge=1, le=10)]) -> dict:
    region = find_location(region_id)
    if region is None:
        raise HTTPException(status_code=404, detail="Region not found")
    if variable not in {item["id"] for item in VARIABLES}:
        raise HTTPException(status_code=422, detail="Unsupported variable")
    live = db_call(repository.live_risk, region_id, variable, lead_day) if repository.configured() else None
    return {"region_name": region["name"], "region": region, **live} if live else _unavailable_risk(region, variable, lead_day)


@app.get("/v1/risk/{prediction_id}")
def risk_detail(prediction_id: str) -> dict:
    if prediction_id.startswith("demo:"):
        parts = prediction_id.split(":")
        if len(parts) != 4:
            raise HTTPException(status_code=404, detail="Prediction not found")
        try:
            return scenario(parts[1], parts[2], int(parts[3]))
        except (ValueError, TypeError):
            raise HTTPException(status_code=404, detail="Prediction not found") from None
    if not repository.configured():
        raise HTTPException(status_code=404, detail="Prediction not found")
    result = db_call(repository.risk_by_id, prediction_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Prediction not found")
    region = find_location(result["region_id"])
    return {"region_name": region["name"], "region": region, **result}


@app.get("/v1/verification")
def verification(limit: Annotated[int, Query(ge=1, le=100)] = 30) -> dict:
    if repository.configured():
        data = db_call(repository.verification, limit)
        if data["summary"]["verified_predictions"]:
            return {"status": "live", "mode": "live", "disclaimer": None, **data}
    return {
        "status": "no_data", "mode": "demo", "disclaimer": DISCLAIMER,
        "summary": {"verified_predictions": 0, "skill": None, "calibration": None},
        "cases": [], "message": "No published predictions have been verified yet.",
    }


@app.get("/v1/models/status")
def model_status() -> dict:
    model = db_call(repository.model_status) if repository.configured() else None
    return model or {
        "status": "not_trained", "active_model_version": None,
        "training_period": None, "evaluation": None,
        "message": "A validated forecast reliability model is not available yet.",
    }


class SavedLocationInput(BaseModel):
    region_id: str


def authenticated_user(authorization: Annotated[str | None, Header()] = None) -> str:
    base = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_ANON_KEY", "") or os.getenv("SUPABASE_PUBLISHABLE_KEY", "")
    if not repository.configured() or not base or not key:
        raise HTTPException(status_code=503, detail="Saved locations are not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="A Supabase access token is required")
    token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="A Supabase access token is required")
    try:
        response = httpx.get(
            f"{base}/auth/v1/user",
            headers={"apikey": key, "Authorization": f"Bearer {token}"},
            timeout=5,
        )
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail="Authentication service unavailable") from None
    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid or expired access token")
    try:
        user_id = str(UUID(response.json()["id"]))
    except (ValueError, KeyError, TypeError):
        raise HTTPException(status_code=503, detail="Authentication service returned an invalid user") from None
    return user_id


@app.get("/v1/me/saved-locations")
def my_saved_locations(user_id: Annotated[str, Depends(authenticated_user)]) -> dict:
    return {"locations": db_call(repository.saved_locations, user_id)}


@app.post("/v1/me/saved-locations", status_code=201)
def add_saved_location(body: SavedLocationInput, user_id: Annotated[str, Depends(authenticated_user)]) -> dict:
    location = db_call(repository.save_location, user_id, body.region_id)
    if location is None:
        raise HTTPException(status_code=404, detail="Region not found")
    return {"location": location}


@app.delete("/v1/me/saved-locations/{region_id}", status_code=204)
def remove_saved_location(region_id: str, user_id: Annotated[str, Depends(authenticated_user)]) -> Response:
    db_call(repository.delete_saved_location, user_id, region_id)
    return Response(status_code=204)
