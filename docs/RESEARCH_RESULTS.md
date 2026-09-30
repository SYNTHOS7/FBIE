# Rainfall research check — 30 September 2026

FBIE paired archived 00 UTC ECMWF IFS forecasts for six Indian city points with
Open-Meteo ERA5 **reanalysis estimates** for matching UTC daily rainfall totals.
The archive spans issued runs from 22 March through 25 July 2026. It contains
7,302 paired cases. Source-request manifests record 15 failed city-runs from
network errors; no values were imputed. Raw responses, pair files, checksums,
and the model artifact remain in the local ignored `data/` directory.

The chronological training workflow kept 65 issued days for training, 16 for
calibration, and 25 later issued days for an untouched test. A ten-day embargo
at each boundary kept the forecast-valid dates of earlier cases out of the
next period.

| Untouched test measure | Result |
| --- | ---: |
| Paired cases | 1,500 |
| FBIE Brier score | 0.302 |
| Simple historical-rate Brier score | 0.407 |
| Observed bust rate | 50.1% |
| Expected calibration error | 0.235 |

The model beats that reference on Brier score but **fails the publication
calibration limit of 0.10**. For example, 1,230 test cases averaged 25.7%
predicted risk while 48.9% actually met the bust definition against ERA5.
FBIE therefore did **not** register or publish this model. The public site
continues to show no measured risk percentage until a model clears the gate.

This is a research check, not evidence of operational weather reliability.
The reference is reanalysis rather than a rain-gauge observation; city-point
sampling, source shifts, seasonal drift, and geographic generalization need
more evaluation. The Open-Meteo source is credited in the website and its
[terms](https://open-meteo.com/en/terms) govern use of the free research API.
