"""Clearly illustrative product scenarios. No forecast or observed data lives here."""

from __future__ import annotations

REGIONS = [
    {"id": "ahmedabad", "name": "Ahmedabad", "state": "Gujarat", "latitude": 23.0225, "longitude": 72.5714},
    {"id": "bengaluru", "name": "Bengaluru", "state": "Karnataka", "latitude": 12.9716, "longitude": 77.5946},
    {"id": "delhi", "name": "Delhi", "state": "Delhi", "latitude": 28.6139, "longitude": 77.2090},
    {"id": "jaipur", "name": "Jaipur", "state": "Rajasthan", "latitude": 26.9124, "longitude": 75.7873},
    {"id": "kolkata", "name": "Kolkata", "state": "West Bengal", "latitude": 22.5726, "longitude": 88.3639},
    {"id": "mumbai", "name": "Mumbai", "state": "Maharashtra", "latitude": 19.0760, "longitude": 72.8777},
]

VARIABLES = [
    {"id": "rainfall", "label": "Rainfall", "unit": "mm"},
    {"id": "temperature", "label": "Temperature", "unit": "°C"},
    {"id": "wind", "label": "Wind", "unit": "km/h"},
]

DISCLAIMER = (
    "Illustrative product scenario only. FBIE has no operational forecast data, "
    "trained model, measured probability, or verified historical results yet. "
    "Do not use this example for weather decisions."
)

SCENARIOS = {
    "rainfall": {
        "headline": "See where a rainfall forecast might be vulnerable",
        "explanation": (
            "A future FBIE analysis would compare the forecast with historical errors, "
            "independent forecast guidance, and changes between forecast runs. "
            "This screen demonstrates the intended explanation format."
        ),
        "drivers": [
            {"label": "Forecast agreement", "detail": "Future analysis will check whether available forecast systems place rain in different areas."},
            {"label": "Run-to-run changes", "detail": "Future analysis will track whether predicted rain location and amount shift between updates."},
            {"label": "Local history", "detail": "Future analysis will compare similar past forecasts with observed rainfall."},
        ],
        "failure_modes": [
            {"name": "Rain arrives in a different area", "probability": None},
            {"name": "Rainfall amount differs substantially", "probability": None},
            {"name": "Rain arrives earlier or later", "probability": None},
        ],
    },
    "temperature": {
        "headline": "Understand possible temperature forecast errors",
        "explanation": (
            "A future FBIE analysis would estimate whether the local temperature forecast "
            "could miss a defined error threshold. This screen demonstrates how those results will appear."
        ),
        "drivers": [
            {"label": "Local historical error", "detail": "Future analysis will measure errors for this place, season, and lead time."},
            {"label": "Forecast spread", "detail": "Future analysis will compare available temperature forecasts."},
        ],
        "failure_modes": [
            {"name": "Warmer than forecast", "probability": None},
            {"name": "Cooler than forecast", "probability": None},
        ],
    },
    "wind": {
        "headline": "Understand possible wind forecast errors",
        "explanation": (
            "A future FBIE analysis would examine wind speed and direction errors "
            "against observations. This screen is an interface example only."
        ),
        "drivers": [
            {"label": "Forecast spread", "detail": "Future analysis will measure disagreement in wind speed and direction."},
            {"label": "Local terrain", "detail": "Future analysis will account for measured local error patterns where data supports it."},
        ],
        "failure_modes": [
            {"name": "Wind stronger than forecast", "probability": None},
            {"name": "Wind direction differs", "probability": None},
        ],
    },
}


def region_by_id(region_id: str) -> dict | None:
    return next((region for region in REGIONS if region["id"] == region_id), None)


def scenario(region_id: str, variable: str, lead_day: int) -> dict:
    region = region_by_id(region_id)
    if region is None:
        raise ValueError("Unknown region")
    if variable not in SCENARIOS:
        raise ValueError("Unknown variable")
    if not 1 <= lead_day <= 10:
        raise ValueError("Lead day must be between 1 and 10")
    details = SCENARIOS[variable]
    return {
        "id": f"demo:{region_id}:{variable}:{lead_day}",
        "status": "demo",
        "mode": "demo",
        "disclaimer": DISCLAIMER,
        "region_id": region["id"],
        "region_name": region["name"],
        "region": region,
        "variable": variable,
        "lead_day": lead_day,
        "probability": None,
        "risk_level": "illustrative",
        "headline": details["headline"],
        "explanation": details["explanation"],
        "drivers": details["drivers"],
        "failure_modes": details["failure_modes"],
        "forecast_time": None,
        "valid_time": None,
        "model_version": None,
        "source": {"type": "synthetic_scenario", "name": "FBIE interface demonstration", "retrieved_at": None},
        "provenance": {"forecast_run_id": None, "observation_batch_id": None, "model_version": None},
    }
