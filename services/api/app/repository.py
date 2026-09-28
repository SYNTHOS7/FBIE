"""Read only published predictions through a database view."""

from __future__ import annotations

import os

import psycopg
from psycopg.rows import dict_row


def live_risk(region_id: str, variable: str, lead_day: int) -> dict | None:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        return None
    with psycopg.connect(database_url, connect_timeout=5, row_factory=dict_row) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT region_id, variable, lead_day, probability, risk_level,
                       headline, explanation, drivers, failure_modes,
                       forecast_time, valid_time, model_version, source, provenance
                  FROM public.api_published_risk
                 WHERE region_id = %s AND variable = %s AND lead_day = %s
                 ORDER BY forecast_time DESC
                 LIMIT 1
                """,
                (region_id, variable, lead_day),
            )
            result = cursor.fetchone()
    if result is None:
        return None
    probability = result["probability"]
    if probability is None or not 0 <= float(probability) <= 1:
        raise ValueError("Published risk probability must be between 0 and 1")
    if not result["model_version"] or not result["source"] or not result["provenance"]:
        raise ValueError("Published risk has incomplete provenance")
    result["probability"] = float(probability)
    result["forecast_time"] = result["forecast_time"].isoformat() if result["forecast_time"] else None
    result["valid_time"] = result["valid_time"].isoformat() if result["valid_time"] else None
    result["status"] = "live"
    result["mode"] = "live"
    result["disclaimer"] = None
    return result
