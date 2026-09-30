"""Synthetic unit fixtures validate split boundaries only; they are never product data."""

import unittest
from datetime import datetime, timedelta, timezone

from ml.register_model import gate
from ml.research_train import predict, train


def fixture(day: int) -> dict:
    issued = datetime(2025, 1, 1, tzinfo=timezone.utc) + timedelta(days=day)
    valid = issued + timedelta(days=2)
    return {"location_id": "test", "variable": "rainfall_mm", "issued_at": issued,
            "valid_at": valid, "forecast_value": 12.0 if day % 4 else 2.0,
            "observed_value": 0.0 if day % 5 else 15.0,
            "lead_day": 2, "season": "monsoon" if valid.month in (6, 7, 8, 9) else "other"}


class ResearchTrainingTests(unittest.TestCase):
    def test_training_calibration_test_are_chronological(self):
        model, report = train([fixture(day) for day in range(250)], min_group=1)
        train_end = datetime.fromisoformat(report["train_last_issued_at"])
        calibration_start = datetime.fromisoformat(report["calibration_first_issued_at"])
        calibration_end = datetime.fromisoformat(report["calibration_last_issued_at"])
        test_start = datetime.fromisoformat(report["test_first_issued_at"])
        self.assertLess(train_end, calibration_start)
        self.assertLess(calibration_end, test_start)
        self.assertTrue(0 <= predict(model, fixture(251))["risk_probability"] <= 1)

    def test_registration_rejects_unproven_skill(self):
        with self.assertRaisesRegex(ValueError, "beat"):
            gate({"test_count": 100, "calibration_count": 30,
                  "brier_score": 0.3, "reference_brier_score": 0.2,
                  "training_data_sha256": "abc"})


if __name__ == "__main__":
    unittest.main()
