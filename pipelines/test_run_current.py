import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from pipelines.run_current import already_published, eligible_run, run_jobs


class FakeConnection:
    def __init__(self, row):
        self.row = row
        self.parameters = None

    def execute(self, sql, parameters):
        self.parameters = parameters
        return self

    def fetchone(self):
        return self.row


class ScheduledRunTests(unittest.TestCase):
    def test_eligible_run_waits_until_eight_utc(self):
        self.assertEqual(eligible_run(datetime(2026, 9, 30, 7, tzinfo=timezone.utc)).date().isoformat(),
                         "2026-09-29")
        self.assertEqual(eligible_run(datetime(2026, 9, 30, 8, tzinfo=timezone.utc)).date().isoformat(),
                         "2026-09-30")

    def test_idempotence_lookup_uses_model_and_run(self):
        run = datetime(2026, 9, 30, tzinfo=timezone.utc)
        existing = FakeConnection((1,))
        self.assertTrue(already_published(existing, "model-1", run))
        self.assertEqual(existing.parameters[1:], ("model-1", run))
        self.assertFalse(already_published(FakeConnection(None), "model-1", run))

    def test_retry_skips_publish_but_verifies(self):
        run = datetime(2026, 9, 30, tzinfo=timezone.utc)
        with patch("pipelines.run_current.publish") as publish_mock, \
             patch("pipelines.run_current.verify_pending", return_value={"completed": 2}):
            published, verified, error = run_jobs(FakeConnection((1,)), {}, "model-1", run, [], 10)
        publish_mock.assert_not_called()
        self.assertEqual(published, 0)
        self.assertEqual(verified["completed"], 2)
        self.assertIsNone(error)

    def test_publish_failure_still_verifies_before_returning_error(self):
        run = datetime(2026, 9, 30, tzinfo=timezone.utc)
        with patch("pipelines.run_current.publish", side_effect=RuntimeError("source delayed")), \
             patch("pipelines.run_current.verify_pending", return_value={"completed": 1}):
            published, verified, error = run_jobs(FakeConnection(None), {}, "model-1", run, [], 10)
        self.assertEqual(published, 0)
        self.assertEqual(verified["completed"], 1)
        self.assertIsInstance(error, RuntimeError)


if __name__ == "__main__":
    unittest.main()
