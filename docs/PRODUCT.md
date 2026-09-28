# FBIE product contract

## Promise

FBIE explains where an Indian weather forecast could go wrong, how it may fail, and what past evidence supports the warning. Every warning is later compared with observations.

## First release

- Public landing page that states the value in plain language.
- A dashboard to inspect location, variable, and forecast lead day.
- A prediction detail with issuance and valid times, failure modes, and supporting signals.
- A verification view that shows forecast versus observed outcome.
- Methodology and model status so coverage and uncertainty are explicit.
- User accounts and saved locations when Supabase is connected.

The initial scientific milestone is rainfall reliability in selected Indian regions. The interface may demonstrate other variables, but it must label unsupported outputs as examples.

## Data rules

1. No demo probability may appear as a live forecast.
2. Missing input data is unavailable, never zero risk.
3. A result identifies its source run, location, valid time, and model version.
4. The website must distinguish model signals, historical evidence, and the model's estimate.
5. Historical validation separates training, calibration, and test periods chronologically.
6. An operational claim requires measured skill against simple baselines and visible calibration results.

## Future capabilities

Spatial rainfall displacement, historical analog retrieval, forecast-run tracking, and advanced multivariate models are research milestones. They enter operational use only when they improve held-out results and can be explained accurately.
