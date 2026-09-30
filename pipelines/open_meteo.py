"""Acquire reproducible ECMWF single runs and a reanalysis reference.

Research use only. Historical Weather is a model analysis, not a rain gauge.
Only complete UTC calendar days from a 00 UTC run are paired.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

FORECAST_URL = "https://single-runs-api.open-meteo.com/v1/forecast"
REFERENCE_URL = "https://archive-api.open-meteo.com/v1/archive"
SOURCE_ID = "open_meteo_ecmwf_ifs_hres_9km"
REFERENCE_ID = "open_meteo_era5_reanalysis"
FORECAST_MODEL = "ecmwf_ifs"


def fetch_json(base: str, params: dict, *, timeout: int = 45) -> tuple[dict, bytes, str]:
    url = f"{base}?{urlencode(params)}"
    request = Request(url, headers={"User-Agent": "FBIE-research/1.0"})
    with urlopen(request, timeout=timeout) as response:
        raw = response.read()
    data = json.loads(raw)
    if data.get("error"):
        raise ValueError(f"Open-Meteo rejected request: {data.get('reason', 'unknown reason')}")
    return data, raw, url


def daily_values(payload: dict) -> dict[str, float]:
    if (payload.get("daily_units") or {}).get("precipitation_sum") != "mm":
        raise ValueError("daily precipitation unit must be mm")
    if payload.get("utc_offset_seconds") != 0:
        raise ValueError("daily precipitation must use UTC accumulation windows")
    daily = payload.get("daily") or {}
    times = daily.get("time") or []
    values = daily.get("precipitation_sum") or []
    if len(times) != len(values) or not times:
        raise ValueError("daily time/precipitation_sum absent or unequal")
    result = {}
    for day, raw in zip(times, values):
        date.fromisoformat(day)
        if raw is None:
            continue
        value = float(raw)
        if not math.isfinite(value) or value < 0 or day in result:
            raise ValueError("invalid or duplicate daily precipitation")
        result[day] = value
    return result


def pair_run(forecast: dict, reference: dict, *, location_id: str,
             run: datetime, forecast_sha256: str, reference_sha256: str) -> list[dict]:
    if run.tzinfo is None or run.utcoffset() != timedelta(0) or run.hour != 0 or run.minute != 0:
        raise ValueError("run must be 00:00 UTC")
    f = daily_values(forecast)
    o = daily_values(reference)
    output = []
    for lead in range(1, 11):
        day = (run.date() + timedelta(days=lead)).isoformat()
        if day not in f or day not in o:
            continue  # No imputation; absence is visible in manifest coverage.
        output.append({
            "location_id": location_id,
            "variable": "rainfall_mm",
            "issued_at": run.isoformat(),
            "valid_at": f"{day}T00:00:00+00:00",
            "forecast_value": f[day],
            "observed_value": o[day],
            "source_id": SOURCE_ID,
            "reference_id": REFERENCE_ID,
            "forecast_sha256": forecast_sha256,
            "reference_sha256": reference_sha256,
        })
    return output


def acquire(location: dict, run: datetime, raw_dir: Path) -> tuple[list[dict], dict]:
    if not location.get("slug") or not -90 <= float(location["latitude"]) <= 90 or not -180 <= float(location["longitude"]) <= 180:
        raise ValueError("invalid location")
    if run.hour != 0 or run.minute != 0 or run.tzinfo != timezone.utc:
        raise ValueError("only 00:00 UTC runs are supported")
    shared = {"latitude": location["latitude"], "longitude": location["longitude"],
              "daily": "precipitation_sum", "timezone": "UTC", "precipitation_unit": "mm"}
    forecast, fraw, furl = fetch_json(FORECAST_URL, {**shared,
        "run": run.strftime("%Y-%m-%dT%H:%M"), "forecast_days": 11,
        "models": FORECAST_MODEL})
    start = (run.date() + timedelta(days=1)).isoformat()
    end = (run.date() + timedelta(days=10)).isoformat()
    reference, oraw, ourl = fetch_json(REFERENCE_URL, {**shared,
        "start_date": start, "end_date": end, "models": "era5"})
    fsha, osha = hashlib.sha256(fraw).hexdigest(), hashlib.sha256(oraw).hexdigest()
    raw_dir.mkdir(parents=True, exist_ok=True)
    base = f"{location['slug']}_{run:%Y%m%dT%H%M}"
    (raw_dir / f"{base}_forecast.json").write_bytes(fraw)
    (raw_dir / f"{base}_reference.json").write_bytes(oraw)
    pairs = pair_run(forecast, reference, location_id=location["slug"], run=run,
                     forecast_sha256=fsha, reference_sha256=osha)
    manifest = {"location_id": location["slug"], "run": run.isoformat(),
                "forecast_source": SOURCE_ID, "reference_source": REFERENCE_ID,
                "reference_kind": "reanalysis_proxy_not_station_observation",
                "forecast_url": furl, "reference_url": ourl,
                "forecast_sha256": fsha, "reference_sha256": osha,
                "paired_days": [r["valid_at"][:10] for r in pairs], "paired_count": len(pairs)}
    (raw_dir / f"{base}_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return pairs, manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--locations", type=Path, required=True, help="JSON array of {slug,latitude,longitude}")
    parser.add_argument("--run", required=True, help="00 UTC run date YYYY-MM-DD")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    args = parser.parse_args()
    run = datetime.combine(date.fromisoformat(args.run), datetime.min.time(), timezone.utc)
    if run.date() + timedelta(days=10) >= datetime.now(timezone.utc).date():
        raise ValueError("reference period is incomplete; use an older run")
    locations = json.loads(args.locations.read_text(encoding="utf-8"))
    if not isinstance(locations, list) or not locations:
        raise ValueError("locations must be a nonempty JSON array")
    rows, manifests = [], []
    for location in locations:
        acquired, manifest = acquire(location, run, args.raw_dir)
        rows.extend(acquired)
        manifests.append(manifest)
    if not rows:
        raise ValueError("no complete paired days returned")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    args.output.with_suffix(".manifest.json").write_text(json.dumps(manifests, indent=2), encoding="utf-8")
    print(f"Wrote {len(rows)} reanalysis-paired cases to {args.output}")


if __name__ == "__main__":
    main()
