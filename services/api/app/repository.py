"""PostgreSQL repository for published FBIE data."""

from __future__ import annotations

import os
from uuid import UUID

import psycopg
from psycopg.rows import dict_row


def configured() -> bool:
    return bool(os.getenv("DATABASE_URL", "").strip())


def connect():
    return psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=5, row_factory=dict_row)


def _region(row: dict) -> dict:
    return {
        "id": row["slug"], "name": row["name"], "state": row["state"],
        "latitude": row["latitude"], "longitude": row["longitude"],
    }


def locations(q: str = "") -> list[dict]:
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT slug, name, state, latitude, longitude FROM public.locations
               WHERE active AND (%s = '' OR name ILIKE %s OR state ILIKE %s)
               ORDER BY name LIMIT 100""", (q, f"%{q}%", f"%{q}%"),
        )
        return [_region(row) for row in cur.fetchall()]


def location(region_id: str) -> dict | None:
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT slug, name, state, latitude, longitude FROM public.locations
               WHERE active AND slug = %s""", (region_id,),
        )
        row = cur.fetchone()
    return _region(row) if row else None


def forecast_runs() -> list[dict]:
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT DISTINCT r.id, r.issued_at, s.code AS source_code,
                      s.name AS source_name, max(b.published_at) AS published_at
                 FROM public.forecast_runs r
                 JOIN public.forecast_sources s ON s.id = r.source_id
                 JOIN public.prediction_batches b ON b.forecast_run_id = r.id
                 JOIN public.model_versions m ON m.id = b.model_version_id
                WHERE b.status = 'published' AND m.approved_for_publication
                GROUP BY r.id, r.issued_at, s.code, s.name
                ORDER BY r.issued_at DESC LIMIT 20"""
        )
        rows = cur.fetchall()
    return [{**row, "id": str(row["id"]), "issued_at": row["issued_at"].isoformat(),
             "published_at": row["published_at"].isoformat()} for row in rows]


def live_coverage() -> dict:
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT DISTINCT region_id, variable, lead_day
                 FROM public.api_published_risk
                ORDER BY region_id, variable, lead_day"""
        )
        rows = cur.fetchall()
        cur.execute("SELECT max(forecast_time) AS latest_run FROM public.api_published_risk")
        latest = cur.fetchone()["latest_run"]
    return {
        "latest_run": latest.isoformat() if latest else None,
        "operational_coverage": [
            {"region_id": row["region_id"], "variable": row["variable"], "lead_day": row["lead_day"]}
            for row in rows
        ],
        "active_region_ids": sorted({row["region_id"] for row in rows}),
        "variables": sorted({row["variable"] for row in rows}),
        "lead_days": sorted({row["lead_day"] for row in rows}),
    }


RISK_SELECT = """SELECT provenance->>'prediction_id' AS prediction_id,
                       region_id, variable, lead_day, probability, risk_level,
                       headline, explanation, drivers, failure_modes,
                       forecast_time, valid_time, model_version, source, provenance
                  FROM public.api_published_risk"""


def _risk(row: dict | None) -> dict | None:
    if row is None:
        return None
    probability = row["probability"]
    if probability is None or not 0 <= float(probability) <= 1:
        raise ValueError("Published risk probability must be between 0 and 1")
    if not row["model_version"] or not row["source"] or not row["provenance"]:
        raise ValueError("Published risk has incomplete provenance")
    result = dict(row)
    result["id"] = str(result.pop("prediction_id"))
    drivers = result.get("drivers") or []
    result["drivers"] = [
        item if isinstance(item, dict) else {"label": str(item), "detail": ""}
        for item in drivers
    ]
    modes = result.get("failure_modes") or []
    if isinstance(modes, dict):
        modes = [{"name": key, "probability": value} for key, value in modes.items()]
    result["failure_modes"] = modes
    result["probability"] = float(probability)
    result["forecast_time"] = result["forecast_time"].isoformat()
    result["valid_time"] = result["valid_time"].isoformat()
    result.update({
        "status": "live", "mode": "live", "disclaimer": None,
        "forecast_value": result["provenance"].get("forecast_value"),
        "error_threshold": result["provenance"].get("error_threshold"),
        "predicted_error_p10": result["provenance"].get("predicted_error_p10"),
        "predicted_error_p90": result["provenance"].get("predicted_error_p90"),
    })
    return result


def live_risk(region_id: str, variable: str, lead_day: int) -> dict | None:
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            RISK_SELECT + """ WHERE region_id = %s AND variable = %s AND lead_day = %s
                               ORDER BY forecast_time DESC LIMIT 1""",
            (region_id, variable, lead_day),
        )
        return _risk(cur.fetchone())


def risk_by_id(prediction_id: str) -> dict | None:
    try:
        UUID(prediction_id)
    except ValueError:
        return None
    with connect() as conn, conn.cursor() as cur:
        cur.execute(RISK_SELECT + " WHERE provenance->>'prediction_id' = %s LIMIT 1", (prediction_id,))
        return _risk(cur.fetchone())


