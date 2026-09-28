"""Canonicalize validated paired forecast/observation records with provenance."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

from pipelines.paired import load_pairs


FIELDS = (
    "location_id", "variable", "issued_at", "valid_at", "forecast_value",
    "observed_value", "lead_day", "season", "source_id",
)


def normalize(input_path: Path, output_path: Path) -> dict:
    rows = load_pairs(input_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row[field].isoformat() if field in ("issued_at", "valid_at") else row[field]
                             for field in FIELDS})
    manifest = {
        "input_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
        "output_sha256": hashlib.sha256(output_path.read_bytes()).hexdigest(),
        "row_count": len(rows),
        "variables": sorted({row["variable"] for row in rows}),
        "first_issued_at": rows[0]["issued_at"].isoformat(),
        "last_issued_at": rows[-1]["issued_at"].isoformat(),
    }
    output_path.with_suffix(output_path.suffix + ".manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(normalize(args.input, args.output), indent=2))


if __name__ == "__main__":
    main()
