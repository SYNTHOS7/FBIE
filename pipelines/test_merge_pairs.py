import csv
import tempfile
import unittest
from pathlib import Path

from pipelines.merge_pairs import merge


class MergePairsTests(unittest.TestCase):
    def test_merges_unique_issued_forecasts_and_rejects_conflicts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fields = ["location_id", "variable", "issued_at", "valid_at",
                      "forecast_value", "observed_value"]
            base = {"location_id": "mumbai", "variable": "rainfall_mm",
                    "forecast_value": "2", "observed_value": "3"}

            def write(path, issued, valid, forecast="2"):
                with path.open("w", newline="", encoding="utf-8") as stream:
                    writer = csv.DictWriter(stream, fieldnames=fields)
                    writer.writeheader()
                    writer.writerow({**base, "issued_at": issued, "valid_at": valid,
                                     "forecast_value": forecast})

            first, second, conflict = (root / name for name in ("a.csv", "b.csv", "c.csv"))
            write(first, "2026-06-01T00:00:00+00:00", "2026-06-02T00:00:00+00:00")
            write(second, "2026-06-02T00:00:00+00:00", "2026-06-03T00:00:00+00:00")
            write(conflict, "2026-06-01T00:00:00+00:00", "2026-06-02T00:00:00+00:00", "9")
            result = merge([first, second], root / "merged.csv")
            self.assertEqual(result["paired_count"], 2)
            self.assertTrue((root / "merged.manifest.json").exists())
            with self.assertRaisesRegex(ValueError, "conflicting pair"):
                merge([first, conflict], root / "bad.csv")


if __name__ == "__main__":
    unittest.main()
