"""Verify published UTC-day rainfall predictions against ERA5 reanalysis.

ERA5 is a model analysis proxy. The record carries that distinction publicly.
Run after the reference source has had time to publish finalized data.
"""

from __future__ import annotations

import argparse
import hashlib
import os
from datetime import datetime, timedelta, timezone

from pipelines.open_meteo import REFERENCE_ID, REFERENCE_URL, daily_values, fetch_json


def verify_pending(conn, *, lag_days: int = 7, limit: int = 100) -> dict:
    if lag_days < 1 or limit < 1:
        raise ValueError("lag_days and limit must be positive")
    cutoff = datetime.now(timezone.utc) - timedelta(days=lag_days)
    candidates = conn.execute("""select p.id, p.valid_at, p.forecast_value, p.error_threshold,
      l.latitude, l.longitude from public.risk_predictions p
      join public.prediction_batches b on b.id=p.batch_id
      join public.locations l on l.id=p.location_id
      left join public.verification_records v on v.prediction_id=p.id
      where b.status='published' and p.variable='rainfall_mm' and p.valid_at < %s
        and v.id is null order by p.valid_at asc limit %s""", (cutoff, limit)).fetchall()
    completed = skipped = 0
    cache = {}
    for prediction_id, valid_at, forecast, threshold, lat, lon in candidates:
        day = valid_at.date().isoformat()
        key = (lat, lon, day)
        if key not in cache:
            payload, raw, _ = fetch_json(REFERENCE_URL, {
                "latitude": lat, "longitude": lon, "daily": "precipitation_sum",
                "timezone": "UTC", "precipitation_unit": "mm", "models": "era5",
                "start_date": day, "end_date": day})
            cache[key] = (daily_values(payload), hashlib.sha256(raw).hexdigest())
        observed = cache[key][0].get(day)
        if observed is None or forecast is None:
            skipped += 1
            continue
        absolute_error = abs(observed - forecast)
        busted = absolute_error > threshold or ((observed >= 10) != (forecast >= 10))
        with conn.transaction():
            conn.execute("""insert into public.verification_records
              (prediction_id, observed_at, observed_value, absolute_error, busted,
               reference_source, reference_kind, reference_file_sha256)
              values (%s,%s,%s,%s,%s,%s,%s,%s)
              on conflict (prediction_id) do nothing""",
              (prediction_id, valid_at, observed, absolute_error, busted,
               REFERENCE_ID, "reanalysis_proxy", cache[key][1]))
        completed += 1
    return {"selected": len(candidates), "completed": completed, "skipped": skipped}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lag-days", type=int, default=7)
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    database_url = os.environ.get("SUPABASE_DATABASE_URL")
    if not database_url:
        raise SystemExit("SUPABASE_DATABASE_URL is required")
    import psycopg
    with psycopg.connect(database_url) as conn:
        print(verify_pending(conn, lag_days=args.lag_days, limit=args.limit))


if __name__ == "__main__":
    main()
