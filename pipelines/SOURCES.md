# Forecast archive candidate

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
