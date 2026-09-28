"""Validate paired forecast/observation CSVs before model training.

Input is one row per issued forecast, location, variable and valid time. Observed
values may be supplied only after verification; they are never model features.
"""

from __future__ import annotations

import argparse
import csv
import math
from datetime import datetime, timezone
from pathlib import Path


REQUIRED = (
    "location_id", "variable", "issued_at", "valid_at",
    "forecast_value", "observed_value",
)
VARIABLES = {"rainfall_mm", "temperature_c", "wind_speed_mps"}


def parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamps must include a UTC offset")
    return parsed.astimezone(timezone.utc)


def load_pairs(path: str | Path) -> list[dict]:
    with Path(path).open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        missing = set(REQUIRED) - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"missing columns: {', '.join(sorted(missing))}")
        rows = []
        keys = set()
        for line, raw in enumerate(reader, 2):
            try:
                location = raw["location_id"].strip()
                variable = raw["variable"].strip()
                if not location or variable not in VARIABLES:
                    raise ValueError("invalid location_id or variable")
                issued = parse_time(raw["issued_at"].strip())
                valid = parse_time(raw["valid_at"].strip())
                if valid <= issued:
                    raise ValueError("valid_at must be later than issued_at")
                lead_days = (valid - issued).total_seconds() / 86400
                if lead_days > 10:
                    raise ValueError("lead must be at most 10 days")
                forecast = float(raw["forecast_value"])
                observed = float(raw["observed_value"])
                if not all(math.isfinite(n) for n in (forecast, observed)):
                    raise ValueError("values must be finite")
                if variable == "rainfall_mm" and (forecast < 0 or observed < 0):
                    raise ValueError("rainfall cannot be negative")
                if variable == "wind_speed_mps" and (forecast < 0 or observed < 0):
                    raise ValueError("wind speed cannot be negative")
                key = (location, variable, issued, valid)
                if key in keys:
                    raise ValueError("duplicate forecast key")
                keys.add(key)
                rows.append({
                    "location_id": location, "variable": variable,
                    "issued_at": issued, "valid_at": valid,
                    "forecast_value": forecast, "observed_value": observed,
                    "lead_day": max(1, math.ceil(lead_days)),
                    "season": "monsoon" if valid.month in (6, 7, 8, 9) else "other",
                    "source_id": (raw.get("source_id") or "unspecified").strip(),
                })
            except (KeyError, ValueError, OverflowError) as exc:
                raise ValueError(f"line {line}: {exc}") from exc
    if not rows:
        raise ValueError("CSV contains no data rows")
    return sorted(rows, key=lambda item: (item["issued_at"], item["location_id"]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    args = parser.parse_args()
    rows = load_pairs(args.csv)
    print(f"Validated {len(rows)} paired cases; {rows[0]['issued_at'].date()} to {rows[-1]['issued_at'].date()}")


if __name__ == "__main__":
    main()
