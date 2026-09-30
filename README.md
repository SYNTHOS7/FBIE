# FBIE — Forecast Bust Intelligence Engine

FBIE helps people see **where a weather forecast may be unreliable, what evidence supports that estimate, and how earlier estimates turned out**. The site opens with a plain-language explanation, then offers a forecast explorer, verification history, methodology, and optional saved places.

This repository is a deployable **research prototype**. Its measurable first release covers daily rainfall at six Indian city points and forecast days 1–10. Until a real historical dataset passes the publication gate and a current batch is published, the site labels the experience as a demonstration and shows **no invented risk percentages**. ERA5 comparisons are reanalysis proxies, not rain-gauge observations. The advanced multivariate, ensemble, spatial and failure-mode ideas in the concept documents remain research milestones.

## Architecture

| Part | Code | Host |
| --- | --- | --- |
| Public website and account UI | `apps/web` | Vercel |
| Published-data and saved-place API | `services/api` | Render |
| Auth, data, provenance and verification | `supabase/migrations` | Supabase |
| Archive, train, publish and verify jobs | `pipelines`, `ml` | GitHub Actions / local research runner |

See [system architecture](docs/ARCHITECTURE.md) and [product contract](docs/PRODUCT.md).
The first real-data [research evaluation](docs/RESEARCH_RESULTS.md) found that
the baseline fails the calibration gate, so no risk model has been published.

## Run locally

Use Node.js 22+ and Python 3.12+. From `services/api`, create a virtual environment, install `requirements.txt`, and run `uvicorn app.main:app --reload --port 8000`. From `apps/web`, run `npm ci` and `npm run dev`. Open `http://localhost:3000`. Without Supabase or a published model, the website and API show the labelled demonstration. Copy the `.env.example` files for local configuration; keep real `.env` files out of Git.

## Connect the hosts

1. Create a Supabase project and apply `supabase/migrations/*.sql` in filename order. The migrations create six research locations but **no weather predictions**.
2. On Render, deploy this repository with `render.yaml`. Set `DATABASE_URL` to the Supabase Postgres connection string, `CORS_ORIGINS` to the exact Vercel origin, `SUPABASE_URL` to the project URL, and `SUPABASE_ANON_KEY` to its public/anon key. The API health endpoint is `/health`.
3. On Vercel, import this GitHub repository with **Root Directory `apps/web`**. Set `NEXT_PUBLIC_API_BASE_URL` to the Render API URL and `NEXT_PUBLIC_SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_ANON_KEY` to the Supabase public values. Configure Auth redirect URLs in Supabase.
4. Keep `SUPABASE_DATABASE_URL` in a trusted runner only; never put a database password or service-role key in `NEXT_PUBLIC_*` variables.

The website and API can be deployed before research data is ready. In that state they remain visibly in demo/no-data mode.

## Produce measured rainfall results

Install `pipelines/requirements.txt` in a trusted Python 3.12 environment and set `SUPABASE_DATABASE_URL` to a writable Supabase Postgres connection. The first backfill uses [Open-Meteo Single Runs](https://open-meteo.com/en/docs/single-runs-api) ECMWF forecasts and [ERA5 reanalysis](https://open-meteo.com/en/docs/historical-weather-api), aligned to UTC daily rainfall totals. The free API is for non-commercial research and requires [attribution](https://open-meteo.com/en/terms); a commercial launch needs an appropriate data plan and source review.

```bash
python -m pipelines.backfill --locations pipelines/research_locations.json --start-run 2025-04-01 --end-run 2025-09-30 --output data/processed/pairs.csv --raw-dir data/raw
python -m ml.research_train data/processed/pairs.csv --output data/processed/model
python -m ml.register_model --model data/processed/model/model.json --evaluation data/processed/model/evaluation.json --code research-v1
python -m pipelines.run_current --model-code research-v1
```

The run dates above are examples; select a completed historical period with at least 125 distinct issued days. Backfill keeps source responses, checksums and a failure manifest. Training splits issuance times chronologically into training, calibration and untouched test periods with a ten-day gap at each boundary so outcomes cannot be shared between periods. Registration refuses a model that lacks provenance, enough independent test dates, or improvement over the simple reference. `run_current` publishes a complete current 00 UTC forecast batch through the database publication gate and verifies older published days as the reference becomes available. See [pipeline details](pipelines/README.md).

For daily operation, add repository secret `SUPABASE_DATABASE_URL` and repository variable `FBIE_MODEL_CODE` to GitHub Actions, then run the **Research forecast cycle** workflow once manually. Its scheduled run starts after 08:00 UTC. The workflow skips data steps until both values are configured.

## Checks

```bash
cd apps/web && npm ci && npm run lint && npm run build
cd services/api && pip install -r requirements.txt && python -m pytest
# From repository root:
python -m unittest discover -s ml -p 'test_*.py'
python -m unittest discover -s pipelines -p 'test_*.py'
```

GitHub Actions runs those checks on pushes and pull requests. Hosted migrations, live source connectivity, model skill and the deployed website must also be checked in the target accounts; no credentials or operational predictions are included in this repository.
