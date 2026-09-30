"""Synthetic unit fixtures validate split boundaries only; they are never product data."""

import unittest
from datetime import datetime, timedelta, timezone

from ml.register_model import gate
from ml.research_train import predict, train


def fixture(day: int) -> dict:
    issued = datetime(2025, 1, 1, tzinfo=timezone.utc) + timedelta(days=day)
    valid = issued + timedelta(days=10)
    return {"location_id": "test", "variable": "rainfall_mm", "issued_at": issued,
            "valid_at": valid, "forecast_value": 12.0 if day % 4 else 2.0,
            "observed_value": 0.0 if day % 5 else 15.0,
            "lead_day": 10, "season": "monsoon" if valid.month in (6, 7, 8, 9) else "other"}


class ResearchTrainingTests(unittest.TestCase):
    def test_training_calibration_test_are_chronological(self):
        rows = [{**fixture(day), "location_id": f"test-{city}"}
                for day in range(250) for city in range(6)]
        model, report = train(rows, min_group=1)
        train_end = datetime.fromisoformat(report["train_last_issued_at"])
        calibration_start = datetime.fromisoformat(report["calibration_first_issued_at"])
        calibration_end = datetime.fromisoformat(report["calibration_last_issued_at"])
        test_start = datetime.fromisoformat(report["test_first_issued_at"])
        self.assertLess(train_end, calibration_start)
        self.assertLess(calibration_end, test_start)
        self.assertLess(datetime.fromisoformat(report["train_last_valid_at"]), calibration_start)
        self.assertLess(datetime.fromisoformat(report["calibration_last_valid_at"]), test_start)
        self.assertGreaterEqual(report["test_issue_days"], 20)
        self.assertTrue(0 <= predict(model, fixture(251))["risk_probability"] <= 1)

    def test_registration_rejects_unproven_skill(self):
        with self.assertRaisesRegex(ValueError, "beat"):
            gate({"test_count": 100, "calibration_count": 30,
                  "brier_score": 0.3, "reference_brier_score": 0.2,
                  "training_data_sha256": "abc"})

    def test_registration_rejects_poor_untouched_calibration(self):
        report = {
            "test_count": 100, "brier_score": 0.1, "reference_brier_score": 0.2,
            "calibration_bins": [{"count": 100, "mean_probability": 0.2,
                                  "observed_rate": 0.5}],
            "calibration_count": 100, "test_issue_days": 20, "embargo_days": 10,
            "train_last_issued_at": "2025-01-01T00:00:00+00:00",
            "train_last_valid_at": "2025-01-11T00:00:00+00:00",
            "calibration_first_issued_at": "2025-01-12T00:00:00+00:00",
            "calibration_last_issued_at": "2025-02-01T00:00:00+00:00",
            "calibration_last_valid_at": "2025-02-11T00:00:00+00:00",
            "test_first_issued_at": "2025-02-12T00:00:00+00:00",
            "training_data_sha256": "abc",
        }
        with self.assertRaisesRegex(ValueError, "calibration error"):
            gate(report)
        report["calibration_bins"][0]["observed_rate"] = 0.2
        gate(report)


if __name__ == "__main__":
    unittest.main()
