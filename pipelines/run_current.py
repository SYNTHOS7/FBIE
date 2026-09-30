"""Scheduled research worker: publish the latest eligible 00 UTC run, then verify older days.

Run after 08:00 UTC so ECMWF 00 UTC output has time to arrive. Requires an
approved model stored in model_versions.artifact_json and database credentials.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, time, timedelta, timezone
from pathlib import Path

from pipelines.open_meteo import SOURCE_ID
from pipelines.publish import load_registered_model, publish
from pipelines.verify import verify_pending


def eligible_run(now: datetime) -> datetime:
    if now.tzinfo is None:
        raise ValueError("current time must be timezone aware")
    current = now.astimezone(timezone.utc)
    day = current.date() if current.hour >= 8 else current.date() - timedelta(days=1)
    return datetime.combine(day, time.min, timezone.utc)


def already_published(conn, model_code: str, run: datetime) -> bool:
    row = conn.execute("""select 1 from public.prediction_batches b
      join public.forecast_runs r on r.id=b.forecast_run_id
      join public.forecast_sources s on s.id=r.source_id
      join public.model_versions m on m.id=b.model_version_id
      where s.code=%s and m.code=%s and r.issued_at=%s and b.status='published'
      limit 1""", (SOURCE_ID, model_code, run)).fetchone()
    return row is not None


def run_jobs(conn, model: dict, model_code: str, run: datetime,
             locations: list[dict], verify_limit: int) -> tuple[int, dict, Exception | None]:
    published = 0
    publish_error = None
    if not already_published(conn, model_code, run):
        try:
            published = publish(conn, model, model_code, run, locations)
        except Exception as exc:
            publish_error = exc
    verified = verify_pending(conn, limit=verify_limit)
    return published, verified, publish_error


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-code", default=os.environ.get("FBIE_MODEL_CODE"))
    parser.add_argument("--locations", type=Path,
                        default=Path(__file__).with_name("research_locations.json"))
    parser.add_argument("--verify-limit", type=int, default=100)
    args = parser.parse_args()
    if not args.model_code:
        raise SystemExit("--model-code or FBIE_MODEL_CODE is required")
    database_url = os.environ.get("SUPABASE_DATABASE_URL")
    if not database_url:
        raise SystemExit("SUPABASE_DATABASE_URL is required")
    locations = json.loads(args.locations.read_text(encoding="utf-8"))
    import psycopg
    with psycopg.connect(database_url) as conn:
        model = load_registered_model(conn, args.model_code)
        run = eligible_run(datetime.now(timezone.utc))
        published, verified, publish_error = run_jobs(
            conn, model, args.model_code, run, locations, args.verify_limit)
    if publish_error is not None:
        raise publish_error
    print(json.dumps({"run": run.isoformat(), "published": published, "verified": verified}))


if __name__ == "__main__":
    main()
