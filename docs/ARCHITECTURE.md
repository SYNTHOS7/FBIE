# FBIE system architecture

FBIE is a forecast reliability product for selected Indian cities. Its first measurable path is daily rainfall, forecast days 1–10. The website shows risk only for approved, published records. A missing record is unavailable, not low risk.

```text
Archived issued forecasts ─┐
                           ├─> paired data ─> train, calibrate, evaluate
ERA5 reanalysis proxy ──────┘                         │
                                                      ▼
Current issued run ─> inference ─> staged batch ─> publication gate
                                                          │
                                                          ▼
                                          Supabase Postgres and Auth
                                                          │
                                                FastAPI read/auth API
                                                          │
                                                 Next.js public website

Later reference values ─> verification job ─> verification records
```

## Components

- **Next.js on Vercel:** landing page, coverage, risk explorer, prediction detail, verification, methodology, and account experience. The browser receives only Supabase public credentials.
- **FastAPI on Render:** published-data and coverage endpoints plus authenticated saved-location endpoints. It reads Postgres using a server-side connection string.
- **Supabase:** run, source, model, prediction, and verification metadata; Auth and saved locations. Publication and row-level policies protect the public boundary.
- **Research jobs:** backfill paired data, train and test chronologically, infer from a current issued run, publish a complete approved batch, and verify after the reference becomes available.

## Evidence rules

Every public probability identifies its issued run, valid day, location, variable, model version, and source. Missing inputs never become zero risk. A batch is public only after its model is approved and the batch is complete.

ERA5 is a reanalysis **proxy**, not a rain-gauge observation. Verification records retain the reference kind and source. The first adapter aligns both forecast and reference to UTC daily rainfall totals. Historical evaluation describes aggregate performance, not a guarantee for an individual forecast.

## Growth path

The first six city points form an inspectable research system. More locations, variables, sources, spatial displacement, and multivariate models can be added after paired data and held-out results justify them. GitHub holds the code; the user will configure Vercel, Render, and Supabase environments.
