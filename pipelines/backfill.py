"""Backfill multiple issued runs into one provenance-preserving paired dataset."""

from __future__ import annotations

import argparse
import csv
import json
import time
from datetime import date, datetime, time as clock_time, timedelta, timezone
from pathlib import Path

from pipelines.open_meteo import acquire
from pipelines.paired import load_pairs


def backfill(locations: list[dict], start: date, end: date, output: Path,
             raw_dir: Path, pause_seconds: float = 1.0) -> dict:
    if end < start:
        raise ValueError("date range must be chronological")
    if end + timedelta(days=17) >= datetime.now(timezone.utc).date():
        raise ValueError("end date must precede today by at least 17 days for reanalysis latency")
    if pause_seconds < 0:
        raise ValueError("pause must be nonnegative")
    rows, manifests, failures = [], [], []
    day = start
    while day <= end:
        run = datetime.combine(day, clock_time.min, timezone.utc)
        for location in locations:
            try:
                acquired, manifest = acquire(location, run, raw_dir)
                rows.extend(acquired)
                manifests.append(manifest)
            except (OSError, TimeoutError, ValueError) as exc:
                failures.append({"run": run.isoformat(), "location": location.get("slug"),
                                 "error": str(exc)})
            if pause_seconds:
                time.sleep(pause_seconds)
        day += timedelta(days=1)
    if not rows:
        raise ValueError(f"no pairs acquired; {len(failures)} source requests failed")
    keys = set()
    for row in rows:
        key = (row["location_id"], row["variable"], row["issued_at"], row["valid_at"])
        if key in keys:
            raise ValueError(f"duplicate pair {key}")
        keys.add(key)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    load_pairs(output)  # Validate the final training contract before declaring success.
    manifest = {"paired_count": len(rows), "requested_runs": (end - start).days + 1,
                "locations": len(locations), "successful_location_runs": len(manifests),
                "failures": failures, "sources": manifests,
                "reference_kind": "reanalysis_proxy_not_station_observation"}
    output.with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--locations", type=Path, required=True)
    parser.add_argument("--start-run", type=date.fromisoformat, required=True)
    parser.add_argument("--end-run", type=date.fromisoformat, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--pause-seconds", type=float, default=1.0)
    args = parser.parse_args()
    locations = json.loads(args.locations.read_text(encoding="utf-8"))
    result = backfill(locations, args.start_run, args.end_run,
                      args.output, args.raw_dir, args.pause_seconds)
    print(f"Wrote {result['paired_count']} paired cases; {len(result['failures'])} location runs failed")


if __name__ == "__main__":
    main()
