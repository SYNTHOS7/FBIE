"""Focused tests for leakage boundaries, target semantics and evaluation."""

import csv
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ml.baseline import evaluate, fit, is_bust, predict, time_split
from pipelines.paired import load_pairs


def case(day, forecast, observed, variable="rainfall_mm"):
    issued = datetime(2025, 1, 1, tzinfo=timezone.utc) + timedelta(days=day)
    return {
        "location_id": "loc-1", "variable": variable,
        "issued_at": issued, "valid_at": issued + timedelta(days=2),
        "forecast_value": forecast, "observed_value": observed,
        "lead_day": 2, "season": "other", "source_id": "example",
    }


class BaselineTests(unittest.TestCase):
    def test_compound_rainfall_label_stays_binary(self):
        row = case(0, 12, 0)
        self.assertIs(is_bust(row, 5, 10), True)
        self.assertEqual(int(is_bust(row, 5, 10)), 1)

    def test_time_split_prevents_future_training(self):
        rows = [case(i, 12, 0 if i % 2 else 13) for i in range(10)]
        train, test = time_split(rows)
        self.assertLess(max(row["issued_at"] for row in train), min(row["issued_at"] for row in test))
        model = fit(train, min_group=1)
        self.assertLess(datetime.fromisoformat(model["train_last_issued_at"]), min(row["issued_at"] for row in test))
        report = evaluate(model, test)
        self.assertEqual(report["test_count"], len(test))
        self.assertTrue(0 <= report["brier_score"] <= 1)
        self.assertTrue(0 <= predict(model, test[0])["risk_probability"] <= 1)

    def test_csv_rejects_unaligned_or_duplicate_cases(self):
        headers = ["location_id", "variable", "issued_at", "valid_at", "forecast_value", "observed_value"]
        row = ["loc-1", "rainfall_mm", "2025-01-01T00:00:00Z", "2025-01-02T00:00:00Z", "5", "7"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pairs.csv"
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.writer(stream)
                writer.writerow(headers)
                writer.writerow(row)
                writer.writerow(row)
            with self.assertRaisesRegex(ValueError, "duplicate"):
                load_pairs(path)
            row[3] = "2024-12-31T00:00:00Z"
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.writer(stream)
                writer.writerow(headers)
                writer.writerow(row)
            with self.assertRaisesRegex(ValueError, "valid_at"):
                load_pairs(path)


if __name__ == "__main__":
    unittest.main()
