# FBIE — Forecast Bust Intelligence Engine

FBIE helps people understand where an Indian weather forecast may fail, how it may fail, and what evidence supports the warning. This repository contains a public website, API, database schema, and a reproducible research baseline.

## Current status

The website is a **clearly labelled demonstration**. It has no operational weather feed, verified historical archive, or approved live model. Demo screens show no numeric risk probability. Do not use them for weather decisions. The API can read approved, published predictions from Supabase Postgres when such records exist, but the data ingestion and publication pipeline has not been connected to a provider.

## Repository layout

| Component | Directory | Deployment |
| --- | --- | --- |
| Next.js website | `apps/web` | Vercel |
| FastAPI service | `services/api` | Render |
| CSV validation and normalization | `pipelines` | Offline jobs |
| Historical-rate baseline and evaluation | `ml` | Offline jobs |
| Database schema and publication function | `supabase/migrations` | Supabase Postgres |

## Run locally

Requires Node.js 22+ and Python 3.12+.

```bash
cd services/api
python -m venv .venv
# Activate .venv using your shell, then:
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

In another terminal:

```bash
cd apps/web
npm ci
npm run dev
```

The website opens at http://localhost:3000. Set `NEXT_PUBLIC_API_BASE_URL` from `apps/web/.env.example` if the API uses a different port. When the API is unavailable, the browser displays a labelled local demonstration.

Run checks:

```bash
cd apps/web && npm run build
cd services/api && python -m pytest
# From the repository root:
python -m unittest ml.test_baseline
```

## Connect Supabase, Render, and Vercel

Apply all SQL files in `supabase/migrations` in filename order to your Supabase project. The database begins empty. On Render, use `render.yaml` to create the FastAPI web service and set `DATABASE_URL` to the Supabase Postgres connection string. Set `CORS_ORIGINS` to the exact Vercel site origin. On Vercel, import this GitHub repository with **Root Directory = `apps/web`** and set `NEXT_PUBLIC_API_BASE_URL` to the Render service URL.

Keep database credentials on Render only. The browser never receives a service role key. The frontend does not yet expose sign-in or saved locations; the Supabase table and row policies prepare that feature.

## Scientific path to operational results

Use `pipelines/paired.py` to validate a real paired forecast and observation CSV. `pipelines/normalize.py` writes a canonical copy and checksums. `ml/baseline.py` trains and evaluates a transparent historical-rate baseline on a chronological holdout. These tools do not fetch weather data or publish a model. Before showing live risk, establish an approved source archive, align observations, test geographic and temporal generalization, check calibration against simple baselines, then publish complete batches through the database publication function. See `pipelines/SOURCES.md` for source and license considerations.

## Product notes

See `docs/PRODUCT.md` for the product contract. Feedback and contributions can start with a GitHub issue.