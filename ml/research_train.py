"""Chronological train, calibration and untouched test workflow."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from statistics import mean

from ml.baseline import fit, is_bust, predict as raw_predict, time_split
from pipelines.paired import load_pairs


EMBARGO_DAYS = 10
MIN_TRAIN_ISSUE_DAYS = 30
MIN_CALIBRATION_ISSUE_DAYS = 15
MIN_TEST_ISSUE_DAYS = 20


def distinct_issue_days(rows: list[dict]) -> int:
    return len({row["issued_at"].date() for row in rows})


def purge_before(rows: list[dict], next_rows: list[dict]) -> tuple[list[dict], int]:
    """Drop earlier issue dates until forecast targets cannot cross the boundary."""
    next_first = min(row["issued_at"] for row in next_rows)
    latest_allowed = next_first - timedelta(days=EMBARGO_DAYS)
    kept = [row for row in rows if row["issued_at"] < latest_allowed and row["valid_at"] < next_first]
    if not kept:
        raise ValueError("embargo removed all earlier cases; backfill a longer period")
    dropped_days = len({row["issued_at"].date() for row in rows}) - distinct_issue_days(kept)
    return kept, dropped_days


def predict(model: dict, row: dict) -> dict:
    score = raw_predict(model, row)
    calibration = model.get("calibration")
    if calibration:
        p = min(1 - 1e-6, max(1e-6, score["risk_probability"]))
        x = math.log(p / (1 - p))
        z = max(-30, min(30, calibration["intercept"] + calibration["slope"] * x))
        score["risk_probability"] = 1 / (1 + math.exp(-z))
    return score


def calibrate(model: dict, rows: list[dict]) -> dict:
    if len(rows) < 30:
        raise ValueError("at least 30 independent calibration cases required")
    training = []
    for row in rows:
        result = raw_predict(model, row)
        p = min(1 - 1e-6, max(1e-6, result["risk_probability"]))
        x = math.log(p / (1 - p))
        y = int(is_bust(row, result["error_threshold"], model["rain_event_mm"]))
        training.append((x, y))
    intercept, slope = 0.0, 1.0
    for _ in range(1000):
        gi = gs = 0.0
        for x, y in training:
            z = max(-30, min(30, intercept + slope * x))
            error = 1 / (1 + math.exp(-z)) - y
            gi += error
            gs += error * x
        intercept -= 0.05 * gi / len(training)
        slope -= 0.05 * (gs / len(training) + 0.01 * (slope - 1))
        slope = max(0.0, min(5.0, slope))
    updated = dict(model)
    updated["calibration"] = {"method": "logistic", "intercept": intercept, "slope": slope,
                              "count": len(rows), "last_issued_at": max(r["issued_at"] for r in rows).isoformat()}
    return updated


def evaluate(model: dict, rows: list[dict]) -> dict:
    if not rows:
        raise ValueError("empty test set")
    samples = []
    for row in rows:
        score = predict(model, row)
        label = int(is_bust(row, score["error_threshold"], model["rain_event_mm"]))
        samples.append((score["risk_probability"], score["reference_probability"], label))
    bins = [{"lower": k / 10, "upper": (k + 1) / 10,
             "count": len(group), "mean_probability": mean(p for p, y in group),
             "observed_rate": mean(y for p, y in group)}
            for k in range(10)
            if (group := [(p, y) for p, _, y in samples
                          if k / 10 <= p < (k + 1) / 10 or (k == 9 and p == 1)])]
    return {"test_count": len(samples),
            "test_first_issued_at": min(row["issued_at"] for row in rows).isoformat(),
            "test_last_issued_at": max(row["issued_at"] for row in rows).isoformat(),
            "brier_score": mean((p - y) ** 2 for p, _, y in samples),
            "reference_brier_score": mean((r - y) ** 2 for _, r, y in samples),
            "observed_bust_rate": mean(y for _, _, y in samples),
            "calibration_bins": bins,
            "expected_calibration_error": sum(
                bucket["count"] * abs(bucket["mean_probability"] - bucket["observed_rate"])
                for bucket in bins
            ) / len(samples)}


def train(rows: list[dict], *, min_group: int = 20) -> tuple[dict, dict]:
    development, test = time_split(rows, 0.2)
    early_train, early_calibration = time_split(development, 0.25)
    calibration_rows, calibration_purged_days = purge_before(early_calibration, test)
    train_rows, train_purged_days = purge_before(early_train, calibration_rows)
    if (distinct_issue_days(train_rows) < MIN_TRAIN_ISSUE_DAYS
            or distinct_issue_days(calibration_rows) < MIN_CALIBRATION_ISSUE_DAYS
            or distinct_issue_days(test) < MIN_TEST_ISSUE_DAYS):
        raise ValueError("need >=30 train, >=15 calibration and >=20 untouched test issue days after 10-day embargo")
    if len(train_rows) < 100 or len(test) < 100:
        raise ValueError("need >=100 train and >=100 untouched test cases after embargo")
    model = calibrate(fit(train_rows, min_group=min_group), calibration_rows)
    report = evaluate(model, test)
    report.update({"train_count": len(train_rows), "calibration_count": len(calibration_rows),
                   "train_issue_days": distinct_issue_days(train_rows),
                   "calibration_issue_days": distinct_issue_days(calibration_rows),
                   "test_issue_days": distinct_issue_days(test),
                   "embargo_days": EMBARGO_DAYS,
                   "train_boundary_purged_issue_days": train_purged_days,
                   "calibration_boundary_purged_issue_days": calibration_purged_days,
                   "train_last_issued_at": max(r["issued_at"] for r in train_rows).isoformat(),
                   "train_last_valid_at": max(r["valid_at"] for r in train_rows).isoformat(),
                   "calibration_first_issued_at": min(r["issued_at"] for r in calibration_rows).isoformat(),
                   "calibration_last_issued_at": max(r["issued_at"] for r in calibration_rows).isoformat(),
                   "calibration_last_valid_at": max(r["valid_at"] for r in calibration_rows).isoformat(),
                   "reference_kind": "reanalysis_proxy_if_open_meteo_era5",
                   "warning": "Research estimate; evaluate geographic skill and source changes before relying on it."})
    return model, report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pairs_csv", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = load_pairs(args.pairs_csv)
    model, report = train(rows)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "model.json").write_text(json.dumps(model, indent=2), encoding="utf-8")
    report["training_data_sha256"] = hashlib.sha256(args.pairs_csv.read_bytes()).hexdigest()
    (args.output / "evaluation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
