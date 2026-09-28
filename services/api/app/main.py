"""FBIE public API. Until validated weather data is available, all risk views are demos."""

from __future__ import annotations

import logging
import os
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .demo import DISCLAIMER, REGIONS, VARIABLES, region_by_id, scenario
from .repository import live_risk

logger = logging.getLogger(__name__)

app = FastAPI(
    title="FBIE API",
    description="Forecast reliability product API. Current risk responses are illustrative only.",
    version="0.1.0",
)

origins = [entry.strip() for entry in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if entry.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "mode": "demo", "version": app.version}


@app.get("/v1/coverage")
def coverage() -> dict:
    return {
        "status": "demo",
        "mode": "demo",
        "disclaimer": DISCLAIMER,
        "regions": REGIONS,
        "variables": VARIABLES,
        "lead_days": list(range(1, 11)),
        "latest_run": None,
        "operational_coverage": [],
    }


@app.get("/v1/locations")
def locations(q: str = "") -> dict:
    term = q.strip().casefold()
    matches = [region for region in REGIONS if term in region["name"].casefold() or term in region["state"].casefold()]
    return {"status": "demo", "locations": matches}


@app.get("/v1/forecast-runs")
def forecast_runs() -> dict:
    return {"status": "demo", "runs": [], "message": "No weather forecast runs have been ingested."}


@app.get("/v1/risk")
def risk(
    region_id: str,
    variable: str,
    lead_day: Annotated[int, Query(ge=1, le=10)],
) -> dict:
    if region_by_id(region_id) is None:
        raise HTTPException(status_code=404, detail="Region not found")
    if variable not in {item["id"] for item in VARIABLES}:
        raise HTTPException(status_code=422, detail="Unsupported variable")
    try:
        live = live_risk(region_id, variable, lead_day)
    except Exception:
        logger.exception('Published risk lookup failed')
        raise HTTPException(status_code=503, detail='Published risk data is temporarily unavailable') from None
    if live is not None:
        region = region_by_id(region_id)
        return {'region_name': region['name'], 'region': region, **live}
    return scenario(region_id, variable, lead_day)


@app.get("/v1/risk/{prediction_id:path}")
def risk_detail(prediction_id: str) -> dict:
    parts = prediction_id.split(":")
    if len(parts) != 4 or parts[0] != "demo":
        raise HTTPException(status_code=404, detail="Prediction not found")
    try:
        lead_day = int(parts[3])
        return scenario(parts[1], parts[2], lead_day)
    except (ValueError, TypeError):
        raise HTTPException(status_code=404, detail="Prediction not found") from None


@app.get("/v1/verification")
def verification() -> dict:
    return {
        "status": "demo",
        "mode": "demo",
        "disclaimer": DISCLAIMER,
        "summary": {"verified_predictions": 0, "skill": None, "calibration": None},
        "cases": [],
        "message": "No forecast and observation pairs have been verified yet.",
    }


@app.get("/v1/models/status")
def model_status() -> dict:
    return {
        "status": "not_trained",
        "active_model_version": None,
        "training_period": None,
        "evaluation": None,
        "message": "A validated forecast reliability model is not available yet.",
    }
