"""Train and evaluate a transparent historical forecast-bust baseline.

This is an offline benchmark, not a production weather model. It uses only
issuance-time features at prediction: variable, season, lead and forecast amount.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean

from pipelines.paired import load_pairs


def quantile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def threshold_key(row: dict) -> str:
    return f"{row['variable']}|{row['season']}|{row['lead_day']}"


def amount_band(row: dict) -> str:
    value = row["forecast_value"]
    if row["variable"] == "rainfall_mm":
        return "dry" if value < 1 else "light" if value < 10 else "heavy"
    if row["variable"] == "wind_speed_mps":
        return "low" if value < 5 else "moderate" if value < 12 else "high"
    return "cold" if value < 15 else "mild" if value < 30 else "hot"


def risk_key(row: dict) -> str:
    return f"{threshold_key(row)}|{amount_band(row)}"


def absolute_error(row: dict) -> float:
    return abs(row["forecast_value"] - row["observed_value"])


def is_bust(row: dict, threshold: float, rain_event_mm: float) -> bool:
    event_mismatch = (row["forecast_value"] >= rain_event_mm) != (row["observed_value"] >= rain_event_mm)
    return absolute_error(row) > threshold or (row["variable"] == "rainfall_mm" and event_mismatch)


def time_split(rows: list[dict], test_fraction: float = 0.2) -> tuple[list[dict], list[dict]]:
    if not 0 < test_fraction < 1:
        raise ValueError("test_fraction must be between 0 and 1")
    issue_times = sorted({row["issued_at"] for row in rows})
    if len(issue_times) < 5:
        raise ValueError("at least five distinct issue times are needed")
    cutoff = issue_times[max(1, math.floor(len(issue_times) * (1 - test_fraction)))]
    train = [row for row in rows if row["issued_at"] < cutoff]
    test = [row for row in rows if row["issued_at"] >= cutoff]
    if not train or not test:
        raise ValueError("time split produced an empty partition")
    return train, test


def fit(rows: list[dict], *, error_quantile: float = 0.9, rain_event_mm: float = 10.0, min_group: int = 20) -> dict:
    if not 0 < error_quantile < 1 or rain_event_mm <= 0 or min_group < 1:
        raise ValueError("invalid fit settings")
    errors: dict[str, list[float]] = defaultdict(list)
    by_variable: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        errors[threshold_key(row)].append(absolute_error(row))
        by_variable[row["variable"]].append(absolute_error(row))
    fallback = {key: quantile(values, error_quantile) for key, values in by_variable.items()}
    thresholds = {key: quantile(values, error_quantile) for key, values in errors.items() if len(values) >= min_group}

    risk_counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    variable_counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for row in rows:
        threshold = thresholds.get(threshold_key(row), fallback[row["variable"]])
        label = int(is_bust(row, threshold, rain_event_mm))
        for bucket in (risk_counts[risk_key(row)], variable_counts[row["variable"]]):
            bucket[0] += label
            bucket[1] += 1
    return {
        "kind": "smoothed_historical_rate_v1", "error_quantile": error_quantile,
        "rain_event_mm": rain_event_mm, "min_group": min_group,
        "thresholds": thresholds, "variable_thresholds": fallback,
        "risk_counts": dict(risk_counts), "variable_counts": dict(variable_counts),
        "train_count": len(rows),
        "train_last_issued_at": max(row["issued_at"] for row in rows).isoformat(),
    }


def predict(model: dict, row: dict, smoothing: float = 20.0) -> dict:
    variable = row["variable"]
    if variable not in model["variable_counts"]:
        raise ValueError(f"model has no training cases for {variable}")
    threshold = model["thresholds"].get(threshold_key(row), model["variable_thresholds"][variable])
    positives, total = model["variable_counts"][variable]
    prior = positives / total
    group_positives, group_total = model["risk_counts"].get(risk_key(row), [0, 0])
    probability = (group_positives + smoothing * prior) / (group_total + smoothing)
    return {"risk_probability": probability, "error_threshold": threshold,
            "reference_probability": prior, "group_training_count": group_total}


def evaluate(model: dict, rows: list[dict]) -> dict:
    if not rows:
        raise ValueError("evaluation requires rows")
    scored = []
    for row in rows:
        result = predict(model, row)
        label = int(is_bust(row, result["error_threshold"], model["rain_event_mm"]))
        scored.append((result["risk_probability"], result["reference_probability"], label))
    buckets = []
    for low in range(0, 10):
        members = [(p, y) for p, _, y in scored if low / 10 <= p < (low + 1) / 10 or (low == 9 and p == 1)]
        if members:
            buckets.append({"probability_band": f"{low / 10:.1f}-{(low + 1) / 10:.1f}",
                            "count": len(members), "mean_predicted": mean(p for p, _ in members),
                            "observed_rate": mean(y for _, y in members)})
    return {
        "test_count": len(scored), "observed_bust_rate": mean(y for _, _, y in scored),
        "brier_score": mean((p - y) ** 2 for p, _, y in scored),
        "reference_brier_score": mean((r - y) ** 2 for _, r, y in scored),
        "calibration_bins": buckets,
        "test_first_issued_at": min(row["issued_at"] for row in rows).isoformat(),
        "test_last_issued_at": max(row["issued_at"] for row in rows).isoformat(),
        "warning": "Research baseline only. Evaluate coverage, calibration, source quality and geographic representativeness before publication.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pairs_csv", type=Path)
    parser.add_argument("--output", type=Path, required=True, help="directory for model.json and evaluation.json")
    parser.add_argument("--test-fraction", type=float, default=0.2)
    parser.add_argument("--min-group", type=int, default=20)
    args = parser.parse_args()
    rows = load_pairs(args.pairs_csv)
    train, test = time_split(rows, args.test_fraction)
    model = fit(train, min_group=args.min_group)
    report = evaluate(model, test)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "model.json").write_text(json.dumps(model, indent=2), encoding="utf-8")
    (args.output / "evaluation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
