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
