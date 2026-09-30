"""Publish an approved baseline's 00 UTC ECMWF run to Supabase.

Requires SUPABASE_DATABASE_URL (direct Postgres URI). This worker writes only
complete eligible results and invokes the atomic publication function.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import date, datetime, time, timezone
from pathlib import Path

from ml.research_train import predict
from pipelines.open_meteo import FORECAST_MODEL, FORECAST_URL, SOURCE_ID, daily_values, fetch_json


def forecast_rows(payload: dict, location_id: str, run: datetime) -> list[dict]:
    values = daily_values(payload)
    rows = []
    for lead in range(1, 11):
        day = (run.date().toordinal() + lead)
        valid_day = date.fromordinal(day).isoformat()
        if valid_day not in values:
            continue
        rows.append({"location_id": location_id, "variable": "rainfall_mm", "issued_at": run,
                     "valid_at": datetime.combine(date.fromisoformat(valid_day), time.min, timezone.utc),
                     "forecast_value": values[valid_day], "lead_day": lead,
                     "season": "monsoon" if date.fromisoformat(valid_day).month in (6, 7, 8, 9) else "other"})
    return rows


def fetch_run(location: dict, run: datetime) -> tuple[list[dict], str]:
    params = {"latitude": location["latitude"], "longitude": location["longitude"],
              "daily": "precipitation_sum", "timezone": "UTC", "precipitation_unit": "mm",
              "run": run.strftime("%Y-%m-%dT%H:%M"), "forecast_days": 11,
              "models": FORECAST_MODEL}
    payload, raw, _ = fetch_json(FORECAST_URL, params)
    return forecast_rows(payload, location["slug"], run), hashlib.sha256(raw).hexdigest()


def load_registered_model(conn, model_code: str) -> dict:
    record = conn.execute(
        "select artifact_json, approved_for_publication from public.model_versions where code=%s",
        (model_code,),
    ).fetchone()
    if record is None or not record[1] or not isinstance(record[0], dict):
        raise ValueError("approved model artifact missing from database")
    return record[0]


def publish(conn, model: dict, model_code: str, run: datetime, locations: list[dict]) -> int:
    if model.get("kind") != "smoothed_historical_rate_v1":
        raise ValueError("unsupported model kind")
    prepared = []
    checksums = []
    for location in locations:
        rows, sha = fetch_run(location, run)
        if len(rows) != 10:
            raise ValueError(f"incomplete 10-day forecast for {location['slug']}: {len(rows)} days")
        prepared.extend(rows)
        checksums.append(sha)
    if not prepared:
        raise ValueError("no forecast values were available")
    source_sha = hashlib.sha256("".join(checksums).encode()).hexdigest()
    with conn.transaction():
        source = conn.execute("select id from public.forecast_sources where code=%s", (SOURCE_ID,)).fetchone()
        if source is None:
            raise ValueError("forecast source missing; apply migrations")
        model_record = conn.execute("select id, approved_for_publication, artifact_json from public.model_versions where code=%s",
                                    (model_code,)).fetchone()
        if model_record is None or not model_record[1]:
            raise ValueError("model version missing or not approved for publication")
        if model_record[2] != model:
            raise ValueError("provided model differs from the registered approved artifact")
        run_key = f"{SOURCE_ID}:{run:%Y%m%dT%H%MZ}"
        forecast_run = conn.execute("""insert into public.forecast_runs
          (source_id, issued_at, source_run_key, source_file_sha256) values (%s,%s,%s,%s)
          on conflict (source_id, source_run_key) do update set source_file_sha256=excluded.source_file_sha256
          returning id""", (source[0], run, run_key, source_sha)).fetchone()[0]
        batch = conn.execute("""insert into public.prediction_batches
          (forecast_run_id, model_version_id, expected_count) values (%s,%s,%s)
          on conflict (forecast_run_id, model_version_id) do nothing returning id""",
          (forecast_run, model_record[0], len(prepared))).fetchone()
        if batch is None:
            raise ValueError("run/model already exists; refusing to replace published or staged batch")
        batch_id = batch[0]
        slugs = [loc["slug"] for loc in locations]
        location_ids = {slug: uid for slug, uid in conn.execute(
            "select slug,id from public.locations where slug = any(%s) and active", (slugs,)).fetchall()}
        if len(location_ids) != len(slugs):
            raise ValueError("one or more locations missing from database")
        for row in prepared:
            score = predict(model, row)
            p = score["risk_probability"]
            if not 0 <= p <= 1:
                raise ValueError("invalid probability")
            summary = (f"Research estimate for UTC-day rainfall. Historical group contains "
                       f"{score['group_training_count']} training cases; compare with reanalysis after the day ends.")
            explanation = json.dumps({"headline": "Rainfall forecast reliability estimate",
                                      "summary": summary, "drivers": ["historical rate", "lead day", "forecast amount"]})
            conn.execute("""insert into public.risk_predictions
              (batch_id, location_id, variable, valid_at, lead_day, forecast_value,
               risk_probability, error_threshold, explanation)
              values (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)""",
              (batch_id, location_ids[row["location_id"]], row["variable"], row["valid_at"],
               row["lead_day"], row["forecast_value"], p, score["error_threshold"], explanation))
        conn.execute("select public.publish_prediction_batch(%s)", (batch_id,))
    return len(prepared)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, help="optional local artifact; must match registered artifact")
    parser.add_argument("--model-code", required=True)
    parser.add_argument("--run", required=True, help="00 UTC run date YYYY-MM-DD")
    parser.add_argument("--locations", type=Path, required=True)
    args = parser.parse_args()
    run = datetime.combine(date.fromisoformat(args.run), time.min, timezone.utc)
    locations = json.loads(args.locations.read_text(encoding="utf-8"))
    database_url = os.environ.get("SUPABASE_DATABASE_URL")
    if not database_url:
        raise SystemExit("SUPABASE_DATABASE_URL is required")
    import psycopg
    with psycopg.connect(database_url) as conn:
        model = load_registered_model(conn, args.model_code)
        if args.model and json.loads(args.model.read_text(encoding="utf-8")) != model:
            raise ValueError("local model differs from registered model")
        count = publish(conn, model, args.model_code, run, locations)
    print(f"Published {count} research predictions")


if __name__ == "__main__":
    main()
