import unittest
from datetime import datetime, timezone

from pipelines.open_meteo import FORECAST_MODEL, daily_values, pair_run
from pipelines.publish import forecast_rows


class OpenMeteoContractTests(unittest.TestCase):
    def test_provider_model_id_is_single_runs_ecmwf_ifs(self):
        self.assertEqual(FORECAST_MODEL, "ecmwf_ifs")

    def setUp(self):
        self.run = datetime(2026, 6, 1, tzinfo=timezone.utc)
        self.forecast = {"utc_offset_seconds": 0, "daily_units": {"precipitation_sum": "mm"},
                         "daily": {"time": ["2026-06-02", "2026-06-03"],
                                    "precipitation_sum": [12.0, 0.0]}}
        self.reference = {"utc_offset_seconds": 0, "daily_units": {"precipitation_sum": "mm"},
                          "daily": {"time": ["2026-06-02", "2026-06-03"],
                                     "precipitation_sum": [2.0, None]}}

    def test_pair_skips_missing_reference_and_preserves_utc_lead(self):
        rows = pair_run(self.forecast, self.reference, location_id="mumbai", run=self.run,
                        forecast_sha256="f", reference_sha256="r")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["valid_at"], "2026-06-02T00:00:00+00:00")
        self.assertEqual(rows[0]["forecast_value"], 12.0)
        self.assertEqual(rows[0]["observed_value"], 2.0)
        self.assertEqual(rows[0]["reference_id"], "open_meteo_era5_reanalysis")

    def test_forecast_rows_do_not_fill_missing_days(self):
        rows = forecast_rows(self.forecast, "mumbai", self.run)
        self.assertEqual([r["lead_day"] for r in rows], [1, 2])
        self.assertEqual(rows[0]["season"], "monsoon")

    def test_rejects_invalid_or_duplicate_daily_values(self):
        with self.assertRaises(ValueError):
            daily_values({"daily": {"time": ["2026-06-02", "2026-06-02"],
                                    "precipitation_sum": [1, 2]}})
        with self.assertRaises(ValueError):
            daily_values({"daily": {"time": ["2026-06-02"], "precipitation_sum": [-1]}})


if __name__ == "__main__":
    unittest.main()
