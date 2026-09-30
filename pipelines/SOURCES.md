# Forecast archive candidate

## Integrated research adapter

`pipelines.open_meteo` uses [Open-Meteo Single Runs](https://open-meteo.com/en/docs/single-runs-api)
with the ECMWF IFS model identifier `ecmwf_ifs`. Its `run=` parameter selects
one model initialization, preserving the issued run. The archive documents
ECMWF IFS 9 km coverage from March 2024 and a 10-day horizon. A 00 UTC run is
typically available several hours later; `run_current` waits until 08 UTC.
The adapter requests daily precipitation totals with UTC day boundaries and
millimetre units. The paired reference comes from the
[Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api)
using `models=era5`. ERA5 is a **reanalysis proxy**, not a station observation.
Both source responses and SHA-256 checksums are retained during backfill.

The [Open-Meteo terms](https://open-meteo.com/en/terms) govern use; the free
API is for non-commercial work. Commercial publication needs an appropriate
license or replacement provider. Forecast accuracy claims must be conditioned
on the source, time period, geography and reanalysis reference.

[Open-Meteo Previous Runs](https://open-meteo.com/en/docs/previous-runs-api)
offers fixed Day 1–7 archive comparisons for some models. Its
[Single Runs and Historical Forecast documentation](https://open-meteo.com/en/docs/historical-forecast-api)
need separate assessment for issued-run preservation and Day 8–10 coverage.
The stitched Historical Forecast API is unsuitable as an issued forecast
archive for training Day 1–10 reliability labels. The
[Open-Meteo terms](https://open-meteo.com/en/terms) limit free use to
non-commercial activity; a paid agreement may be needed for commercial use.

This is a candidate source, not an integrated live feed, a complete India
archive, or a license approval. Before ingestion, verify model coverage,
retention, run timestamps, historical availability, licensing and observation
alignment. Preserve source run identifiers and raw file checksums.