def model_status() -> dict | None:
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT m.code, m.model_kind, m.trained_through, m.evaluation,
                      max(b.published_at) AS latest_publication
                 FROM public.model_versions m
                 JOIN public.prediction_batches b ON b.model_version_id = m.id
                WHERE m.approved_for_publication AND b.status = 'published'
                GROUP BY m.id ORDER BY latest_publication DESC LIMIT 1"""
        )
        row = cur.fetchone()
    if not row:
        return None
    return {
        "status": "published", "active_model_version": row["code"],
        "model_kind": row["model_kind"],
        "training_period": {"through": row["trained_through"].isoformat() if row["trained_through"] else None},
        "evaluation": row["evaluation"],
        "latest_publication": row["latest_publication"].isoformat(),
    }


def saved_locations(user_id: str) -> list[dict]:
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT l.slug, l.name, l.state, l.latitude, l.longitude
                 FROM public.saved_locations s JOIN public.locations l ON l.id = s.location_id
                WHERE s.user_id = %s AND l.active ORDER BY s.created_at DESC""", (user_id,),
        )
        return [_region(row) for row in cur.fetchall()]


def save_location(user_id: str, region_id: str) -> dict | None:
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            """INSERT INTO public.saved_locations (user_id, location_id)
               SELECT %s, id FROM public.locations WHERE slug = %s AND active
               ON CONFLICT DO NOTHING""", (user_id, region_id),
        )
        cur.execute(
            "SELECT slug, name, state, latitude, longitude FROM public.locations WHERE slug = %s AND active",
            (region_id,),
        )
        row = cur.fetchone()
    return _region(row) if row else None


def delete_saved_location(user_id: str, region_id: str) -> None:
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            """DELETE FROM public.saved_locations s USING public.locations l
                WHERE s.location_id = l.id AND s.user_id = %s AND l.slug = %s""",
            (user_id, region_id),
        )


def verification(limit: int = 30) -> dict:
    """Return only outcomes for published predictions and approved models."""
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT count(*) AS verified_predictions,
                      avg(CASE WHEN v.busted THEN 1.0 ELSE 0.0 END) AS bust_rate
                 FROM public.verification_records v
                 JOIN public.risk_predictions p ON p.id = v.prediction_id
                 JOIN public.prediction_batches b ON b.id = p.batch_id
                 JOIN public.model_versions m ON m.id = b.model_version_id
                WHERE b.status = 'published' AND m.approved_for_publication"""
        )
        summary_row = cur.fetchone()
        cur.execute(
            """SELECT v.id, l.name AS region_name, p.variable, p.valid_at,
                      v.observed_at, p.risk_probability, v.busted,
                      v.reference_kind, v.reference_source,
                      v.observed_value, v.absolute_error, p.error_threshold
                 FROM public.verification_records v
                 JOIN public.risk_predictions p ON p.id = v.prediction_id
                 JOIN public.locations l ON l.id = p.location_id
                 JOIN public.prediction_batches b ON b.id = p.batch_id
                 JOIN public.model_versions m ON m.id = b.model_version_id
                WHERE b.status = 'published' AND m.approved_for_publication
                ORDER BY v.verified_at DESC LIMIT %s""", (limit,),
        )
        rows = cur.fetchall()
    variable_names = {
        "rainfall_mm": "rainfall",
        "temperature_c": "temperature",
        "wind_speed_mps": "wind",
    }
    cases = []
    for row in rows:
        proxy = row["reference_kind"] == "reanalysis_proxy"
        outcome = "bust" if row["busted"] else "within_threshold"
        reference = "reanalysis estimate" if proxy else "reference measurement"
        summary = (
            f"Forecast absolute error {row['absolute_error']:.2f} exceeded "
            f"the {row['error_threshold']:.2f} threshold against {reference}."
            if row["busted"] else
            f"Forecast absolute error {row['absolute_error']:.2f} stayed within "
            f"the {row['error_threshold']:.2f} threshold against {reference}."
        )
        cases.append({
            "id": str(row["id"]), "region_name": row["region_name"],
            "variable": variable_names.get(row["variable"], row["variable"]),
            "forecast_date": row["valid_at"].isoformat(),
            "observed_date": row["observed_at"].isoformat(),
            "predicted_risk": float(row["risk_probability"]),
            "outcome": outcome, "summary": summary,
            "reference_kind": row["reference_kind"],
            "reference_source": row["reference_source"],
            "observed_value": row["observed_value"],
            "absolute_error": row["absolute_error"],
            "error_threshold": row["error_threshold"],
        })
    return {
        "summary": {
            "verified_predictions": summary_row["verified_predictions"],
            "skill": None, "calibration": None,
            "bust_rate": float(summary_row["bust_rate"]) if summary_row["bust_rate"] is not None else None,
        },
        "cases": cases,
        "message": "Skill and calibration require a larger held-out verification set.",
    }
