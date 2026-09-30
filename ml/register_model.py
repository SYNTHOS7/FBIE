"""Register a trained model only when research publication gates pass."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def gate(report: dict) -> None:
    if report.get("test_count", 0) < 100:
        raise ValueError("publication requires at least 100 untouched test cases")
    if report.get("brier_score", 1) >= report.get("reference_brier_score", 0):
        raise ValueError("model must beat the historical-rate reference on untouched test cases")
    if report.get("calibration_count", 0) < 30:
        raise ValueError("calibration sample too small")
    if not report.get("training_data_sha256"):
        raise ValueError("training data provenance is missing")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--evaluation", type=Path, required=True)
    parser.add_argument("--code", required=True)
    args = parser.parse_args()
    model = json.loads(args.model.read_text(encoding="utf-8"))
    report = json.loads(args.evaluation.read_text(encoding="utf-8"))
    gate(report)
    if model.get("kind") != "smoothed_historical_rate_v1" or not model.get("calibration"):
        raise ValueError("unsupported or uncalibrated model")
    database_url = os.environ.get("SUPABASE_DATABASE_URL")
    if not database_url:
        raise SystemExit("SUPABASE_DATABASE_URL is required")
    import psycopg
    with psycopg.connect(database_url) as conn:
        inserted = conn.execute("""insert into public.model_versions
          (code, model_kind, artifact_json, training_data_sha256, trained_through,
           evaluation, approved_for_publication)
          values (%s,%s,%s::jsonb,%s,%s,%s::jsonb,true)
          on conflict (code) do nothing returning id""",
          (args.code, model["kind"], json.dumps(model), report["training_data_sha256"],
           model["calibration"]["last_issued_at"], json.dumps(report))).fetchone()
        if inserted is None:
            raise ValueError("model code already exists; choose a new immutable version code")
    print(f"Registered publication-approved research model {args.code}")


if __name__ == "__main__":
    main()
