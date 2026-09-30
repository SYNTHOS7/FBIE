# Offline baseline

Train and evaluate only after supplying a checked, real paired forecast and
observation CSV (see `../pipelines/README.md`):

```bash
python -m ml.baseline path/to/pairs.csv --output path/to/results
python -m unittest ml.test_baseline
```

The command writes `model.json` and `evaluation.json`. It splits by forecast
issuance time, fits absolute-error thresholds on the earlier partition, then
evaluates bust risk on later cases. Rainfall labels include both an error
threshold and occurrence mismatch at 10 mm; the target is binary. The model is
a smoothed historical bust rate for variable, season, lead day and forecast
amount band. It reports the Brier score alongside a variable-level historical
rate reference, plus observed rates by probability band.

This is a research baseline. It lacks external forecast ingestion, spatial
matching, source quality review, rolling backtests, confidence intervals and
evidence of useful skill. `model.json` is not automatically approved for
publication. Do not present its output as a live operational risk forecast.

The executable research path is `python -m ml.research_train data/pairs.csv
--output data/model`. It reserves the latest issue times for untouched testing,
uses an earlier chronological slice for logistic probability calibration, and
fits all thresholds using the oldest training slice. The output includes the
calibrated model JSON and held-out Brier score against a historical-rate
reference. `python -m ml.register_model --model data/model/model.json
--evaluation data/model/evaluation.json --code research-v1` enforces minimum
sample and held-out improvement gates before storing the immutable artifact in
Supabase. This remains a research estimate until geographic and temporal
representativeness are reviewed.
