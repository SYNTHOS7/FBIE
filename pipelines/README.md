# Paired data contract

`python -m pipelines.paired path/to/pairs.csv` validates a CSV of **real archived
forecasts paired with observations**. The required headers are:

```csv
location_id,variable,issued_at,valid_at,forecast_value,observed_value
```

`source_id` is optional. Times must be ISO 8601 with a UTC offset. Supported
variables and units are `rainfall_mm` (daily accumulation), `temperature_c`
(daily temperature), and `wind_speed_mps` (daily wind speed). All pairs must use
the same variable definition, accumulation window, location, and observation
method. The loader rejects invalid lead times, duplicates, nonfinite values and
negative rainfall/wind values. A source adapter should preserve source run IDs,
original files, checksums, licenses and normalization details before producing
this interchange CSV. CSV alone does not prove that spatial and temporal
alignment was correct.

No weather data is bundled. Do not use the test fixtures as product predictions.

## Executable research path

The Open-Meteo adapter fetches exact ECMWF IFS Single Runs (`models=ecmwf_ifs`)
and pairs the next ten **UTC calendar-day** rainfall totals with the ERA5
reanalysis reference. The two API requests specify identical `timezone=UTC`,
`precipitation_unit=mm`, and daily `precipitation_sum` fields. The adapter
rejects unexpected units/time offsets, preserves raw JSON and checksums, and
leaves incomplete days out of the training set. ERA5 is a **reanalysis proxy**,
not an independent weather station observation. Do not describe comparisons
against it as ground-truth verification.

For a research backfill covering at least 125 distinct issued days for
chronological splits and two ten-day gap periods:

```bash
python -m pipelines.backfill --locations pipelines/research_locations.json --start-run 2025-04-01 --end-run 2025-09-30 --output data/processed/pairs.csv --raw-dir data/raw
python -m ml.research_train data/processed/pairs.csv --output data/processed/model
```

Backfill accepts multi-year ranges. It records failed location/run requests in
the manifest and never imputes missing values. Check the manifest, coverage,
source license and evaluation before registering a model. If the archive is
collected in chunks, merge checked CSV files without duplicate cases:

```bash
python -m pipelines.merge_pairs data/processed/chunk1.csv data/processed/chunk2.csv --output data/processed/pairs.csv
```

Large backfills make
many API requests; the default one-second pause limits request rate.

After applying the Supabase migrations and setting `SUPABASE_DATABASE_URL` to
the direct Postgres connection URI (server-side only):

```bash
python -m ml.register_model --model data/processed/model/model.json --evaluation data/processed/model/evaluation.json --code research-2025-v1
python -m pipelines.publish --model-code research-2025-v1 --run 2026-09-29 --locations pipelines/research_locations.json
python -m pipelines.verify --lag-days 7
```

Registration persists the small JSON model in `model_versions.artifact_json`,
so subsequent workers do not require a local model file. It requires at least
100 untouched test cases over at least 20 distinct issued days, 15 calibration
issue days and 30 training issue days, two ten-day embargos between the three
periods, a better held-out Brier score than the historical-rate reference,
and expected calibration error at most 0.10 on untouched cases.
The `--model` argument to publish is
optional and, if given, must match the registered artifact exactly. Publication
rejects any incomplete 10-day city forecast and is atomic in Postgres.

For a daily scheduled worker, set `FBIE_MODEL_CODE` and
`SUPABASE_DATABASE_URL`, then run `python -m pipelines.run_current` after
08:00 UTC. It chooses the latest 00 UTC run expected to be available and
verifies older predictions. `verify` defaults to a seven-day lag for ERA5
availability; it records `reference_kind=reanalysis_proxy` with each result.
Install `pipelines/requirements.txt` for the worker. A GitHub Actions schedule
can use `SUPABASE_DATABASE_URL` as a repository secret and `FBIE_MODEL_CODE` as
a repository variable. The worker skips a published run on retry and still
verifies pending older predictions. A failed new-run fetch remains a failed job
after verification so operators can investigate it.
