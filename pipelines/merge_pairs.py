"""Merge validated backfill CSV files without duplicate or conflicting cases."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

from pipelines.paired import load_pairs


def merge(inputs: list[Path], output: Path) -> dict:
    if len(inputs) < 2:
        raise ValueError("at least two backfill CSV files are required")
    cases: dict[tuple[str, str, str, str], dict[str, str]] = {}
    fields: list[str] | None = None
    sources = []
    for path in inputs:
        load_pairs(path)
        raw = path.read_bytes()
        sources.append({"path": str(path), "sha256": hashlib.sha256(raw).hexdigest()})
        with path.open(newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream)
            if fields is None:
                fields = reader.fieldnames
            elif reader.fieldnames != fields:
                raise ValueError(f"CSV fields differ in {path}")
            for row in reader:
                key = tuple(row[name] for name in ("location_id", "variable", "issued_at", "valid_at"))
                if key in cases and cases[key] != row:
                    raise ValueError(f"conflicting pair {key}")
                cases[key] = row
    if not cases or fields is None:
        raise ValueError("no paired cases were found")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(cases[key] for key in sorted(cases, key=lambda item: (item[2], item[0], item[3])))
    load_pairs(output)
    manifest = {"paired_count": len(cases), "inputs": sources,
                "output_sha256": hashlib.sha256(output.read_bytes()).hexdigest()}
    output.with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = merge(args.inputs, args.output)
    print(f"Merged {result['paired_count']} paired cases into {args.output}")


if __name__ == "__main__":
    main()
